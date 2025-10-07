from database import db
from datetime import datetime, timedelta
import pickle

class User:
    """User model for database operations"""

    @staticmethod
    def find_by_username(username):
        """Find user by username"""
        query = "SELECT * FROM users WHERE username = %s"
        return db.fetch_one(query, (username,))

    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        query = "SELECT * FROM users WHERE email = %s"
        return db.fetch_one(query, (email,))

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        query = "SELECT id, username, email, role, full_name, employee_id, is_active FROM users WHERE id = %s"
        return db.fetch_one(query, (user_id,))

    @staticmethod
    def create_user(username, email, password_hash, full_name, employee_id, role='user'):
        """Create new user"""
        query = """
            INSERT INTO users (username, email, password_hash, full_name, employee_id, role)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = db.execute(query, (username, email, password_hash, full_name, employee_id, role))
        return result

    @staticmethod
    def update_user(user_id, data):
        """Update user information"""
        # Build dynamic update query
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = %s")
            values.append(value)

        if not fields:
            return

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s"
        db.execute(query, tuple(values))

    @staticmethod
    def deactivate_user(user_id):
        """Deactivate user"""
        query = "UPDATE users SET is_active = FALSE WHERE id = %s"
        db.execute(query, (user_id,))

    @staticmethod
    def get_all_users():
        """Get all users"""
        query = "SELECT id, username, email, role, full_name, employee_id, is_active FROM users ORDER BY created_at DESC"
        return db.fetch_all(query)

    @staticmethod
    def save_facial_encodings(user_id, encodings, photo_paths):
        """Save facial encodings for a user"""
        # Delete existing encodings
        delete_query = "DELETE FROM facial_encodings WHERE user_id = %s"
        db.execute(delete_query, (user_id,))

        # Insert new encodings
        insert_query = """
            INSERT INTO facial_encodings (user_id, encoding, photo_path)
            VALUES (%s, %s, %s)
        """
        for encoding, photo_path in zip(encodings, photo_paths):
            # Serialize numpy array
            encoding_bytes = pickle.dumps(encoding)
            db.execute(insert_query, (user_id, encoding_bytes, photo_path))

    @staticmethod
    def get_all_facial_encodings():
        """Get all facial encodings with user information"""
        query = """
            SELECT fe.user_id, fe.encoding, u.full_name, u.employee_id
            FROM facial_encodings fe
            JOIN users u ON fe.user_id = u.id
            WHERE u.is_active = TRUE
        """
        return db.fetch_all(query)


class Attendance:
    """Attendance model for database operations"""

    @staticmethod
    def create_attendance(user_id, date, entry_time=None, exit_time=None, status='present'):
        """Create attendance record"""
        query = """
            INSERT INTO attendance (user_id, date, entry_time, exit_time, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, date) DO UPDATE
            SET entry_time = EXCLUDED.entry_time,
                exit_time = EXCLUDED.exit_time,
                status = EXCLUDED.status
            RETURNING id
        """
        result = db.execute(query, (user_id, date, entry_time, exit_time, status))
        return result

    @staticmethod
    def update_attendance(attendance_id, data):
        """Update attendance record"""
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = %s")
            values.append(value)

        if not fields:
            return

        values.append(attendance_id)
        query = f"UPDATE attendance SET {', '.join(fields)} WHERE id = %s"
        db.execute(query, tuple(values))

    @staticmethod
    def get_attendance_by_id(attendance_id):
        """Get attendance record by ID"""
        query = """
            SELECT a.*, u.full_name, u.employee_id
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = %s
        """
        return db.fetch_one(query, (attendance_id,))

    @staticmethod
    def get_user_attendance(user_id, start_date=None, end_date=None, month=None, year=None):
        """Get attendance records for a user"""
        query = """
            SELECT a.*, u.full_name, u.employee_id
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.user_id = %s
        """
        params = [user_id]

        if start_date and end_date:
            query += " AND a.date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif month and year:
            query += " AND EXTRACT(MONTH FROM a.date) = %s AND EXTRACT(YEAR FROM a.date) = %s"
            params.extend([month, year])

        query += " ORDER BY a.date DESC"
        return db.fetch_all(query, tuple(params))

    @staticmethod
    def get_user_attendance_by_date(user_id, date):
        """Get attendance record for a user on a specific date"""
        query = "SELECT * FROM attendance WHERE user_id = %s AND date = %s"
        return db.fetch_one(query, (user_id, date))

    @staticmethod
    def get_all_attendance(start_date=None, end_date=None, month=None, year=None):
        """Get all attendance records"""
        query = """
            SELECT a.*, u.full_name, u.employee_id
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE 1=1
        """
        params = []

        if start_date and end_date:
            query += " AND a.date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif month and year:
            query += " AND EXTRACT(MONTH FROM a.date) = %s AND EXTRACT(YEAR FROM a.date) = %s"
            params.extend([month, year])

        query += " ORDER BY a.date DESC, u.full_name"
        return db.fetch_all(query, tuple(params)) if params else db.fetch_all(query)

    @staticmethod
    def get_attendance_by_date(date):
        """Get all attendance records for a specific date"""
        query = """
            SELECT a.*, u.full_name, u.employee_id
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.date = %s
            ORDER BY u.full_name
        """
        return db.fetch_all(query, (date,))

    @staticmethod
    def delete_attendance(attendance_id):
        """Delete attendance record"""
        query = "DELETE FROM attendance WHERE id = %s"
        db.execute(query, (attendance_id,))

    @staticmethod
    def get_attendance_summary(user_id, month, year):
        """Get attendance summary for a user for a specific month"""
        query = """
            SELECT
                COUNT(*) as total_days,
                COUNT(CASE WHEN status = 'present' THEN 1 END) as present_days,
                COUNT(CASE WHEN status = 'absent' THEN 1 END) as absent_days,
                COUNT(CASE WHEN status = 'late' THEN 1 END) as late_days,
                COUNT(CASE WHEN status = 'half-day' THEN 1 END) as half_days,
                COALESCE(AVG(total_hours), 0) as avg_hours
            FROM attendance
            WHERE user_id = %s
            AND EXTRACT(MONTH FROM date) = %s
            AND EXTRACT(YEAR FROM date) = %s
        """
        result = db.fetch_one(query, (user_id, month, year))
        return result if result else {
            'total_days': 0,
            'present_days': 0,
            'absent_days': 0,
            'late_days': 0,
            'half_days': 0,
            'avg_hours': 0
        }


class RecognitionLog:
    """Recognition log model for database operations"""

    @staticmethod
    def log_recognition(user_id=None, confidence=0, status='success', photo_path=None):
        """Log a face recognition attempt"""
        query = """
            INSERT INTO recognition_logs (user_id, confidence, status, photo_path)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = db.execute(query, (user_id, confidence, status, photo_path))
        return result

    @staticmethod
    def get_logs(user_id=None, start_date=None, end_date=None, status=None, limit=100):
        """Get recognition logs with filters"""
        query = """
            SELECT rl.*, u.full_name, u.employee_id
            FROM recognition_logs rl
            LEFT JOIN users u ON rl.user_id = u.id
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND rl.user_id = %s"
            params.append(user_id)

        if start_date and end_date:
            query += " AND rl.timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])

        if status:
            query += " AND rl.status = %s"
            params.append(status)

        query += " ORDER BY rl.timestamp DESC LIMIT %s"
        params.append(limit)

        return db.fetch_all(query, tuple(params))


class AttendanceReport:
    """Attendance report model for database operations"""

    @staticmethod
    def create_report(generated_by, month, year, report_path):
        """Create attendance report record"""
        query = """
            INSERT INTO attendance_reports (generated_by, month, year, report_path)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = db.execute(query, (generated_by, month, year, report_path))
        return result

    @staticmethod
    def get_report(report_id):
        """Get report by ID"""
        query = "SELECT * FROM attendance_reports WHERE id = %s"
        return db.fetch_one(query, (report_id,))

    @staticmethod
    def get_all_reports(limit=50):
        """Get all reports"""
        query = """
            SELECT ar.*, u.full_name as generated_by_name
            FROM attendance_reports ar
            JOIN users u ON ar.generated_by = u.id
            ORDER BY ar.created_at DESC
            LIMIT %s
        """
        return db.fetch_all(query, (limit,))

    @staticmethod
    def delete_report(report_id):
        """Delete report"""
        query = "DELETE FROM attendance_reports WHERE id = %s"
        db.execute(query, (report_id,))
