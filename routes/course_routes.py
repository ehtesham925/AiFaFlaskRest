from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models import Course, CourseModule, Lesson, User, Enrollment, UserRole, CourseStatus,MasterCategory,SubCategory
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

# get specific course
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
@course_bp.route('/<int:course_id>', methods=['PUT'])
# @instructor_required
def update_course(course_id):
    try:
        user = get_current_user()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # ✅ Allow Admin to update any course, Instructor only their own
        if not (
            user.role == UserRole.ADMIN or
            (user.role == UserRole.INSTRUCTOR and course.instructor_id == user.id)
        ):
            return jsonify({'error': 'Unauthorized to update this course'}), 403

        # ✅ Support form data + file upload
        data = request.form
        file = request.files.get('thumbnail')

        # Update text/number fields if present
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

        # ✅ Handle status update for Admin and Instructor
        if data.get('status') and user.role in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
            try:
                course.status = CourseStatus(data['status'].lower())
            except ValueError:
                return jsonify({'error': f"Invalid status: {data['status']}"}), 400

        # ✅ Handle thumbnail upload (optional)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            course.thumbnail = filepath  # update thumbnail path

        db.session.commit()

        return jsonify({
            'message': 'Course updated successfully',
            'course': course.to_dict(include_modules=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
    
#create lesson 
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


 
# get modules 
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
    



# get lessons 
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

# ------------------------------
# Existing flat list endpoint
# ------------------------------
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


# ------------------------------
# New hierarchical endpoint
# ------------------------------


# get full category → subcategory → courses hierarchy
@course_bp.route('get-master-categories/', methods=['GET'])
def get_master_categories():
    try:
        categories = MasterCategory.query.all()
        return jsonify({
            "categories": [cat.to_dict() for cat in categories]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Create MasterCategory with SubCategories
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




@course_bp.route('/create-courses-new', methods=['POST'])
# @instructor_required
def create_course_new():
    try:
        print("FORM DATA:", request.form)
        print("FILES:", request.files)

        user = get_current_user()

        # Detect request type: JSON or form-data
        if request.is_json:
            data = request.get_json()
            file = None
        else:
            data = request.form.to_dict()  # convert MultiDict → dict
            file = request.files.get('thumbnail')

        # Validate required fields
        required_fields = ['title', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Handle thumbnail (URL or file)
        thumbnail_path = None
        global UPLOAD_FOLDER
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            thumbnail_path = filepath
        elif data.get("thumbnail"):  
            # If JSON contains a URL string
            thumbnail_path = data.get("thumbnail")

        # Handle course status safely
        if data.get('status'):
            try:
                status = CourseStatus(data['status'].lower())
            except ValueError:
                return jsonify({'error': f"Invalid status: {data['status']}"}), 400
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
            duration_hours=float(data.get('duration_hours', 0)) if data.get('duration_hours') else None,
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
