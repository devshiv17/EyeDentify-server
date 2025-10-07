from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
from database import db
from models import User
from services.face_recognition_service import FaceRecognitionService

users_bp = Blueprint('users', __name__)

def admin_required():
    """Decorator to check if user is admin"""
    def wrapper(fn):
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user = get_jwt_identity()
            if current_user['role'] != 'admin':
                return jsonify({'error': 'Admin access required'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    """
    Get all users (admin only) or current user info
    Returns: [{id, username, full_name, email, role, employee_id, is_active}]
    """
    current_user = get_jwt_identity()

    if current_user['role'] == 'admin':
        users = User.get_all_users()
        return jsonify({'users': users}), 200
    else:
        user = User.find_by_id(current_user['id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user}), 200

@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    Get user by ID
    Admin: can view any user
    Regular user: can only view themselves
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin' and current_user['id'] != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user}), 200

@users_bp.route('/', methods=['POST'])
@admin_required()
@jwt_required()
def create_user():
    """
    Create new user (admin only)
    Body: {username, email, password, full_name, employee_id, role}
    """
    data = request.get_json()

    required_fields = ['username', 'email', 'password', 'full_name', 'employee_id']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if username or email already exists
    if User.find_by_username(data['username']):
        return jsonify({'error': 'Username already exists'}), 409

    if User.find_by_email(data['email']):
        return jsonify({'error': 'Email already exists'}), 409

    password_hash = generate_password_hash(data['password'])
    role = data.get('role', 'user')

    user_id = User.create_user(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash,
        full_name=data['full_name'],
        employee_id=data['employee_id'],
        role=role
    )

    return jsonify({
        'message': 'User created successfully',
        'user_id': user_id
    }), 201

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    Update user information
    Admin: can update any user
    Regular user: can only update themselves (limited fields)
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin' and current_user['id'] != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    # Regular users can only update certain fields
    if current_user['role'] != 'admin':
        allowed_fields = ['email', 'password']
        data = {k: v for k, v in data.items() if k in allowed_fields}

    if 'password' in data:
        data['password_hash'] = generate_password_hash(data['password'])
        del data['password']

    User.update_user(user_id, data)

    return jsonify({'message': 'User updated successfully'}), 200

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required()
@jwt_required()
def delete_user(user_id):
    """
    Deactivate user (admin only)
    """
    current_user = get_jwt_identity()

    if current_user['id'] == user_id:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400

    User.deactivate_user(user_id)

    return jsonify({'message': 'User deactivated successfully'}), 200

@users_bp.route('/<int:user_id>/photos', methods=['POST'])
@admin_required()
@jwt_required()
def upload_user_photos(user_id):
    """
    Upload facial photos for a user and train the recognition model (admin only)
    Form Data: photos (multiple files)
    """
    if 'photos' not in request.files:
        return jsonify({'error': 'No photos provided'}), 400

    files = request.files.getlist('photos')

    if len(files) < 3:
        return jsonify({'error': 'At least 3 photos required for training'}), 400

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Save photos and extract facial encodings
    face_service = FaceRecognitionService()
    saved_photos = []
    encodings = []

    user_folder = os.path.join('uploads/photos', str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{user_id}_{len(saved_photos)}_{file.filename}")
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)

            # Extract facial encoding
            encoding = face_service.extract_face_encoding(filepath)
            if encoding is not None:
                encodings.append(encoding)
                saved_photos.append(filepath)
            else:
                os.remove(filepath)

    if len(encodings) < 3:
        return jsonify({'error': 'Could not detect faces in enough photos. Please provide clearer photos.'}), 400

    # Save encodings to database
    User.save_facial_encodings(user_id, encodings, saved_photos)

    # Retrain the model
    face_service.retrain_model()

    return jsonify({
        'message': f'Successfully uploaded {len(saved_photos)} photos and trained model',
        'photos_count': len(saved_photos)
    }), 200

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
