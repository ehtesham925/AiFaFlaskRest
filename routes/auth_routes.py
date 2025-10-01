from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity, get_jwt,set_access_cookies,set_refresh_cookies
from werkzeug.security import check_password_hash
from app import db
from models import User, UserRole, TokenBlacklist
from utils.validators import validate_email, validate_password
import re
import os 
from werkzeug.utils import secure_filename
import requests 
from config import Config
from services.email_service import EmailService

email_service = EmailService()

auth_bp = Blueprint('auth', __name__)

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS_PROFILES = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_PROFILES
from flask import jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies
from werkzeug.utils import secure_filename
import os

""" Register """
@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if not validate_password(data['password']):
            return jsonify({
                'error': 'Password must be at least 8 characters long and contain uppercase, lowercase, digit and special character'
            }), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email'].lower()).first():
            return jsonify({'error': 'Email already registered'}), 409
             
        # Handle role safely
        if data.get('role'):
            try:
                role = UserRole(data['role'].lower())
            except ValueError:
                return jsonify({'error': f"Invalid role: {data['role']}"}), 400
        else:
            role = UserRole.STUDENT
        
        # (Optional) File upload handling — commented
        # file = request.files.get('profile_pic')
        # profile_path = None
        # if file and allowed_file(file.filename):
        #     filename = secure_filename(file.filename)
        #     os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        #     profile_path = os.path.join(UPLOAD_FOLDER,"instructors", filename)
        #     file.save(profile_path)
        
        # Create new user
        user = User(
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=role,
            phone=data.get('phone'),
            bio=data.get('bio')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        response_data = {
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        email_service.send_welcome_email(user)
        # ✅ jsonify makes it a Response object
        response = jsonify(response_data)

        # ✅ Attach cookies properly
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        return response, 201 
        
    except Exception as e:
        db.session.rollback()
        # Always return JSON response on error
        return jsonify({'error': str(e)}), 500

"""  Login  """
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email'].lower()).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""  Refresh Token  """
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or deactivated'}), 404
        
        new_token = create_access_token(identity=current_user_id)
        
        return jsonify({
            'access_token': new_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

""" Logout  """
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    try:
        jti = get_jwt()['jti']
        
        # Add token to blacklist
        blacklisted_token = TokenBlacklist(jti=jti)
        db.session.add(blacklisted_token)
        db.session.commit()
        
        return jsonify({'message': 'Successfully logged out'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

""" Change Password  """
@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Check current password
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        if not validate_password(data['new_password']):
            return jsonify({'error': 'New password must be at least 8 characters long and contain uppercase, lowercase, digit and special character'}), 400
        
        # Update password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

""" Get Current Details   """
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500





GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# Step 2: Function to verify Google ID token
def verify_google_token(token):
    """
    Verifies the ID token received from frontend using Google's endpoint.
    Returns user info (email, name, etc) if valid, else None.
    """
    try:
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={token}')
        if response.status_code != 200:
            return None
        user_info = response.json()

        # Confirm token is issued for your app
        if user_info['aud'] != Config.GOOGLE_CLIENT_ID:
            return None

        return user_info
    except Exception as e:
        print(f"Token verification error: {e}")
        return None



# Step 3: Route to handle Google login
@auth_bp.route('/api/auth/google', methods=['POST'])
def google_login():
    """
    This route receives the Google ID token from frontend,
    verifies it, then issues a custom JWT for use with protected routes.
    """
    data = request.get_json()
    google_token = data.get("token")



    if not google_token:
        return jsonify({"error": "Token is missing"}), 400

    # Verify token with Google
    user_info = verify_google_token(google_token)
    if not user_info:
        return jsonify({"error": "Invalid token"}), 401

    # You can also store user in DB here (optional)
    # Example: create_user_if_not_exists(user_info["email"])
    
    # Step 4: Issue your own JWT
    access_token = create_access_token(identity= user_info["email"],
        additional_claims={
        "name": user_info.get("name"),
        "picture": user_info.get("picture")
    })

    return jsonify(access_token=access_token), 200


