# ESP32-CAM WebSocket Streaming Server

A real-time camera streaming server for ESP32-CAM that provides WebSocket-based video streaming with Firebase integration for the SmartHaus IoT ecosystem.

## Features

- **Real-time video streaming** via WebSocket
- **Firebase Realtime Database integration** for device management
- **Web-based status interface** for monitoring
- **Automatic device registration** with IP address
- **Connection monitoring** and auto-restart functionality

## Setup

### Prerequisites
- PlatformIO IDE
- ESP32-CAM (AI-Thinker model)
- Firebase project with Authentication and Realtime Database enabled
- USB-to-Serial adapter for programming

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rul3zero/SmartHaus.git
   cd SmartHaus/esp32cam
   ```

2. **Copy the secrets template and configure your credentials**
   ```bash
   cp include/secrets.h.example include/secrets.h
   ```

3. **Configure Firebase and WiFi**
   - Edit `include/secrets.h` with your actual credentials:
     - WiFi SSID and password
     - Firebase Web API key
     - Firebase Auth user email and password
     - Firebase Realtime Database URL
   - Follow the detailed setup instructions in the `secrets.h.example` file

4. **Build and upload using PlatformIO**
   ```bash
   pio run --target upload
   ```

## Database Structure

The ESP32-CAM writes to and reads from these Firebase paths:

```json
{
  "devices": {
    "esp32cam_001": {
      "ip_address": "192.168.1.100",
      "ws_port": 81,
      "status": "online",
      "last_updated": "2025-08-27 14:30:25"
    }
  },
  "test": {
    "connection": "Hello from ESP32-CAM"
  }
}
```

---

## Hardware Configuration

### Camera Settings

- **Frame size:** VGA (640x480)
- **Format:** JPEG
- **Quality:** 12 (adjustable)
- **Frame rate:** ~10 FPS

### Pinout (AI-Thinker ESP32-CAM)

```
PWDN:  GPIO32    RESET: -1         XCLK:  GPIO0
SIOD:  GPIO26    SIOC:  GPIO27     
Y9:    GPIO35    Y8:    GPIO34     Y7:    GPIO39    Y6:    GPIO36
Y5:    GPIO21    Y4:    GPIO19     Y3:    GPIO18    Y2:    GPIO5
VSYNC: GPIO25    HREF:  GPIO23     PCLK:  GPIO22
FLASH: GPIO4
```

---

## Usage

### WebSocket Streaming

Connect to:
```
ws://[ESP32_IP_ADDRESS]:81/ws
```

### Web Interface

Access device status at:
```
http://[ESP32_IP_ADDRESS]/
```

### API Endpoints

- `GET /` — Device info page
- `GET /status` — JSON status

---

## Firebase Integration

- Uses Firebase Email/Password authentication for device status and commands.

---

## Tech Stack

- **PlatformIO/Arduino** — Development framework
- **ESP32-CAM** — Hardware
- **Firebase** — Auth & Realtime Database
- **WebSockets** — Video streaming
- **WiFi** — Connectivity

---

## Client Applications

Works well with [SmartHaus-App](https://github.com/rul3zero/SmartHaus-App)