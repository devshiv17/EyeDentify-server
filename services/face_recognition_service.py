import cv2
import numpy as np
import pickle
import os
import face_recognition
from database import db
from models import User

class FaceRecognitionService:
    """
    Face recognition using face_recognition library (dlib-based deep learning models)
    Provides high accuracy face detection and recognition
    """

    def __init__(self):
        self.known_face_encodings = []
        self.known_face_metadata = []  # Store user_id, full_name, employee_id
        self.confidence_threshold = 0.6  # Distance threshold (lower = more strict)
        self.model_path = 'models/face_encodings.pkl'
        os.makedirs('models', exist_ok=True)
        self.load_model()

    def extract_face_encoding(self, image_path):
        """
        Extract face encoding from an image using dlib's deep learning model
        Returns: 128-dimensional face encoding or None if no face detected
        """
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)

            # Find all face locations and encodings in the image
            # model can be 'hog' (faster) or 'cnn' (more accurate, requires GPU)
            face_locations = face_recognition.face_locations(image, model='hog')

            if len(face_locations) == 0:
                print("No face detected in image")
                return None

            # Get encoding for the first face
            face_encodings = face_recognition.face_encodings(image, face_locations)

            if len(face_encodings) == 0:
                print("Could not generate encoding for detected face")
                return None

            # Return the first face encoding (128-dimensional vector)
            return face_encodings[0]

        except Exception as e:
            print(f"Error extracting face encoding: {str(e)}")
            return None

    def retrain_model(self):
        """
        Reload all face encodings from database
        """
        try:
            # Get all facial encodings from database
            encodings_data = User.get_all_facial_encodings()

            if not encodings_data or len(encodings_data) == 0:
                print("No facial encodings found for training")
                return False

            self.known_face_encodings = []
            self.known_face_metadata = []

            for item in encodings_data:
                user_id = item['user_id']
                encoding_bytes = item['encoding']

                # Deserialize numpy array
                encoding = pickle.loads(encoding_bytes)

                self.known_face_encodings.append(encoding)
                self.known_face_metadata.append({
                    'user_id': user_id,
                    'full_name': item['full_name'],
                    'employee_id': item['employee_id']
                })

            # Save to cache
            self.save_model()

            print(f"Model trained successfully with {len(self.known_face_encodings)} face encodings from {len(set(item['user_id'] for item in self.known_face_metadata))} users")
            return True

        except Exception as e:
            print(f"Error training model: {str(e)}")
            return False

    def identify_face(self, image):
        """
        Identify a person from an image
        Args:
            image: numpy array (OpenCV image in BGR format) or path to image
        Returns:
            dict: {success, user_id, full_name, employee_id, confidence, message}
        """
        try:
            if len(self.known_face_encodings) == 0:
                return {
                    'success': False,
                    'message': 'Face recognition model not trained'
                }

            # Convert from BGR to RGB (face_recognition uses RGB)
            if isinstance(image, np.ndarray):
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = face_recognition.load_image_file(image)

            # Find all face locations and encodings
            face_locations = face_recognition.face_locations(rgb_image, model='hog')

            if len(face_locations) == 0:
                return {
                    'success': False,
                    'message': 'No face detected in image'
                }

            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

            if len(face_encodings) == 0:
                return {
                    'success': False,
                    'message': 'Could not generate encoding for detected face'
                }

            # Use the first detected face
            unknown_encoding = face_encodings[0]

            # Compare with all known faces
            face_distances = face_recognition.face_distance(self.known_face_encodings, unknown_encoding)

            if len(face_distances) == 0:
                return {
                    'success': False,
                    'message': 'No known faces to compare against'
                }

            # Find the best match
            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]

            # Convert distance to confidence (0-1 scale, higher is better)
            # face_distance returns euclidean distance, typical threshold is 0.6
            confidence = 1 - best_distance

            # Check if confidence meets threshold
            if best_distance > self.confidence_threshold:
                return {
                    'success': False,
                    'message': f'Face not recognized with sufficient confidence (distance: {best_distance:.2f}, threshold: {self.confidence_threshold})'
                }

            # Get user information
            user_info = self.known_face_metadata[best_match_index]

            return {
                'success': True,
                'user_id': int(user_info['user_id']),
                'full_name': user_info['full_name'],
                'employee_id': user_info['employee_id'],
                'confidence': float(confidence),
                'distance': float(best_distance)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error during face recognition: {str(e)}'
            }

    def save_model(self):
        """Save the known face encodings to disk"""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'encodings': self.known_face_encodings,
                    'metadata': self.known_face_metadata
                }, f)
            return True
        except Exception as e:
            print(f"Error saving model: {str(e)}")
            return False

    def load_model(self):
        """Load the known face encodings from disk"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data['encodings']
                    self.known_face_metadata = data['metadata']
                print(f"Model loaded successfully with {len(self.known_face_encodings)} encodings")
                return True
            else:
                print("No saved model found")
                return False
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return False

    def detect_and_draw_faces(self, image):
        """
        Detect faces and draw bounding boxes (for testing/debugging)
        Args:
            image: numpy array (OpenCV image in BGR format)
        Returns: image with drawn boxes and labels
        """
        try:
            # Convert from BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Find all face locations
            face_locations = face_recognition.face_locations(rgb_image, model='hog')

            # Draw rectangles around faces
            for (top, right, bottom, left) in face_locations:
                # Draw box
                cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)

            return image

        except Exception as e:
            print(f"Error detecting faces: {str(e)}")
            return image
