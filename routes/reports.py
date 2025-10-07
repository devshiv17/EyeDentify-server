from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import Attendance, User, AttendanceReport
import pandas as pd
import os

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_report():
    """
    Generate monthly attendance report (admin only)
    Body: {month: int, year: int, format: 'csv'|'excel'|'pdf'}
    Returns: {report_id, download_url}
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    month = data.get('month', datetime.now().month)
    year = data.get('year', datetime.now().year)
    format_type = data.get('format', 'csv')

    # Get all attendance records for the month
    records = Attendance.get_all_attendance(month=month, year=year)

    if not records:
        return jsonify({'error': 'No attendance records found for the specified period'}), 404

    # Create DataFrame
    df = pd.DataFrame(records)

    # Generate report file
    report_filename = f"attendance_report_{year}_{month:02d}.{format_type}"
    report_path = os.path.join('reports', report_filename)
    os.makedirs('reports', exist_ok=True)

    if format_type == 'csv':
        df.to_csv(report_path, index=False)
    elif format_type == 'excel':
        df.to_excel(report_path, index=False, engine='openpyxl')
    else:
        return jsonify({'error': 'Unsupported format'}), 400

    # Save report metadata
    report_id = AttendanceReport.create_report(
        generated_by=current_user['id'],
        month=month,
        year=year,
        report_path=report_path
    )

    return jsonify({
        'message': 'Report generated successfully',
        'report_id': report_id,
        'download_url': f'/api/reports/download/{report_id}'
    }), 201

@reports_bp.route('/download/<int:report_id>', methods=['GET'])
@jwt_required()
def download_report(report_id):
    """
    Download generated report (admin only)
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    report = AttendanceReport.get_report(report_id)

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if not os.path.exists(report['report_path']):
        return jsonify({'error': 'Report file not found'}), 404

    return send_file(
        report['report_path'],
        as_attachment=True,
        download_name=os.path.basename(report['report_path'])
    )

@reports_bp.route('/', methods=['GET'])
@jwt_required()
def get_reports():
    """
    Get list of generated reports (admin only)
    Query params: limit
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    limit = request.args.get('limit', type=int, default=50)

    reports = AttendanceReport.get_all_reports(limit)

    return jsonify({'reports': reports}), 200

@reports_bp.route('/<int:report_id>', methods=['DELETE'])
@jwt_required()
def delete_report(report_id):
    """
    Delete report (admin only)
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    report = AttendanceReport.get_report(report_id)

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    # Delete file
    if os.path.exists(report['report_path']):
        os.remove(report['report_path'])

    # Delete from database
    AttendanceReport.delete_report(report_id)

    return jsonify({'message': 'Report deleted successfully'}), 200

@reports_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_monthly_summary():
    """
    Get attendance summary for all users for a specific month
    Query params: month, year
    Returns detailed statistics
    """
    current_user = get_jwt_identity()

    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    # Get all users
    users = User.get_all_users()

    summary_data = []
    for user in users:
        if user['role'] == 'user':  # Exclude admins from attendance summary
            user_summary = Attendance.get_attendance_summary(user['id'], month, year)
            summary_data.append({
                'user_id': user['id'],
                'employee_id': user['employee_id'],
                'full_name': user['full_name'],
                'summary': user_summary
            })

    return jsonify({
        'month': month,
        'year': year,
        'users': summary_data
    }), 200
