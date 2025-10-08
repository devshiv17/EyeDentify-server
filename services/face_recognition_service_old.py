import cv2
import dlib
import numpy as np
import pickle
import os
from sklearn.neighbors import KNeighborsClassifier
from database import db
from models import User

class FaceRecognitionService:
    """
    Face recognition service using OpenCV and Dlib
    Uses face_recognition library's approach with dlib's face detector and encoder
    """

    def __init__(self):
        self.face_detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor('models/shape_predictor_68_face_landmarks.dat')
        self.face_encoder = dlib.face_recognition_model_v1('models/dlib_face_recognition_resnet_model_v1.dat')
        self.model = None
        self.user_labels = {}
        self.confidence_threshold = 0.6  # Adjust based on testing
        self.model_path = 'models/face_recognition_model.pkl'
        self.load_model()

    def extract_face_encoding(self, image_path):
        """
        Extract 128-dimensional face encoding from an image
        Returns: numpy array of face encoding or None if no face detected
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return None

            # Convert to RGB (dlib uses RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect faces
            faces = self.face_detector(rgb_image, 1)

            if len(faces) == 0:
                return None

            # Use the first detected face
            face = faces[0]

            # Get facial landmarks
            shape = self.shape_predictor(rgb_image, face)

            # Compute face encoding (128D vector)
            face_encoding = self.face_encoder.compute_face_descriptor(rgb_image, shape)

            return np.array(face_encoding)

        except Exception as e:
            print(f"Error extracting face encoding: {str(e)}")
            return None

    def retrain_model(self):
        """
        Retrain the face recognition model with all stored face encodings
        Uses KNN classifier for fast recognition
        """
        try:
            # Get all facial encodings from database
            encodings_data = User.get_all_facial_encodings()

            if not encodings_data or len(encodings_data) == 0:
                print("No facial encodings found for training")
                return False

            X = []  # Face encodings
            y = []  # User IDs

            for item in encodings_data:
                user_id = item['user_id']
                encoding_bytes = item['encoding']

                # Deserialize numpy array
                encoding = pickle.loads(encoding_bytes)
                X.append(encoding)
                y.append(user_id)

                # Store user label mapping
                if user_id not in self.user_labels:
                    self.user_labels[user_id] = {
                        'full_name': item['full_name'],
                        'employee_id': item['employee_id']
                    }

            X = np.array(X)
            y = np.array(y)

            # Train KNN classifier
            # n_neighbors should be at least 3, but not more than number of samples
            n_neighbors = min(5, len(X))
            self.model = KNeighborsClassifier(
                n_neighbors=n_neighbors,
                algorithm='ball_tree',
                weights='distance'
            )
            self.model.fit(X, y)

            # Save model
            self.save_model()

            print(f"Model trained successfully with {len(X)} face encodings from {len(set(y))} users")
            return True

        except Exception as e:
            print(f"Error training model: {str(e)}")
            return False

    def identify_face(self, image):
        """
        Identify a person from an image
        Args:
            image: numpy array (OpenCV image)
        Returns:
            dict: {
                success: bool,
                user_id: int,
                full_name: str,
                employee_id: str,
                confidence: float,
                message: str
            }
        """
        try:
            if self.model is None:
                return {
                    'success': False,
                    'message': 'Face recognition model not trained'
                }

            # Convert to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect faces
            faces = self.face_detector(rgb_image, 1)

            if len(faces) == 0:
                return {
                    'success': False,
                    'message': 'No face detected in image'
                }

            # Use the first detected face
            face = faces[0]

            # Get facial landmarks
            shape = self.shape_predictor(rgb_image, face)

            # Compute face encoding
            face_encoding = self.face_encoder.compute_face_descriptor(rgb_image, shape)
            face_encoding = np.array(face_encoding).reshape(1, -1)

            # Predict using KNN
            distances, indices = self.model.kneighbors(face_encoding, n_neighbors=1)
            predicted_user_id = self.model.predict(face_encoding)[0]

            # Calculate confidence (inverse of distance, normalized)
            distance = distances[0][0]
            confidence = 1 / (1 + distance)

            # Check if confidence meets threshold
            if confidence < self.confidence_threshold:
                return {
                    'success': False,
                    'message': f'Face not recognized with sufficient confidence (confidence: {confidence:.2f})'
                }

            # Get user information
            user_info = self.user_labels.get(predicted_user_id)

            return {
                'success': True,
                'user_id': int(predicted_user_id),
                'full_name': user_info['full_name'],
                'employee_id': user_info['employee_id'],
                'confidence': float(confidence)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error during face recognition: {str(e)}'
            }

    def save_model(self):
        """Save the trained model to disk"""
        try:
            os.makedirs('models', exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'user_labels': self.user_labels
                }, f)
            return True
        except Exception as e:
            print(f"Error saving model: {str(e)}")
            return False

    def load_model(self):
        """Load the trained model from disk"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.user_labels = data['user_labels']
                print("Model loaded successfully")
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
        Returns: image with drawn boxes
        """
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        faces = self.face_detector(rgb_image, 1)

        for face in faces:
            x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        return image
