from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models import User, Enrollment, Course, LessonProgress, Certificate
from auth import get_current_user
from utils.validators import validate_email

user_bp = Blueprint('users', __name__)

# get profile details 
@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# update user details 
@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'bio' in data:
            user.bio = data['bio']
        if 'profile_picture' in data:
            user.profile_picture = data['profile_picture']
        
        # Validate email if provided
        if 'email' in data:
            if not validate_email(data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=data['email'].lower()).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already taken'}), 409
            
            user.email = data['email'].lower()
            user.email_verified = False  # Need to re-verify email
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

#ger enrollments 
@user_bp.route('/enrollments', methods=['GET'])
@jwt_required()
def get_enrollments():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        enrollments = Enrollment.query.filter_by(user_id=user.id, is_active=True).all()
        
        enrollment_data = []
        for enrollment in enrollments:
            course_data = enrollment.course.to_dict()
            course_data['enrollment'] = enrollment.to_dict()
            enrollment_data.append(course_data)
        
        return jsonify({'enrollments': enrollment_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# create enrollments 
@user_bp.route('/enrollments/<int:course_id>', methods=['POST'])
@jwt_required()
def enroll_course(course_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if course exists
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        if course.status.value != 'published':
            return jsonify({'error': 'Course is not available for enrollment'}), 400
        
        # Check if already enrolled
        existing_enrollment = Enrollment.query.filter_by(user_id=user.id, course_id=course_id).first()
        if existing_enrollment:
            if existing_enrollment.is_active:
                return jsonify({'error': 'Already enrolled in this course'}), 409
            else:
                # Reactivate enrollment
                existing_enrollment.is_active = True
                db.session.commit()
                return jsonify({
                    'message': 'Successfully re-enrolled in course',
                    'enrollment': existing_enrollment.to_dict()
                }), 200
        
        # Create new enrollment
        enrollment = Enrollment(user_id=user.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully enrolled in course',
            'enrollment': enrollment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# get enrollment details 
@user_bp.route('/enrollments/<int:course_id>/progress', methods=['GET'])
@jwt_required()
def get_course_progress(course_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check enrollment
        enrollment = Enrollment.query.filter_by(user_id=user.id, course_id=course_id, is_active=True).first()
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this course'}), 404
        
        # Get lesson progress
        lesson_progress = LessonProgress.query.filter_by(enrollment_id=enrollment.id).all()
        progress_data = [
            {
                'lesson_id': lp.lesson_id,
                'completed': lp.completed,
                'completed_at': lp.completed_at.isoformat() if lp.completed_at else None,
                'watch_time_seconds': lp.watch_time_seconds
            }
            for lp in lesson_progress
        ]
        
        return jsonify({
            'course_id': course_id,
            'enrollment': enrollment.to_dict(),
            'lesson_progress': progress_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create enrollment progress 
@user_bp.route('/enrollments/<int:course_id>/lessons/<int:lesson_id>/progress', methods=['POST'])
@jwt_required()
def update_lesson_progress(course_id, lesson_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Check enrollment
        enrollment = Enrollment.query.filter_by(user_id=user.id, course_id=course_id, is_active=True).first()
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this course'}), 404
        
        # Get or create lesson progress
        lesson_progress = LessonProgress.query.filter_by(
            enrollment_id=enrollment.id, 
            lesson_id=lesson_id
        ).first()
        
        if not lesson_progress:
            lesson_progress = LessonProgress(
                enrollment_id=enrollment.id,
                lesson_id=lesson_id
            )
            db.session.add(lesson_progress)
        
        # Update progress
        if 'completed' in data:
            lesson_progress.completed = data['completed']
            if data['completed']:
                from datetime import datetime
                lesson_progress.completed_at = datetime.utcnow()
        
        if 'watch_time_seconds' in data:
            lesson_progress.watch_time_seconds = data['watch_time_seconds']
        
        db.session.commit()
        
        # Calculate overall course progress
        total_lessons = db.session.query(db.func.count(LessonProgress.id)).filter_by(enrollment_id=enrollment.id).scalar()
        completed_lessons = db.session.query(db.func.count(LessonProgress.id)).filter_by(
            enrollment_id=enrollment.id, completed=True
        ).scalar()
        
        if total_lessons > 0:
            enrollment.progress_percentage = (completed_lessons / total_lessons) * 100
            
            # Mark course as completed if 100% progress
            if enrollment.progress_percentage == 100 and not enrollment.completed_at:
                from datetime import datetime
                enrollment.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Lesson progress updated successfully',
            'lesson_progress': {
                'lesson_id': lesson_progress.lesson_id,
                'completed': lesson_progress.completed,
                'completed_at': lesson_progress.completed_at.isoformat() if lesson_progress.completed_at else None,
                'watch_time_seconds': lesson_progress.watch_time_seconds
            },
            'course_progress': enrollment.progress_percentage
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/certificates', methods=['GET'])
@jwt_required()
def get_certificates():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificates = Certificate.query.filter_by(user_id=user.id).all()
        
        return jsonify({
            'certificates': [cert.to_dict() for cert in certificates]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get active enrollments
        enrollments = Enrollment.query.filter_by(user_id=user.id, is_active=True).all()
        
        # Get certificates
        certificates = Certificate.query.filter_by(user_id=user.id).all()
        
        # Calculate statistics
        total_courses = len(enrollments)
        completed_courses = len([e for e in enrollments if e.completed_at])
        in_progress_courses = total_courses - completed_courses
        total_certificates = len(certificates)
        
        # Get recent activity (last 5 enrollments)
        recent_enrollments = Enrollment.query.filter_by(user_id=user.id, is_active=True)\
            .order_by(Enrollment.enrolled_at.desc()).limit(5).all()
        
        recent_activity = []
        for enrollment in recent_enrollments:
            course_data = enrollment.course.to_dict()
            course_data['enrollment'] = enrollment.to_dict()
            recent_activity.append(course_data)
        
        return jsonify({
            'user': user.to_dict(),
            'statistics': {
                'total_courses': total_courses,
                'completed_courses': completed_courses,
                'in_progress_courses': in_progress_courses,
                'total_certificates': total_certificates
            },
            'recent_activity': recent_activity,
            'certificates': [cert.to_dict() for cert in certificates]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
