from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app import db
from models import LessonResource, Lesson, Course, Enrollment
from auth import get_current_user, instructor_required
from services.file_service import FileService
import os

file_bp = Blueprint('files', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'wav', 'doc', 'docx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@file_bp.route('/upload', methods=['POST'])
@instructor_required
def upload_file():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        lesson_id = request.form.get('lesson_id')
        title = request.form.get('title')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not lesson_id:
            return jsonify({'error': 'Lesson ID is required'}), 400
        
        # Verify lesson exists and user has permission
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        course = lesson.module.course
        if course.instructor_id != user.id and user.role.value != 'admin':
            return jsonify({'error': 'Unauthorized to upload files for this lesson'}), 403
        
        if file and allowed_file(file.filename):
            file_service = FileService()
            file_path, file_size = file_service.save_file(file, 'lesson_resources')
            
            # Create lesson resource record
            resource = LessonResource(
                lesson_id=lesson_id,
                title=title or file.filename,
                file_path=file_path,
                file_type=file.filename.rsplit('.', 1)[1].lower(),
                file_size=file_size
            )
            
            db.session.add(resource)
            db.session.commit()
            
            return jsonify({
                'message': 'File uploaded successfully',
                'resource': resource.to_dict()
            }), 201
        else:
            return jsonify({'error': 'File type not allowed'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@file_bp.route('/download/<int:resource_id>', methods=['GET'])
@jwt_required()
def download_file(resource_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        resource = LessonResource.query.get(resource_id)
        if not resource:
            return jsonify({'error': 'File not found'}), 404
        
        lesson = resource.lesson
        course = lesson.module.course
        
        # Check if user has access (enrolled, instructor, or admin)
        has_access = False
        
        if user.role.value == 'admin' or course.instructor_id == user.id:
            has_access = True
        else:
            # Check if user is enrolled and has access to this lesson
            enrollment = Enrollment.query.filter_by(
                user_id=user.id,
                course_id=course.id,
                is_active=True
            ).first()
            
            if enrollment:
                # If lesson is preview, allow access
                if lesson.is_preview or lesson.module.is_preview:
                    has_access = True
                # If enrolled, allow access
                else:
                    has_access = True
        
        if not has_access:
            return jsonify({'error': 'Access denied. Please enroll in the course first.'}), 403
        
        file_service = FileService()
        return file_service.send_file(resource.file_path, resource.title)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@file_bp.route('/upload-course-thumbnail', methods=['POST'])
@instructor_required
def upload_course_thumbnail():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        course_id = request.form.get('course_id')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not course_id:
            return jsonify({'error': 'Course ID is required'}), 400
        
        # Verify course exists and user has permission
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        if course.instructor_id != user.id and user.role.value != 'admin':
            return jsonify({'error': 'Unauthorized to update this course'}), 403
        
        # Check if file is an image
        if file and file.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}:
            file_service = FileService()
            file_path, file_size = file_service.save_file(file, 'course_thumbnails')
            
            # Update course thumbnail
            course.thumbnail = file_path
            db.session.commit()
            
            return jsonify({
                'message': 'Thumbnail uploaded successfully',
                'thumbnail_url': file_path
            }), 200
        else:
            return jsonify({'error': 'Only image files are allowed for thumbnails'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@file_bp.route('/upload-profile-picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check if file is an image
        if file and file.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}:
            file_service = FileService()
            file_path, file_size = file_service.save_file(file, 'profile_pictures')
            
            # Update user profile picture
            user.profile_picture = file_path
            db.session.commit()
            
            return jsonify({
                'message': 'Profile picture uploaded successfully',
                'profile_picture_url': file_path
            }), 200
        else:
            return jsonify({'error': 'Only image files are allowed for profile pictures'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@file_bp.route('/lesson-resources/<int:lesson_id>', methods=['GET'])
@jwt_required()
def get_lesson_resources(lesson_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        course = lesson.module.course
        
        # Check if user has access
        has_access = False
        
        if user.role.value == 'admin' or course.instructor_id == user.id:
            has_access = True
        else:
            enrollment = Enrollment.query.filter_by(
                user_id=user.id,
                course_id=course.id,
                is_active=True
            ).first()
            
            if enrollment and (lesson.is_preview or lesson.module.is_preview):
                has_access = True
            elif enrollment:
                has_access = True
        
        if not has_access:
            return jsonify({'error': 'Access denied'}), 403
        
        resources = LessonResource.query.filter_by(lesson_id=lesson_id).all()
        
        return jsonify({
            'lesson_id': lesson_id,
            'resources': [resource.to_dict() for resource in resources]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@file_bp.route('/resources/<int:resource_id>', methods=['DELETE'])
@instructor_required
def delete_resource(resource_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        resource = LessonResource.query.get(resource_id)
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        lesson = resource.lesson
        course = lesson.module.course
        
        if course.instructor_id != user.id and user.role.value != 'admin':
            return jsonify({'error': 'Unauthorized to delete this resource'}), 403
        
        # Delete file from filesystem
        file_service = FileService()
        file_service.delete_file(resource.file_path)
        
        # Delete database record
        db.session.delete(resource)
        db.session.commit()
        
        return jsonify({'message': 'Resource deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
