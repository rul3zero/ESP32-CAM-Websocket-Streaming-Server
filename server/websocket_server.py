import tornado.httpserver
import tornado.websocket
import tornado.concurrent
import tornado.ioloop
import tornado.web
import tornado.gen
import threading
import asyncio
import socket
import numpy as np
import imutils
import copy
import time
import cv2
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
lock = threading.Lock()
connectedDevices = set()

class WSHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(WSHandler, self).__init__(*args, **kwargs)
        self.outputFrame = None
        self.frame = None
        self.id = None
        self.executor = tornado.concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.last_frame_time = time.time()

    def process_frames(self):
        if self.frame is None:
            return
        try:
            # Rotate frame 90 degrees (adjust as needed for your camera orientation)
            frame = imutils.rotate_bound(self.frame.copy(), 0)  # Changed from 90 to 0
            (flag, encodedImage) = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

            if not flag:
                logger.warning("Failed to encode frame")
                return
            
            self.outputFrame = encodedImage.tobytes()
            self.last_frame_time = time.time()
            logger.info(f'Processed frame: {len(self.outputFrame)} bytes for device {self.id}')
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    def open(self):
        logger.info(f'New WebSocket connection from {self.request.remote_ip}')
        connectedDevices.add(self)
        
        # Auto-assign device ID for ESP32-CAM connections
        if self.request.remote_ip == "192.168.137.132":
            self.id = "ESP32CAM_001"
            logger.info(f'Auto-assigned device ID: {self.id}')
            
            # Send confirmation to ESP32-CAM
            try:
                self.write_message("DEVICE_ID_CONFIRMED")
                logger.info(f'Sent confirmation to ESP32-CAM: DEVICE_ID_CONFIRMED')
            except Exception as e:
                logger.error(f'Failed to send confirmation: {e}')
        
        # Do NOT create test frames - wait for real camera frames
        self.outputFrame = None
        logger.info(f'Waiting for real camera frames from device: {getattr(self, "id", "unknown")}')

    def on_message(self, message):
        try:
            logger.info(f'Received message: type={type(message)}, length={len(message) if hasattr(message, "__len__") else "N/A"}')
            
            # Handle text messages (device ID confirmation or commands)
            if isinstance(message, str) or (isinstance(message, bytes) and len(message) < 100):
                if isinstance(message, bytes):
                    message_str = message.decode('utf-8')
                else:
                    message_str = str(message)
                
                if self.id is None:
                    # First message should be device ID
                    self.id = message_str
                    logger.info(f'Device registered with ID: {self.id}')
                    # Send confirmation back to ESP32-CAM
                    self.write_message("OK")
                    logger.info(f'Sent confirmation to {self.id}')
                else:
                    # Commands from web interface or device confirmations
                    logger.info(f'Received command/confirmation: {message_str}')
            else:
                # Binary messages should be image data
                if isinstance(message, bytes) and len(message) > 100:  # Basic check for image data
                    logger.info(f'Received frame data: {len(message)} bytes from {self.id}')
                    
                    # Store the raw frame data for streaming
                    self.outputFrame = message
                    logger.info(f'Updated outputFrame for streaming: {len(message)} bytes')
                    
                    # Also try to decode for processing if needed
                    self.frame = cv2.imdecode(np.frombuffer(message, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if self.frame is not None:
                        logger.info(f'Successfully decoded frame: {self.frame.shape}')
                    else:
                        logger.warning("Failed to decode received frame, but raw data stored for streaming")
                else:
                    # Handle text messages (commands from web interface)
                    if isinstance(message, bytes):
                        message_str = message.decode('utf-8')
                    else:
                        message_str = str(message)
                    logger.info(f'Received command: {message_str}')
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def on_close(self):
        """Handle WebSocket connection close"""
        if hasattr(self, 'id') and self.id:
            logger.info(f"WebSocket connection closed for device: {self.id}")
        else:
            logger.info("WebSocket connection closed for unknown device")
        
        # Remove from the connectedDevices set
        if self in connectedDevices:
            connectedDevices.remove(self)

    def check_origin(self, origin):
        return True

class StreamHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self, device_id):
        logger.info(f'Stream request for device: {device_id}')
        
        # Set headers for MJPEG stream
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
        self.set_header('Pragma', 'no-cache')
        self.set_header('Content-Type', 'multipart/x-mixed-replace; boundary=jpgboundary')
        self.set_header('Connection', 'close')

        # Find the client device
        client = None
        for c in connectedDevices:
            if c.id == device_id:
                client = c
                break

        if client is None:
            self.set_status(404)
            self.write(f"Device '{device_id}' not found or not connected")
            return

        frame_count = 0
        
        try:
            while client in connectedDevices and not self.request.connection.stream.closed():
                if client.outputFrame is not None:
                    jpgData = client.outputFrame
                    
                    # Write boundary and headers
                    boundary_data = b"\r\n--jpgboundary\r\n"
                    header_data = f"Content-Type: image/jpeg\r\nContent-Length: {len(jpgData)}\r\n\r\n".encode()
                    
                    self.write(boundary_data)
                    yield self.flush()
                    
                    self.write(header_data)
                    yield self.flush()
                    
                    self.write(jpgData)
                    yield self.flush()
                    
                    frame_count += 1
                    
                    if frame_count % 30 == 0:  # Log every 30 frames
                        logger.info(f"Streamed {frame_count} frames for device {device_id}")
                
                # Small delay to control frame rate
                yield tornado.gen.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in stream handler: {e}")

class ButtonHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = self.get_argument("data")
            logger.info(f'Button command: {data}')
            
            # Send command to all connected devices
            for client in connectedDevices:
                if client.id is not None:  # Only send to identified devices
                    client.write_message(data)
            
            self.write({"status": "success", "message": f"Command sent to {len(connectedDevices)} devices"})
        except Exception as e:
            logger.error(f"Error handling button command: {e}")
            self.write({"status": "error", "message": str(e)})

    def get(self):
        self.write({"message": "This is a POST-only endpoint for sending commands."})

class StatusHandler(tornado.web.RequestHandler):
    def get(self):
        device_list = []
        for device in connectedDevices:
            device_info = {
                "id": device.id or "Unknown",
                "connected": True,
                "last_frame": getattr(device, 'last_frame_time', 0)
            }
            device_list.append(device_info)
        
        self.write({
            "connected_devices": len(connectedDevices),
            "devices": device_list,
            "server_time": time.time()
        })

class TemplateHandler(tornado.web.RequestHandler):
    def get(self):
        device_ids = [d.id for d in connectedDevices if d.id is not None]
        # Use the hotspot IP for video feed URLs
        hotspot_ip = "192.168.137.1"
        
        self.render(
            os.path.join(os.path.dirname(__file__), "templates", "index.html"),
            url=f"http://{hotspot_ip}:3000/video_feed/",
            deviceIds=device_ids,
            server_ip=hotspot_ip
        )

# Static file handler for serving additional resources
class StaticHandler(tornado.web.StaticFileHandler):
    def set_default_headers(self):
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")

def make_app():
    return tornado.web.Application([
        (r'/video_feed/([^/]+)', StreamHandler),
        (r'/ws', WSHandler),
        (r'/button', ButtonHandler),
        (r'/status', StatusHandler),
        (r'/static/(.*)', StaticHandler, {"path": os.path.join(os.path.dirname(__file__), "static")}),
        (r'/', TemplateHandler),
    ], debug=True)

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    
    port = 3000
    # Listen on all interfaces
    http_server.listen(port, address="0.0.0.0")
    
    # Use the hotspot IP (192.168.137.x range) 
    hotspot_ip = "192.168.137.1"  # PC hotspot IP where ESP32-CAM can reach
    
    logger.info(f'=== WebSocket Server Started ===')
    logger.info(f'Server listening on: 0.0.0.0:{port} (all interfaces)')
    logger.info(f'Hotspot IP: {hotspot_ip}')
    logger.info(f'WebSocket URL: ws://{hotspot_ip}:{port}/ws')
    logger.info(f'Web Interface: http://{hotspot_ip}:{port}/')
    logger.info(f'Status API: http://{hotspot_ip}:{port}/status')
    logger.info(f'Also accessible via Ethernet: http://192.168.8.100:{port}/')
    logger.info(f'================================')
    
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
