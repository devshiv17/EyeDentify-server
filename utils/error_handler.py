"""
Generic error handler utilities for Flask routes
"""
from functools import wraps
from flask import jsonify
import psycopg2

def handle_errors(f):
    """
    Decorator to handle common errors in Flask routes
    Usage: @handle_errors
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except psycopg2.errors.UniqueViolation as e:
            error_msg = str(e)
            if 'employee_id' in error_msg:
                return jsonify({'error': 'Employee ID already exists'}), 409
            elif 'username' in error_msg:
                return jsonify({'error': 'Username already exists'}), 409
            elif 'email' in error_msg:
                return jsonify({'error': 'Email already exists'}), 409
            else:
                return jsonify({'error': 'Duplicate entry detected'}), 409
        except psycopg2.errors.ForeignKeyViolation as e:
            return jsonify({'error': 'Referenced record does not exist'}), 400
        except psycopg2.errors.NotNullViolation as e:
            return jsonify({'error': 'Missing required field'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid value: {str(e)}'}), 400
        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
        except Exception as e:
            # Log the error for debugging
            print(f"Error in {f.__name__}: {str(e)}")
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    return decorated_function
