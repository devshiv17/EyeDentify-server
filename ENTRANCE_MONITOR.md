# Entrance Monitoring System

Automatic attendance marking system using camera-based face recognition.

## Overview

The entrance monitoring system automatically detects and identifies people entering the office, marking their attendance in real-time. It uses the face_recognition library (built on dlib's deep learning models) for high-accuracy face recognition.

## Features

- **Real-time face detection and recognition**
- **Automatic attendance marking** when a person is identified
- **Cooldown mechanism** to prevent duplicate entries (default: 5 minutes)
- **Webcam and IP camera support**
- **Live video feed** with visual feedback
- **Configurable settings** via environment variables or command-line arguments

## Requirements

- Python 3.8+
- Webcam or IP camera
- All dependencies from `requirements.txt`

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure camera settings in `.env` file:
```bash
cp .env.example .env
# Edit .env with your camera settings
```

## Usage

### Basic Usage (Webcam)

```bash
python entrance_monitor.py
```

This will use the default webcam (camera index 0) with default settings.

### Custom Camera Source

**Using a different webcam:**
```bash
python entrance_monitor.py --camera 1
```

**Using an IP camera (RTSP):**
```bash
python entrance_monitor.py --camera "rtsp://username:password@192.168.1.100:554/stream"
```

**Using an IP camera (HTTP):**
```bash
python entrance_monitor.py --camera "http://192.168.1.100:8080/video"
```

### Custom Cooldown Period

```bash
python entrance_monitor.py --cooldown 10
```

This sets a 10-minute cooldown between attendance marks for the same person.

### Combined Options

```bash
python entrance_monitor.py --camera "rtsp://admin:pass123@192.168.1.50:554/stream" --cooldown 3
```

## Configuration

### Environment Variables

Configure in `.env` file:

```bash
# Camera source (0 for default webcam)
CAMERA_SOURCE=0

# Or use IP camera
IP_CAMERA_URL=rtsp://username:password@192.168.1.100:554/stream

# Camera resolution
CAMERA_WIDTH=640
CAMERA_HEIGHT=480

# Process every N frames (higher = faster but less responsive)
PROCESS_EVERY_N_FRAMES=5

# Recognition cooldown in minutes
COOLDOWN_MINUTES=5

# Confidence threshold (0.6 recommended, lower = more strict)
CONFIDENCE_THRESHOLD=0.6

# Face detection model ('hog' for CPU, 'cnn' for GPU)
FACE_DETECTION_MODEL=hog
```

### Performance Tuning

**For faster performance:**
- Increase `PROCESS_EVERY_N_FRAMES` (e.g., 10)
- Use lower camera resolution (e.g., 320x240)
- Use 'hog' detection model

**For better accuracy:**
- Decrease `PROCESS_EVERY_N_FRAMES` (e.g., 2)
- Use higher camera resolution (e.g., 1280x720)
- Use 'cnn' detection model (requires GPU)

## How It Works

1. **Camera Capture**: Continuously captures video frames from the camera
2. **Face Detection**: Detects faces in each frame using dlib's HOG or CNN detector
3. **Face Recognition**: Compares detected faces against known encodings in the database
4. **Attendance Marking**: When a face is recognized with sufficient confidence:
   - Checks if user is in cooldown period
   - If not in cooldown, marks attendance in database
   - Updates cooldown timer for that user
5. **Visual Feedback**: Displays bounding boxes and status on video feed:
   - **Green**: Attendance marked successfully
   - **Orange**: In cooldown period
   - **Red**: Unknown face

## IP Camera Setup

### Common IP Camera URL Formats

**RTSP (most common):**
```
rtsp://username:password@ip:port/stream
rtsp://admin:admin123@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0
```

**HTTP/MJPEG:**
```
http://ip:port/video
http://192.168.1.100:8080/video.mjpg
```

**ONVIF cameras:**
```
rtsp://username:password@ip:554/onvif1
```

### Finding Your IP Camera URL

1. Check camera manufacturer's documentation
2. Use VLC Media Player to test the URL:
   - Open VLC → Media → Open Network Stream
   - Enter the URL and test
3. Common default ports:
   - RTSP: 554
   - HTTP: 80, 8080

### Troubleshooting IP Cameras

- Ensure camera is on the same network
- Check firewall settings
- Verify username/password
- Try different stream URLs (main stream vs sub stream)
- Some cameras require specific URL parameters

## Controls

- **'q' key**: Quit the application
- **Close window**: Also quits the application

## System Architecture

```
entrance_monitor.py
├── Camera capture
├── Face detection (face_recognition library)
├── Face recognition (FaceRecognitionService)
├── Attendance marking (Attendance model)
└── Visual display (OpenCV)
```

## Database Requirements

The system requires:
- Face encodings stored in database (via user registration)
- Attendance table with timestamp tracking

Make sure you have:
1. Registered users with face photos
2. Trained face recognition model (`/api/users/retrain`)

## Best Practices

### Camera Placement

- Mount at entrance at face height
- Ensure good lighting
- Avoid backlighting (windows behind entrance)
- Position for front-facing views
- Consider camera angle (slightly downward is often best)

### Lighting

- Use consistent, even lighting
- Avoid harsh shadows
- Consider adding LED lights if needed
- Test at different times of day

### Network (for IP cameras)

- Use wired connection when possible
- Ensure sufficient bandwidth
- Use local network (avoid internet streams)

## Troubleshooting

### No camera detected
- Check camera connection
- Try different camera index (0, 1, 2, etc.)
- Check camera permissions on your OS

### Poor recognition accuracy
- Ensure good lighting
- Check if face encodings are trained
- Adjust confidence threshold
- Re-register users with better quality photos

### Slow performance
- Increase `PROCESS_EVERY_N_FRAMES`
- Lower camera resolution
- Use 'hog' detection model instead of 'cnn'
- Reduce number of registered users

### IP camera won't connect
- Verify URL format
- Check network connectivity
- Test with VLC media player first
- Check camera authentication

## Security Considerations

- Use HTTPS for IP cameras when possible
- Change default camera passwords
- Use local network, avoid exposing cameras to internet
- Secure the database with proper authentication
- Consider encrypting face encodings

## Future Enhancements

- Multi-face detection and parallel recognition
- Video recording of entries
- Email/SMS notifications
- Web dashboard for live monitoring
- Analytics and reporting
- Mobile app integration
- Temperature screening integration

## License

This is part of the Attendance App system.
