from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models import Course, CourseModule, Lesson, User, Enrollment, UserRole, CourseStatus
from auth import get_current_user, instructor_required
from utils.validators import validate_course_data
from werkzeug.utils import secure_filename
import uuid 
import os 

course_bp = Blueprint('courses', __name__)


UPLOAD_FOLDER = 'static/uploads/thumbnails'  # Or wherever you want
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@course_bp.route('/', methods=['GET'])
def get_courses():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        difficulty = request.args.get('difficulty')
        instructor_id = request.args.get('instructor_id', type=int)
        search = request.args.get('search')
        
        # Build query
        query = Course.query.filter_by(status=CourseStatus.PUBLISHED)
        
        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)
        
        if instructor_id:
            query = query.filter_by(instructor_id=instructor_id)
        
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    Course.title.ilike(search_term),
                    Course.description.ilike(search_term),
                    Course.short_description.ilike(search_term)
                )
            )
        
        # Execute query with pagination
        courses = query.order_by(Course.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'courses': [course.to_dict() for course in courses.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': courses.total,
                'pages': courses.pages,
                'has_next': courses.has_next,
                'has_prev': courses.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@course_bp.route('/<int:course_id>', methods=['GET'])
def get_course(course_id):
    try:
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user is enrolled (if authenticated)
        user = get_current_user()
        is_enrolled = False
        if user:
            enrollment = Enrollment.query.filter_by(
                user_id=user.id, 
                course_id=course_id, 
                is_active=True
            ).first()
            is_enrolled = enrollment is not None
        
        # Include modules only if enrolled or course has preview modules
        include_modules = is_enrolled or any(module.is_preview for module in course.modules)
        
        course_data = course.to_dict(include_modules=include_modules)
        course_data['is_enrolled'] = is_enrolled
        
        return jsonify({'course': course_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@course_bp.route('/', methods=['POST'])
# @instructor_required
def create_course():
    try:
        user = get_current_user()
        data = request.form  # ✅ Get non-file fields from form data
        file = request.files.get('thumbnail')  # ✅ Get uploaded file

        # Optional: validate required fields
        required_fields = ['title', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Handle thumbnail upload if provided
        thumbnail_path = None
        if file and allowed_file(file.filename):  # Make sure `allowed_file` checks file extension
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            thumbnail_path = filepath

        
        print(data.get('status'),CourseStatus(data['status']))
        # return {"done"}

                # Handle role safely
        if data.get('status'):
            try:
                status = CourseStatus(data['status'].lower())
            except ValueError:
                return jsonify({'error': f"Invalid role: {data['role']}"}), 400
        else:
            status = CourseStatus.DRAFT

        # Create course
        course = Course(
            title=data.get('title'),
            description=data.get('description'),
            short_description=data.get('short_description'),
            instructor_id=user.id,
            price=float(data.get('price')),
            currency=data.get('currency', 'USD'),
            duration_hours=data.get('duration_hours'),
            difficulty_level=data.get('difficulty_level'),
            thumbnail=thumbnail_path,
            max_students=int(data.get('max_students', 0)) if data.get('max_students') else None,
            prerequisites=data.get('prerequisites'),
            status=status,
            learning_outcomes=data.get('learning_outcomes'),
        )

        db.session.add(course)
        db.session.commit()

        return jsonify({
            'message': 'Course created successfully',
            'course': course.to_dict(include_modules=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@course_bp.route('/<int:course_id>', methods=['PUT'])
@instructor_required
def update_course(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to update this course'}), 403
        
        data = request.get_json()
        
        # Update course fields
        if 'title' in data:
            course.title = data['title']
        if 'description' in data:
            course.description = data['description']
        if 'short_description' in data:
            course.short_description = data['short_description']
        if 'price' in data:
            course.price = data['price']
        if 'currency' in data:
            course.currency = data['currency']
        if 'duration_hours' in data:
            course.duration_hours = data['duration_hours']
        if 'difficulty_level' in data:
            course.difficulty_level = data['difficulty_level']
        if 'thumbnail' in data:
            course.thumbnail = data['thumbnail']
        if 'max_students' in data:
            course.max_students = data['max_students']
        if 'prerequisites' in data:
            course.prerequisites = data['prerequisites']
        if 'learning_outcomes' in data:
            course.learning_outcomes = data['learning_outcomes']
        if 'status' in data and user.role == UserRole.ADMIN:
            course.status = CourseStatus(data['status'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Course updated successfully',
            'course': course.to_dict(include_modules=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/<int:course_id>', methods=['DELETE'])
@instructor_required
def delete_course(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to delete this course'}), 403
        
        # Check if course has enrollments
        if course.enrollments.count() > 0:
            return jsonify({'error': 'Cannot delete course with active enrollments'}), 400
        
        db.session.delete(course)
        db.session.commit()
        
        return jsonify({'message': 'Course deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/<int:course_id>/modules', methods=['POST'])
@instructor_required
def create_module(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to modify this course'}), 403
        
        data = request.get_json()
        
        if not data.get('title'):
            return jsonify({'error': 'Module title is required'}), 400
        
        # Get next order number
        max_order = db.session.query(db.func.max(CourseModule.order)).filter_by(course_id=course_id).scalar() or 0
        
        module = CourseModule(
            course_id=course_id,
            title=data['title'],
            description=data.get('description'),
            order=max_order + 1,
            is_preview=data.get('is_preview', False)
        )
        
        db.session.add(module)
        db.session.commit()
        
        return jsonify({
            'message': 'Module created successfully',
            'module': module.to_dict(include_lessons=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/<int:course_id>/modules/<int:module_id>/lessons', methods=['POST'])
@instructor_required
def create_lesson(course_id, module_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)
        
        if not course or not module or module.course_id != course_id:
            return jsonify({'error': 'Course or module not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to modify this course'}), 403
        
        data = request.get_json()
        
        if not data.get('title'):
            return jsonify({'error': 'Lesson title is required'}), 400
        
        # Get next order number
        max_order = db.session.query(db.func.max(Lesson.order)).filter_by(module_id=module_id).scalar() or 0
        
        lesson = Lesson(
            module_id=module_id,
            title=data['title'],
            content=data.get('content'),
            video_url=data.get('video_url'),
            duration_minutes=data.get('duration_minutes'),
            order=max_order + 1,
            is_preview=data.get('is_preview', False)
        )
        
        db.session.add(lesson)
        db.session.commit()
        
        return jsonify({
            'message': 'Lesson created successfully',
            'lesson': lesson.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/my-courses', methods=['GET'])
@instructor_required
def get_my_courses():
    try:
        user = get_current_user()
        
        # Get courses based on user role
        if user.role == UserRole.ADMIN:
            courses = Course.query.all()
        else:
            courses = Course.query.filter_by(instructor_id=user.id).all()
        
        return jsonify({
            'courses': [course.to_dict(include_modules=True) for course in courses]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@course_bp.route('/<int:course_id>/publish', methods=['POST'])
@instructor_required
def publish_course(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to publish this course'}), 403
        
        # Validate course is ready for publishing
        if not course.modules.count():
            return jsonify({'error': 'Course must have at least one module to be published'}), 400
        
        has_lessons = any(module.lessons.count() > 0 for module in course.modules)
        if not has_lessons:
            return jsonify({'error': 'Course must have at least one lesson to be published'}), 400
        
        course.status = CourseStatus.PUBLISHED
        db.session.commit()
        
        return jsonify({
            'message': 'Course published successfully',
            'course': course.to_dict(include_modules=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/<int:course_id>/enrollments', methods=['GET'])
@instructor_required
def get_course_enrollments(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to view course enrollments'}), 403
        
        enrollments = Enrollment.query.filter_by(course_id=course_id, is_active=True).all()
        
        enrollment_data = []
        for enrollment in enrollments:
            user_data = enrollment.user.to_dict()
            enrollment_info = enrollment.to_dict()
            enrollment_data.append({
                'user': user_data,
                'enrollment': enrollment_info
            })
        
        return jsonify({
            'course_id': course_id,
            'course_title': course.title,
            'total_enrollments': len(enrollment_data),
            'enrollments': enrollment_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
