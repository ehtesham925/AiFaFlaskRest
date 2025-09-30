from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models import Course, CourseModule, Lesson, User, Enrollment, UserRole, CourseStatus,MasterCategory,SubCategory,CoursePrerequisitesCourses
from auth import get_current_user, instructor_required
from utils.validators import validate_course_data
from werkzeug.utils import secure_filename
import uuid 
import os 

course_bp = Blueprint('courses', __name__)


UPLOAD_FOLDER = 'static/uploads/thumbnails/'  # Or wherever you want
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    global ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


ALLOWED_VIDEO_EXTENSIONS_LESSONS = {'mp4', 'avi', 'mov', 'mkv'}
UPLOAD_FOLDER_lessons = 'uploads'

def allowed_file_lessons(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


"""Get courses such as archived, draft, published """
# get courses 
@course_bp.route('get-courses/', methods=['POST'])
def get_courses():
    try:
        data = request.get_json()
        types = ["published", "draft", "archived"]
        status = data.get('status', '').lower()

        # Start with base query
        query = Course.query

        # Status filtering
        if status:
            if status in types:
                query = query.filter_by(status=CourseStatus(status))
            elif status != 'all':
                return {"error": f"Invalid status: {status}"}

        # Optional filters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        difficulty = request.args.get('difficulty')
        instructor_id = request.args.get('instructor_id', type=int)
        search = request.args.get('search')

        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)

        if instructor_id:
            query = query.filter_by(instructor_id=instructor_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Course.title.ilike(search_term),
                    Course.description.ilike(search_term),
                    Course.short_description.ilike(search_term)
                )
            )

        # Final query execution
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

@course_bp.route('get-courses/', methods=['GET'])
def get_courses_all():
    try:
        courses = Course.query.order_by(Course.created_at.desc()).all()

        return jsonify({
            "courses": [course.to_dict(include_modules=True) for course in courses]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@course_bp.route('/get-courses/<int:subcourse_id>', methods=['GET'])
def get_courses_undersubcourse(subcourse_id):
    try:
        # Get the subcategory first
        subcourse = SubCategory.query.get(subcourse_id)
        if not subcourse:
            return jsonify({"error": "Subcategory not found"}), 404

        # Fetch courses that belong to this subcategory
        courses = Course.query.filter_by(subcategory_id=subcourse_id) \
                              .order_by(Course.created_at.desc()) \
                              .all()

        return jsonify({
            "subcategory": subcourse.to_dict() if hasattr(subcourse, "to_dict") else {"id": subcourse.id, "name": subcourse.name},
            "courses": [course.to_dict(include_modules=True) for course in courses]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500





# get specific course
""" get a specific course   """
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


"""Create courses with subcategory id """
# creating courses 
@course_bp.route('/create-courses', methods=['POST'])
# @instructor_required
def create_course():
    print("Create Course Route hit---")
    
    print("FORM DATA:", request.form)
    print("FILES:", request.files)




    user = get_current_user()
    data = request.form  # ✅ Get non-file fields from form data
    file = request.files.get('thumbnail')  # ✅ Get uploaded file
    
    subcategory_id = data.get("subcategory_id")

    if subcategory_id:
        try:
            subcategory_id = int(subcategory_id)
            # Optional: validate if subcategory exists
            subcategory = SubCategory.query.get(subcategory_id)
            if not subcategory:
                return jsonify({'error': f"Invalid subcategory_id: {subcategory_id}"}), 400
        except ValueError:
            return jsonify({'error': "subcategory_id must be an integer"}), 400
    else:
        subcategory_id = None  # or default
    
    # Optional: validate required fields
    required_fields = ['title', 'price']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Handle thumbnail upload if provided
    thumbnail_path = None
    global UPLOAD_FOLDER
    if file and allowed_file(file.filename):  # Make sure `allowed_file` checks file extension
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        thumbnail_path = filepath

    
    # print(data.get('status'),CourseStatus(data['status']))
    
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
        subcategory_id=subcategory_id,
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

    # except Exception as e:
    #     db.session.rollback()
    #     return jsonify({'error': str(e)}), 500
# edit specific course 

"""Edit a Specific course """
@course_bp.route('/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # ✅ Role check
        if not (
            user.role == UserRole.ADMIN or
            (user.role == UserRole.INSTRUCTOR and course.instructor_id == user.id)
        ):
            return jsonify({'error': 'Unauthorized to update this course'}), 403

        # ✅ Handle both JSON + form-data
        if request.content_type and "application/json" in request.content_type:
            data = request.get_json()
            file = None
        else:
            data = request.form
            file = request.files.get('thumbnail')

        # ✅ Update only if provided (no "title is required" check here)
        if data.get('title'):
            course.title = data['title']
        if data.get('description'):
            course.description = data['description']
        if data.get('short_description'):
            course.short_description = data['short_description']
        if data.get('price'):
            course.price = float(data['price'])
        if data.get('currency'):
            course.currency = data['currency']
        if data.get('duration_hours'):
            course.duration_hours = data['duration_hours']
        if data.get('difficulty_level'):
            course.difficulty_level = data['difficulty_level']
        if data.get('max_students'):
            course.max_students = int(data['max_students'])
        if data.get('prerequisites'):
            course.prerequisites = data['prerequisites']
        if data.get('learning_outcomes'):
            course.learning_outcomes = data['learning_outcomes']
        if data.get('subcategory_id'):
            course.subcategory_id = int(data['subcategory_id'])

        # ✅ Status update
        if data.get('status') and user.role in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
            try:
                course.status = CourseStatus(data['status'].lower())
            except ValueError:
                return jsonify({'error': f"Invalid status: {data['status']}"}), 400

        # ✅ Handle prerequisites mapping (many-to-many table)
        if "prerequisite_course_ids" in data:
            CoursePrerequisitesCourses.query.filter_by(course_id=course.id).delete()
            for pid in data["prerequisite_course_ids"]:
                db.session.add(
                    CoursePrerequisitesCourses(course_id=course.id, prerequisite_course_id=pid)
                )

        # ✅ Handle thumbnail upload
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            course.thumbnail = filepath

        db.session.commit()

        return jsonify({
            'message': 'Course updated successfully',
            'course': course.to_dict(include_modules=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

"""  delete courses   """
#delete course 
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


#create modules 
""" create modules with courses    """
@course_bp.route('/<int:course_id>/modules', methods=['POST'])
@instructor_required
def create_module(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN :
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
    
# get all modules
@course_bp.route('/modules', methods=['GET'])
@instructor_required
def list_all_modules():
    try:
        user = get_current_user()

        # Admins can see all, instructors only their own course modules
        if user.role == UserRole.ADMIN:
            modules = CourseModule.query.order_by(CourseModule.course_id, CourseModule.order).all()
        else:
            # restrict to modules in courses owned by this instructor
            modules = (
                CourseModule.query
                .join(Course, Course.id == CourseModule.course_id)
                .filter(Course.instructor_id == user.id)
                .order_by(CourseModule.course_id, CourseModule.order)
                .all()
            )

        return jsonify({
            "modules": [m.to_dict(include_lessons=True) for m in modules]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# get modules 
""" get a specific module   """
@course_bp.route('/<int:course_id>/modules', methods=['GET'])
@instructor_required
def list_modules(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Check role: instructor of the course or admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to view modules for this course'}), 403

        modules = CourseModule.query.filter_by(course_id=course_id).order_by(CourseModule.order).all()

        return jsonify({
            'course_id': course.id,
            'course_title': course.title,
            'modules': [m.to_dict(include_lessons=True) for m in modules]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# update module 
""" Edit a Specific Module   """
@course_bp.route('/<int:course_id>/modules/<int:module_id>', methods=['PUT'])
@instructor_required
def update_module(course_id, module_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)

        if not course or not module or module.course_id != course_id:
            return jsonify({'error': 'Course or module not found'}), 404

        # Check role: instructor of the course or admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to update this module'}), 403

        data = request.get_json()

        if 'title' in data:
            module.title = data['title']
        if 'description' in data:
            module.description = data['description']
        if 'is_preview' in data:
            module.is_preview = data['is_preview']

        db.session.commit()

        return jsonify({
            'message': 'Module updated successfully',
            'module': module.to_dict(include_lessons=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# delete module 
""" Delete a Specific Module  """
@course_bp.route('/<int:course_id>/modules/<int:module_id>', methods=['DELETE'])
@instructor_required
def delete_module(course_id, module_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)

        if not course or not module or module.course_id != course_id:
            return jsonify({'error': 'Course or module not found'}), 404

        # Check role: instructor of the course or admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to delete this module'}), 403

        db.session.delete(module)
        db.session.commit()

        return jsonify({'message': 'Module deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    






#create lesson
"""Create a lesson under a course/module """ 
@course_bp.route('/<int:course_id>/modules/<int:module_id>/lessons', methods=['POST'])
@instructor_required
def create_lesson(course_id, module_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)
        data = request.get_data()

        if not course or not module or module.course_id != course_id:
            return jsonify({'error': 'Course or module not found'}), 404

        # Check if user owns the course or is admin
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to modify this course'}), 403

        # Handle form data (supports file + text)
        title = request.form.get('title')
        content = request.form.get('content')
        duration_minutes = request.form.get('duration_minutes', type=int)
        is_preview = request.form.get('is_preview', 'false').lower() == 'true'
        video_file = request.files.get('video')

        print("title",title)

        if not title:
            return jsonify({'error': 'Lesson title is required'}), 400

        # Get next order number
        max_order = db.session.query(db.func.max(Lesson.order)).filter_by(module_id=module_id).scalar() or 0

        # Build safe folder names
        course_name = secure_filename(course.title)
        module_name = secure_filename(module.title)
        lesson_name = secure_filename(title)

        #case 1. local file upload 
        video_path = None
        if video_file and allowed_file_lessons(video_file.filename, ALLOWED_VIDEO_EXTENSIONS_LESSONS):
            video_folder = os.path.join(UPLOAD_FOLDER, course_name, module_name, 'video')
            os.makedirs(video_folder, exist_ok=True)
            video_filename = f"{lesson_name}_{secure_filename(video_file.filename)}"
            video_path = os.path.join(video_folder, video_filename)
            video_file.save(video_path)
                
        # Case 2: YouTube or remote URL
        # elif request.form.get('video_url'):
        #     video_path = request.form.get('video_url')
        # Create lesson entry
        lesson = Lesson(
            module_id=module_id,
            title=title,
            content=content,
            video_url=video_path,
            duration_minutes=duration_minutes,
            order=max_order + 1,
            is_preview=is_preview
        )
        db.session.add(lesson)
        db.session.commit()

        return jsonify({
            'message': 'Lesson created successfully',
            'lesson_id': lesson.id,
            'lesson': lesson.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# get all lessons in a course (flat list)
"""Get all lessons in a course"""
@course_bp.route('/<int:course_id>/all-lessons', methods=['GET'])
@instructor_required
def list_all_lessons_flat(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Role check
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to view lessons'}), 403

        # Fetch all lessons by joining modules
        lessons = (
            Lesson.query
            .join(CourseModule, Lesson.module_id == CourseModule.id)
            .filter(CourseModule.course_id == course_id)
            .order_by(Lesson.order)
            .all()
        )

        return jsonify({
            'course_id': course.id,
            'course_title': course.title,
            'lessons': [lesson.to_dict(include_resources=True) for lesson in lessons]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


        


# get lessons 
"""Get a lesson """
@course_bp.route('/<int:course_id>/modules/<int:module_id>/lessons', methods=['GET'])
@instructor_required
def list_lessons(course_id, module_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)

        if not course or not module or module.course_id != course_id:
            return jsonify({'error': 'Course or module not found'}), 404

        # Role check
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to view lessons'}), 403

        lessons = Lesson.query.filter_by(module_id=module_id).order_by(Lesson.order).all()

        return jsonify({
            'module_id': module.id,
            'module_title': module.title,
            'lessons': [lesson.to_dict() for lesson in lessons]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# update lesson 
@course_bp.route('/<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>', methods=['PUT'])
@instructor_required
def update_lesson(course_id, module_id, lesson_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)
        lesson = Lesson.query.get(lesson_id)

        if not course or not module or not lesson or module.course_id != course_id or lesson.module_id != module_id:
            return jsonify({'error': 'Course, module, or lesson not found'}), 404

        # Role check
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to update this lesson'}), 403

        data = request.form if request.form else request.get_json()

        if 'title' in data and data['title']:
            lesson.title = data['title']
        if 'content' in data:
            lesson.content = data['content']
        if 'duration_minutes' in data:
            lesson.duration_minutes = int(data['duration_minutes'])
        if 'is_preview' in data:
            lesson.is_preview = str(data['is_preview']).lower() == 'true'

        db.session.commit()

        return jsonify({
            'message': 'Lesson updated successfully',
            'lesson': lesson.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# delete lesson 
""" Delete a Lesson   """
@course_bp.route('/<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>', methods=['DELETE'])
@instructor_required
def delete_lesson(course_id, module_id, lesson_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        module = CourseModule.query.get(module_id)
        lesson = Lesson.query.get(lesson_id)

        if not course or not module or not lesson or module.course_id != course_id or lesson.module_id != module_id:
            return jsonify({'error': 'Course, module, or lesson not found'}), 404

        # Role check
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to delete this lesson'}), 403

        db.session.delete(lesson)
        db.session.commit()

        return jsonify({'message': 'Lesson deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

""" get your courses  """
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

# target-1 start from here 10 sept 
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
    


# get enrollments for specific course id 
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


 

# ------------------------------
# Existing flat list endpoint
# ------------------------------

""" Get all courses   types = ["published", "draft", "archived"] """
@course_bp.route('get-courses-master/', methods=['POST'])
def get_courses_master():
    try:
        data = request.get_json()
        types = ["published", "draft", "archived"]
        status = data.get('status', '').lower()

        query = Course.query

        if status:
            if status in types:
                query = query.filter_by(status=CourseStatus(status))
            elif status != 'all':
                return {"error": f"Invalid status: {status}"}

        # Filters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        difficulty = request.args.get('difficulty')
        instructor_id = request.args.get('instructor_id', type=int)
        search = request.args.get('search')

        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)

        if instructor_id:
            query = query.filter_by(instructor_id=instructor_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Course.title.ilike(search_term),
                    Course.description.ilike(search_term),
                    Course.short_description.ilike(search_term)
                )
            )

        # Pagination
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



"""Create only master categories"""
# Create MasterCategory only
@course_bp.route("/only-mastercategories", methods=["POST"])
def create_only_master_category():
    try:
        data = request.get_json()

        # Validate required field
        if "name" not in data or not data["name"].strip():
            return jsonify({"error": "Category name is required"}), 400

        # Create MasterCategory
        master = MasterCategory(name=data["name"].strip())
        db.session.add(master)
        db.session.commit()

        return jsonify({
            "message": "MasterCategory created successfully",
            "category": master.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

"""Get master Categories only"""
@course_bp.route('/only-mastercategories', methods=['GET'])
def get_master_categories_only():
    try:
        categories = MasterCategory.query.all()
        count = len(categories)

        # Convert SQLAlchemy objects into dictionaries
        categories_data = [
            {"id": cat.id, "name": cat.name}
            for cat in categories
        ]

        return jsonify({
            "message": "Master categories fetched successfully",
            "count": count,
            "categories": categories_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


"""Update MasterCategory"""
@course_bp.route('/only-mastercategories/<int:id>', methods=['PUT'])
def update_master_category_only(id):
    try:
        data = request.get_json()

        # Validate input
        if "name" not in data or not data["name"].strip():
            return jsonify({"error": "Category name is required"}), 400

        category = MasterCategory.query.get(id)
        if not category:
            return jsonify({"error": "MasterCategory not found"}), 404

        category.name = data["name"].strip()
        db.session.commit()

        return jsonify({
            "message": "MasterCategory updated successfully",
            "category": category.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


"""Delete MasterCategory"""
@course_bp.route('/only-mastercategories/<int:id>', methods=['DELETE'])
def delete_master_category_only(id):
    try:
        category = MasterCategory.query.get(id)
        if not category:
            return jsonify({"error": "MasterCategory not found"}), 404

        db.session.delete(category)
        db.session.commit()

        return jsonify({
            "message": "MasterCategory deleted successfully",
            "deleted_id": id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500





""" Master Categories with Subcategories     """



# base subcategory 
# get full category → subcategory → courses hierarchy
"""Get all the Master Courses with sub categories  """
@course_bp.route('mastercategories/', methods=['GET'])
def get_master_categories():
    try:
        categories = MasterCategory.query.all()
        return jsonify({
            "categories": [cat.to_dict() for cat in categories]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


"""Get all the Master Course with specific id """
@course_bp.route("/mastercategories/<int:category_id>", methods=["GET"])
def get_master_category(category_id):
    try:
        category = MasterCategory.query.get_or_404(category_id)
        return jsonify(category.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ✅ GET all master categories with their subcategories
"""Get Master Categories with SubCategories"""
@course_bp.route("/mastercourses_subcourses", methods=["GET"])
def get_master_courses():
    try:
        masters = MasterCategory.query.all()

        result = []
        for master in masters:
            result.append({
                "id": master.id,
                "mastercourse": master.name,
                "subcategories": [
                    {"id": sub.id, "name": sub.name} for sub in master.subcategories
                ]
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# target-1
# base mastercategory
# Create MasterCategory with SubCategories
"""Create  Master Courses with sub categories  """
@course_bp.route("/mastercategories", methods=["POST"])
def create_master_category():
    try:
        data = request.get_json()

        # Create MasterCategory
        master = MasterCategory(name=data["name"])
        db.session.add(master)
        db.session.flush()  # to get master.id before commit

        # Create SubCategories if provided
        if "subcategories" in data:
            for sub in data["subcategories"]:
                new_sub = SubCategory(
                    name=sub["name"],
                    master_category_id=master.id
                )
                db.session.add(new_sub)

        db.session.commit()

        return jsonify({"message": "MasterCategory created successfully", "category": master.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
"""Edit Master Courses"""
@course_bp.route("/mastercategories/<int:category_id>", methods=["PUT"])
def update_master_category(category_id):
    try:
        data = request.get_json()
        category = MasterCategory.query.get_or_404(category_id)



        # Update master category name
        if "name" in data:
            category.name = data["name"]

        # Update subcategories if provided
        if "subcategories" in data:
            # Clear old subcategories and replace with new
            SubCategory.query.filter_by(master_category_id=category.id).delete()

            for sub in data["subcategories"]:
                new_sub = SubCategory(
                    name=sub["name"],
                    master_category_id=category.id
                )
                db.session.add(new_sub)

        db.session.commit()
        return jsonify({"message": "MasterCategory updated successfully", "category": category.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    

""" Delete Master Category with specific id """
@course_bp.route("/mastercategories/<int:category_id>", methods=["DELETE"])
def delete_master_category(category_id):
    try:
        category = MasterCategory.query.get_or_404(category_id)

        # Delete subcategories first (if cascade is not configured in model)
        SubCategory.query.filter_by(master_category_id=category.id).delete()

        db.session.delete(category)
        db.session.commit()
        return jsonify({"message": "MasterCategory deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# target-2
# Create SubCategory only
"""Create subCategories """
@course_bp.route("/only-subcategories", methods=["POST"])
def create_only_subcategory():
    try:
        data = request.get_json()

        # Validate required fields
        if "master_category_id" not in data:
            return jsonify({"error": "master_category_id is required"}), 400
        if "name" not in data or not data["name"].strip():
            return jsonify({"error": "SubCategory name is required"}), 400

        # Check if master category exists
        master = MasterCategory.query.get(data["master_category_id"])
        if not master:
            return jsonify({"error": "MasterCategory not found"}), 404

        # Create SubCategory
        subcategory = SubCategory(
            name=data["name"].strip(),
            master_category_id=master.id
        )   
        db.session.add(subcategory)
        db.session.commit()

        return jsonify({
            "message": "SubCategory created successfully",
            "subcategory": subcategory.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# ✅ GET all subcategories
"""Get All Subcategories with courses"""
@course_bp.route("/only-subcategories", methods=["GET"])
def get_all_subcategories():
    try:
        subcategories = SubCategory.query.all()
        return jsonify([sub.to_dict() for sub in subcategories]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ✅ GET single subcategory by ID
""" GET single subcategory by ID"""
@course_bp.route("/only-subcategories/<int:subcategory_id>", methods=["GET"])
def get_subcategory(subcategory_id):
    try:
        subcategory = SubCategory.query.get_or_404(subcategory_id)
        return jsonify(subcategory.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ✅ UPDATE subcategory
"""Update Category with specific id """
@course_bp.route("/only-subcategories/<int:subcategory_id>", methods=["PUT"])
def update_subcategory(subcategory_id):
    try:
        data = request.get_json()
        subcategory = SubCategory.query.get_or_404(subcategory_id)

        # Update name if provided
        if "name" in data and data["name"].strip():
            subcategory.name = data["name"].strip()

        # Update master_category_id if provided
        if "master_category_id" in data:
            master = MasterCategory.query.get(data["master_category_id"])
            if not master:
                return jsonify({"error": "MasterCategory not found"}), 404
            subcategory.master_category_id = master.id

        db.session.commit()
        return jsonify({
            "message": "SubCategory updated successfully",
            "subcategory": subcategory.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400



# ✅ DELETE subcategory
"""Delete Subcategory"""
@course_bp.route("/only-subcategories/<int:subcategory_id>", methods=["DELETE"])
def delete_subcategory(subcategory_id):
    try:
        subcategory = SubCategory.query.get_or_404(subcategory_id)
        db.session.delete(subcategory)
        db.session.commit()
        return jsonify({"message": "SubCategory deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# ✅ GET all subcategories with their respective master categories
"""Get All Subcategories with their Master Categories"""
@course_bp.route("/only-subcategories_alone", methods=["GET"])
def get_all_subcategories_alone():
    try:
        subcategories = SubCategory.query.all()

        result = []
        for sub in subcategories:
            result.append({
                "id": sub.id,
                "name": sub.name,
                "master_category": {
                    "id": sub.master_category.id,
                    "name": sub.master_category.name
                }
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400



""" create subcategoires with master category  """
# Create SubCategory with Courses
@course_bp.route("/subcategories", methods=["POST"])
def create_subcategory_with_courses():
    try:
        data = request.get_json()

        # Validate MasterCategory exists
        master = MasterCategory.query.get(data["master_category_id"])
        if not master:
            return jsonify({"error": "MasterCategory not found"}), 404

        # Create SubCategory
        subcategory = SubCategory(
            name=data["name"],
            master_category_id=master.id
        )
        db.session.add(subcategory)
        db.session.flush()  # get subcategory.id before commit

        # Add Courses if provided
        if "courses" in data:
            for c in data["courses"]:
                new_course = Course(
                    title=c["title"],
                    description=c.get("description", ""),
                    subcategory_id=subcategory.id
                )
                db.session.add(new_course)

        db.session.commit()

        return jsonify({
            "message": "SubCategory with courses created successfully",
            "subcategory": subcategory.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    


"Create a course under a subcategory"
#  Create a Course under a SubCategory
@course_bp.route("/subcategory/courses", methods=["POST"])
def create_course_subcategory():
    try:
        data = request.get_json()

        # Validate SubCategory
        subcategory = SubCategory.query.get(data["subcategory_id"])
        if not subcategory:
            return jsonify({"error": "SubCategory not found"}), 404

        # Create Course
        course = Course(
            title=data["title"],
            description=data.get("description", ""),
            subcategory_id=subcategory.id
        )
        db.session.add(course)
        db.session.commit()

        return jsonify({
            "message": "Course created successfully",
            "course": {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "subcategory_id": course.subcategory_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400




"""Get All Courses Details"""
@course_bp.route("/categories-with-courses", methods=["GET"])
def get_categories_with_courses():
    try:
        categories = MasterCategory.query.all()
        response = {}

        for category in categories:
            sub_dict = {}
            for sub in category.subcategories:
                sub_dict[sub.name] = [course.to_dict(include_modules=True) for course in sub.courses]
            response[category.name] = sub_dict

        return jsonify({
            "success": True,
            "data": response
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500




import os
from werkzeug.utils import secure_filename
from models import db, LessonResource
from datetime import datetime


# Folder to save uploads
UPLOAD_FOLDER = os.path.join("static", "uploads", "resources")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "mp4", "mp3", "wav", "avi", "mov", "docx", "pptx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -------------------------------
# Create a Lesson Resource with File Upload
# -------------------------------
@course_bp.route("/lesson-resources", methods=["POST"])
def create_lesson_resource():
    try:
        lesson_id = request.form.get("lesson_id")
        title = request.form.get("title")

        if not lesson_id or not title:
            return jsonify({"error": "lesson_id and title are required"}), 400

        # Handle file upload
        if "file" not in request.files:
            return jsonify({"error": "File is required"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Example: courseid_moduleid_lessonid_lessonresourse.ext
        course_id = request.form.get("course_id", "course")
        module_id = request.form.get("module_id", "module")

        filename = secure_filename(file.filename)
        extension = filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{course_id}_{module_id}_{lesson_id}_{title.replace(' ', '_')}.{extension}"

        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)

        # Create DB entry
        resource = LessonResource(
            lesson_id=lesson_id,
            title=title,
            file_path=file_path.replace("\\", "/"),  # store forward slashes
            file_type=extension,
            file_size=os.path.getsize(file_path),
            created_at=datetime.utcnow()
        )

        db.session.add(resource)
        db.session.commit()

        return jsonify(resource.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# -------------------------------
# READ ALL (GET)
# -------------------------------
@course_bp.route("/lesson-resources", methods=["GET"])
def get_all_resources():
    try:
        resources = LessonResource.query.all()
        return jsonify([res.to_dict() for res in resources]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# -------------------------------
# READ SINGLE (GET by ID)
# -------------------------------
@course_bp.route("/lesson-resources/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    resource = LessonResource.query.get(resource_id)
    if not resource:
        return jsonify({"error": "Resource not found"}), 404
    return jsonify(resource.to_dict()), 200



# -------------------------------
# UPDATE (PUT) with file replacement
# -------------------------------
@course_bp.route("/lesson-resources/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    try:
        resource = LessonResource.query.get(resource_id)
        if not resource:
            return jsonify({"error": "Resource not found"}), 404

        title = request.form.get("title", resource.title)
        resource.title = title
        resource.lesson_id = request.form.get("lesson_id", resource.lesson_id)

        # Handle file update if a new one is uploaded
        if "file" in request.files:
            file = request.files["file"]
            if file.filename != "" and allowed_file(file.filename):
                # Delete old file
                if os.path.exists(resource.file_path):
                    os.remove(resource.file_path)

                course_id = request.form.get("course_id", "course")
                module_id = request.form.get("module_id", "module")

                filename = secure_filename(file.filename)
                ext = filename.rsplit(".", 1)[1].lower()
                unique_filename = f"{course_id}_{module_id}_{resource.lesson_id}_{title.replace(' ', '_')}.{ext}"

                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)

                resource.file_path = file_path.replace("\\", "/")
                resource.file_type = ext
                resource.file_size = os.path.getsize(file_path)

        db.session.commit()
        return jsonify(resource.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# -------------------------------
# DELETE (remove from DB + file)
# -------------------------------

@course_bp.route("/lesson-resources/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    try:
        resource = LessonResource.query.get(resource_id)
        if not resource:
            return jsonify({"error": "Resource not found"}), 404

        # Delete file from disk
        if resource.file_path and os.path.exists(resource.file_path):
            os.remove(resource.file_path)

        db.session.delete(resource)
        db.session.commit()

        return jsonify({"message": "Resource deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500