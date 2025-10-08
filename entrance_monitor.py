"""
Entrance Monitoring System
Automatically detects and identifies people entering the office
Marks attendance with cooldown to prevent duplicates
"""

import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from services.face_recognition_service import FaceRecognitionService
from models import Attendance
from database import db
import sys
import os

class EntranceMonitor:
    """
    Real-time entrance monitoring system for automatic attendance
    """

    def __init__(self, camera_source=0, cooldown_minutes=5):
        """
        Initialize entrance monitor

        Args:
            camera_source: Camera index (0 for default webcam) or IP camera URL
            cooldown_minutes: Minutes to wait before allowing same person to mark attendance again
        """
        self.camera_source = camera_source
        self.cooldown_minutes = cooldown_minutes
        self.face_service = FaceRecognitionService()
        self.last_recognition = {}  # user_id -> timestamp
        self.process_every_n_frames = 5  # Process every 5th frame for performance
        self.frame_count = 0

        # Video capture
        self.video_capture = None

        # Display settings
        self.font = cv2.FONT_HERSHEY_DUPLEX
        self.font_scale = 0.6
        self.font_thickness = 1

    def start_camera(self):
        """Initialize camera connection"""
        try:
            self.video_capture = cv2.VideoCapture(self.camera_source)

            if not self.video_capture.isOpened():
                print(f"Error: Could not open camera {self.camera_source}")
                return False

            # Set camera properties for better performance
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            print(f"Camera {self.camera_source} started successfully")
            return True

        except Exception as e:
            print(f"Error starting camera: {str(e)}")
            return False

    def stop_camera(self):
        """Release camera resources"""
        if self.video_capture:
            self.video_capture.release()
        cv2.destroyAllWindows()

    def is_in_cooldown(self, user_id):
        """Check if user is in cooldown period"""
        if user_id not in self.last_recognition:
            return False

        last_time = self.last_recognition[user_id]
        cooldown_end = last_time + timedelta(minutes=self.cooldown_minutes)

        return datetime.now() < cooldown_end

    def get_cooldown_remaining(self, user_id):
        """Get remaining cooldown time in seconds"""
        if user_id not in self.last_recognition:
            return 0

        last_time = self.last_recognition[user_id]
        cooldown_end = last_time + timedelta(minutes=self.cooldown_minutes)
        remaining = (cooldown_end - datetime.now()).total_seconds()

        return max(0, remaining)

    def mark_attendance(self, user_id, full_name, employee_id):
        """Mark attendance for recognized user"""
        try:
            # Check cooldown
            if self.is_in_cooldown(user_id):
                remaining = self.get_cooldown_remaining(user_id)
                print(f"User {full_name} is in cooldown. {int(remaining)}s remaining")
                return False, f"Cooldown active: {int(remaining)}s remaining"

            # Mark attendance in database
            success, message = Attendance.mark_attendance(user_id)

            if success:
                # Update last recognition time
                self.last_recognition[user_id] = datetime.now()
                print(f"✓ Attendance marked for {full_name} ({employee_id})")
                return True, "Attendance marked successfully"
            else:
                print(f"✗ Failed to mark attendance for {full_name}: {message}")
                return False, message

        except Exception as e:
            print(f"Error marking attendance: {str(e)}")
            return False, str(e)

    def draw_face_box(self, frame, face_location, label, color, sub_label=None):
        """Draw bounding box and label on frame"""
        top, right, bottom, left = face_location

        # Draw box
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        # Draw label background
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, label, (left + 6, bottom - 10), self.font,
                   self.font_scale, (255, 255, 255), self.font_thickness)

        # Draw sub-label if provided
        if sub_label:
            cv2.rectangle(frame, (left, bottom), (right, bottom + 25), color, cv2.FILLED)
            cv2.putText(frame, sub_label, (left + 6, bottom + 18), self.font,
                       0.5, (255, 255, 255), 1)

    def process_frame(self, frame):
        """Process a single frame for face recognition"""
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

        # Convert to RGB for face_recognition library
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Find face locations
        import face_recognition
        face_locations = face_recognition.face_locations(rgb_small_frame, model='hog')

        # Scale back up face locations
        face_locations = [(top*2, right*2, bottom*2, left*2) for (top, right, bottom, left) in face_locations]

        # Process each detected face
        for face_location in face_locations:
            # Identify face
            result = self.face_service.identify_face(frame)

            if result['success']:
                user_id = result['user_id']
                full_name = result['full_name']
                employee_id = result['employee_id']
                confidence = result['confidence']

                # Check if in cooldown
                if self.is_in_cooldown(user_id):
                    remaining = int(self.get_cooldown_remaining(user_id))
                    label = f"{full_name} (Cooldown)"
                    sub_label = f"{remaining}s remaining"
                    color = (0, 165, 255)  # Orange
                else:
                    # Try to mark attendance
                    success, message = self.mark_attendance(user_id, full_name, employee_id)

                    if success:
                        label = f"{full_name} - CHECKED IN"
                        sub_label = f"ID: {employee_id}"
                        color = (0, 255, 0)  # Green
                    else:
                        label = f"{full_name}"
                        sub_label = message
                        color = (0, 165, 255)  # Orange

                self.draw_face_box(frame, face_location, label, color, sub_label)
            else:
                # Unknown face
                label = "Unknown"
                sub_label = result.get('message', '')[:30]
                color = (0, 0, 255)  # Red
                self.draw_face_box(frame, face_location, label, color, sub_label)

        return frame

    def run(self):
        """Main monitoring loop"""
        print("="*60)
        print("ENTRANCE MONITORING SYSTEM")
        print("="*60)
        print(f"Camera Source: {self.camera_source}")
        print(f"Cooldown Period: {self.cooldown_minutes} minutes")
        print(f"Press 'q' to quit")
        print("="*60)

        # Start camera
        if not self.start_camera():
            return

        try:
            while True:
                # Capture frame
                ret, frame = self.video_capture.read()

                if not ret:
                    print("Error: Failed to capture frame")
                    break

                self.frame_count += 1

                # Process every Nth frame to improve performance
                if self.frame_count % self.process_every_n_frames == 0:
                    frame = self.process_frame(frame)

                # Add timestamp and info to frame
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), self.font, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 10),
                           self.font, 0.5, (255, 255, 255), 1)

                # Display frame
                cv2.imshow('Entrance Monitor', frame)

                # Check for quit command
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nShutting down...")
                    break

        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"\nError in monitoring loop: {str(e)}")
        finally:
            self.stop_camera()
            print("Camera stopped. Goodbye!")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Entrance Monitoring System')
    parser.add_argument('--camera', type=str, default='0',
                       help='Camera source (0 for default webcam, or IP camera URL)')
    parser.add_argument('--cooldown', type=int, default=5,
                       help='Cooldown period in minutes (default: 5)')

    args = parser.parse_args()

    # Convert camera source to int if it's a number
    camera_source = args.camera
    try:
        camera_source = int(camera_source)
    except ValueError:
        pass  # Keep as string for IP camera URLs

    # Create and run monitor
    monitor = EntranceMonitor(
        camera_source=camera_source,
        cooldown_minutes=args.cooldown
    )

    monitor.run()


if __name__ == '__main__':
    main()
