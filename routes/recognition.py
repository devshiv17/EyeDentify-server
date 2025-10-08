from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
import cv2
import numpy as np
from services.face_recognition_service import FaceRecognitionService
from models import Attendance, RecognitionLog
import base64

recognition_bp = Blueprint('recognition', __name__)

face_service = FaceRecognitionService()

def get_current_user():
    """Helper function to get user ID and role from JWT"""
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    return {
        'id': user_id,
        'role': claims.get('role', 'user')
    }

@recognition_bp.route('/identify', methods=['POST'])
def identify_face():
    """
    Identify user from captured image and mark attendance
    Body: {image: base64_encoded_image} or multipart/form-data with image file
    Returns: {
        success: bool,
        user_id: int,
        full_name: str,
        employee_id: str,
        attendance_type: 'entry'|'exit'|'ignored',
        timestamp: str,
        confidence: float
    }
    """
    try:
        # Reload model if not loaded
        if len(face_service.known_face_encodings) == 0:
            face_service.load_model()

        # Get image from request
        if 'image' in request.files:
            file = request.files['image']
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif request.is_json and 'image' in request.get_json():
            # Base64 encoded image
            data = request.get_json()
            image_data = base64.b64decode(data['image'].split(',')[-1])
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            return jsonify({'error': 'No image provided'}), 400

        # Perform face recognition
        result = face_service.identify_face(image)

        if not result['success']:
            # Log failed recognition
            RecognitionLog.log_recognition(
                user_id=None,
                confidence=0,
                status='failed'
            )
            return jsonify({
                'success': False,
                'message': result.get('message', 'Face not recognized')
            }), 200

        user_id = result['user_id']
        confidence = result['confidence']
        full_name = result['full_name']
        employee_id = result['employee_id']

        # Log successful recognition
        RecognitionLog.log_recognition(
            user_id=user_id,
            confidence=confidence,
            status='success'
        )

        # Mark attendance based on first/last detection logic
        attendance_result = mark_user_attendance(user_id)

        return jsonify({
            'success': True,
            'user_id': user_id,
            'full_name': full_name,
            'employee_id': employee_id,
            'attendance_type': attendance_result['type'],
            'timestamp': datetime.now().isoformat(),
            'confidence': confidence,
            'message': attendance_result['message']
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def mark_user_attendance(user_id):
    """
    Mark attendance for user based on first/last detection logic
    - First detection of the day: entry time
    - Last detection of the day: exit time (updates existing record)
    - Middle detections: ignored
    """
    today = datetime.now().date()
    current_time = datetime.now()

    # Check if attendance record exists for today
    existing_record = Attendance.get_user_attendance_by_date(user_id, today)

    if not existing_record:
        # First detection of the day - mark entry
        attendance_id = Attendance.create_attendance(
            user_id=user_id,
            date=today,
            entry_time=current_time,
            status='present'
        )
        return {
            'type': 'entry',
            'message': 'Entry time recorded',
            'attendance_id': attendance_id
        }
    else:
        # Update exit time (will be updated with each subsequent detection)
        # This ensures the last detection becomes the exit time
        Attendance.update_attendance(
            existing_record['id'],
            {'exit_time': current_time}
        )

        # Calculate total hours
        entry_time = existing_record['entry_time']
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)

        total_hours = (current_time - entry_time).total_seconds() / 3600

        Attendance.update_attendance(
            existing_record['id'],
            {'total_hours': round(total_hours, 2)}
        )

        return {
            'type': 'exit',
            'message': 'Exit time updated',
            'attendance_id': existing_record['id'],
            'total_hours': round(total_hours, 2)
        }

@recognition_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_recognition_logs():
    """
    Get recognition logs (admin only)
    Query params: user_id, start_date, end_date, status, limit
    """
    current_user = get_current_user()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    limit = request.args.get('limit', type=int, default=100)

    logs = RecognitionLog.get_logs(user_id, start_date, end_date, status, limit)

    return jsonify({'logs': logs}), 200

@recognition_bp.route('/test', methods=['POST'])
@jwt_required()
def test_recognition():
    """
    Test face recognition without marking attendance
    Body: {image: base64_encoded_image} or multipart/form-data
    Returns: {success: bool, user_id: int, full_name: str, confidence: float}
    """
    current_user = get_current_user()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    try:
        # Reload model if not loaded
        if len(face_service.known_face_encodings) == 0:
            face_service.load_model()

        # Get image from request
        if 'image' in request.files:
            file = request.files['image']
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif request.is_json and 'image' in request.get_json():
            data = request.get_json()
            image_data = base64.b64decode(data['image'].split(',')[-1])
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            return jsonify({'error': 'No image provided'}), 400

        # Perform face recognition
        result = face_service.identify_face(image)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
