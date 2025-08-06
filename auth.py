from functools import wraps
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask import jsonify
from models import User, UserRole

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        print(user.role, UserRole.ADMIN)
        print(type(user.role), type(UserRole.ADMIN))
        print(user.role == UserRole.ADMIN)

        
        if not user or user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def instructor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
            return jsonify({'error': 'Instructor access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current user from JWT token"""
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        return User.query.get(current_user_id)
    except:
        return None
