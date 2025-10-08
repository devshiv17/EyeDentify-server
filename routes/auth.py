from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import check_password_hash
from database import db
from models import User

auth_bp = Blueprint('auth', __name__)

def get_current_user_info():
    """Helper function to get user ID and role from JWT"""
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    return {
        'id': user_id,
        'role': claims.get('role', 'user')
    }

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    Body: {username, password}
    Returns: {access_token, user: {id, username, role, full_name}}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        user = User.find_by_username(username)

        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user['is_active']:
            return jsonify({'error': 'Account is deactivated'}), 403

        access_token = create_access_token(
            identity=str(user['id']),
            additional_claims={
                'username': user['username'],
                'role': user['role']
            }
        )

        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name'],
                'email': user['email'],
                'employee_id': user['employee_id']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify JWT token validity
    Returns: {valid: true, user: {...}}
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'valid': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name'],
                'email': user['email']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout endpoint (client-side token removal)
    """
    return jsonify({'message': 'Logged out successfully'}), 200
