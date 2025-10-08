"""
Camera Configuration
Supports webcam and IP camera connections
"""

import os

class CameraConfig:
    """Camera configuration settings"""

    # Default camera source (0 = default webcam, 1 = second camera, etc.)
    DEFAULT_CAMERA = int(os.getenv('CAMERA_SOURCE', '0'))

    # IP Camera URL format examples:
    # - RTSP: 'rtsp://username:password@ip_address:port/stream'
    # - HTTP: 'http://ip_address:port/video'
    IP_CAMERA_URL = os.getenv('IP_CAMERA_URL', None)

    # Camera resolution (width, height)
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '640'))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '480'))

    # Frame processing settings
    PROCESS_EVERY_N_FRAMES = int(os.getenv('PROCESS_EVERY_N_FRAMES', '5'))
    RESIZE_SCALE = float(os.getenv('RESIZE_SCALE', '0.5'))

    # Recognition settings
    COOLDOWN_MINUTES = int(os.getenv('COOLDOWN_MINUTES', '5'))
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.6'))

    # Face detection model ('hog' is faster, 'cnn' is more accurate but requires GPU)
    FACE_DETECTION_MODEL = os.getenv('FACE_DETECTION_MODEL', 'hog')

    @staticmethod
    def get_camera_source():
        """Get the active camera source"""
        if CameraConfig.IP_CAMERA_URL:
            return CameraConfig.IP_CAMERA_URL
        return CameraConfig.DEFAULT_CAMERA

    @staticmethod
    def get_camera_info():
        """Get camera configuration information"""
        source = CameraConfig.get_camera_source()
        return {
            'source': source,
            'type': 'IP Camera' if isinstance(source, str) else 'Webcam',
            'resolution': f"{CameraConfig.CAMERA_WIDTH}x{CameraConfig.CAMERA_HEIGHT}",
            'detection_model': CameraConfig.FACE_DETECTION_MODEL,
            'cooldown_minutes': CameraConfig.COOLDOWN_MINUTES,
            'confidence_threshold': CameraConfig.CONFIDENCE_THRESHOLD
        }


# Example usage:
if __name__ == '__main__':
    info = CameraConfig.get_camera_info()
    print("Camera Configuration:")
    for key, value in info.items():
        print(f"  {key}: {value}")
