from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from models import Attendance

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/', methods=['GET'])
@jwt_required()
def get_attendance():
    """
    Get attendance records
    Admin: can view all users' attendance with optional filters
    Regular user: can only view their own attendance
    Query params: user_id, start_date, end_date, month, year
    """
    current_user = get_jwt_identity()

    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    # Regular users can only view their own attendance
    if current_user['role'] != 'admin':
        user_id = current_user['id']

    # If admin doesn't specify user_id, return all users' attendance
    if current_user['role'] == 'admin' and not user_id:
        records = Attendance.get_all_attendance(start_date, end_date, month, year)
    else:
        records = Attendance.get_user_attendance(user_id, start_date, end_date, month, year)

    return jsonify({'attendance': records}), 200

@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_attendance():
    """
    Get today's attendance for current user or all users (admin)
    """
    current_user = get_jwt_identity()
    today = datetime.now().date()

    if current_user['role'] == 'admin':
        records = Attendance.get_attendance_by_date(today)
    else:
        records = Attendance.get_user_attendance_by_date(current_user['id'], today)

    return jsonify({'attendance': records}), 200

@attendance_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_attendance_summary():
    """
    Get attendance summary for a user
    Query params: user_id (admin only), month, year
    Returns: {total_days, present_days, absent_days, late_days, half_days}
    """
    current_user = get_jwt_identity()

    user_id = request.args.get('user_id', type=int)
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    if current_user['role'] != 'admin':
        user_id = current_user['id']

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    summary = Attendance.get_attendance_summary(user_id, month, year)

    return jsonify({'summary': summary}), 200

@attendance_bp.route('/<int:attendance_id>', methods=['GET'])
@jwt_required()
def get_attendance_by_id(attendance_id):
    """
    Get specific attendance record by ID
    """
    current_user = get_jwt_identity()

    record = Attendance.get_attendance_by_id(attendance_id)

    if not record:
        return jsonify({'error': 'Attendance record not found'}), 404

    # Regular users can only view their own records
    if current_user['role'] != 'admin' and record['user_id'] != current_user['id']:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({'attendance': record}), 200

@attendance_bp.route('/', methods=['POST'])
@jwt_required()
def mark_attendance():
    """
    Manually mark attendance (admin only)
    Body: {user_id, date, entry_time, exit_time, status}
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()

    required_fields = ['user_id', 'date']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    attendance_id = Attendance.create_attendance(
        user_id=data['user_id'],
        date=data['date'],
        entry_time=data.get('entry_time'),
        exit_time=data.get('exit_time'),
        status=data.get('status', 'present')
    )

    return jsonify({
        'message': 'Attendance marked successfully',
        'attendance_id': attendance_id
    }), 201

@attendance_bp.route('/<int:attendance_id>', methods=['PUT'])
@jwt_required()
def update_attendance(attendance_id):
    """
    Update attendance record (admin only)
    Body: {entry_time, exit_time, status}
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()

    Attendance.update_attendance(attendance_id, data)

    return jsonify({'message': 'Attendance updated successfully'}), 200

@attendance_bp.route('/<int:attendance_id>', methods=['DELETE'])
@jwt_required()
def delete_attendance(attendance_id):
    """
    Delete attendance record (admin only)
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    Attendance.delete_attendance(attendance_id)

    return jsonify({'message': 'Attendance deleted successfully'}), 200
