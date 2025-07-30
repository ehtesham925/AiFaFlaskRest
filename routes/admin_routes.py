from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from models import User, Course, Enrollment, Payment, UserRole, CourseStatus, PaymentStatus
from auth import admin_required, get_current_user
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    try:
        # Get statistics
        total_users = User.query.count()
        total_students = User.query.filter_by(role=UserRole.STUDENT).count()
        total_instructors = User.query.filter_by(role=UserRole.INSTRUCTOR).count()
        total_courses = Course.query.count()
        published_courses = Course.query.filter_by(status=CourseStatus.PUBLISHED).count()
        total_enrollments = Enrollment.query.filter_by(is_active=True).count()
        
        # Payment statistics
        total_revenue = db.session.query(func.sum(Payment.amount)).filter_by(status=PaymentStatus.COMPLETED).scalar() or 0
        this_month_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == PaymentStatus.COMPLETED,
            Payment.created_at >= datetime.utcnow().replace(day=1)
        ).scalar() or 0
        
        # Recent activity
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
        recent_enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).limit(10).all()
        recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
        
        return jsonify({
            'statistics': {
                'total_users': total_users,
                'total_students': total_students,
                'total_instructors': total_instructors,
                'total_courses': total_courses,
                'published_courses': published_courses,
                'total_enrollments': total_enrollments,
                'total_revenue': float(total_revenue),
                'this_month_revenue': float(this_month_revenue)
            },
            'recent_activity': {
                'users': [user.to_dict() for user in recent_users],
                'enrollments': [
                    {
                        'enrollment': enrollment.to_dict(),
                        'user': enrollment.user.to_dict(),
                        'course': enrollment.course.to_dict()
                    }
                    for enrollment in recent_enrollments
                ],
                'payments': [payment.to_dict() for payment in recent_payments]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role = request.args.get('role')
        search = request.args.get('search')
        
        query = User.query
        
        if role:
            query = query.filter_by(role=UserRole(role))
        
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': users.total,
                'pages': users.pages,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's enrollments
        enrollments = Enrollment.query.filter_by(user_id=user_id).all()
        enrollment_data = []
        for enrollment in enrollments:
            course_data = enrollment.course.to_dict()
            course_data['enrollment'] = enrollment.to_dict()
            enrollment_data.append(course_data)
        
        # Get user's payments
        payments = Payment.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'user': user.to_dict(),
            'enrollments': enrollment_data,
            'payments': [payment.to_dict() for payment in payments]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update user fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            # Check if email is already taken
            existing_user = User.query.filter_by(email=data['email'].lower()).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already taken'}), 409
            user.email = data['email'].lower()
        if 'role' in data:
            user.role = UserRole(data['role'])
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'phone' in data:
            user.phone = data['phone']
        if 'bio' in data:
            user.bio = data['bio']
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has active enrollments
        active_enrollments = Enrollment.query.filter_by(user_id=user_id, is_active=True).count()
        if active_enrollments > 0:
            return jsonify({'error': 'Cannot delete user with active enrollments'}), 400
        
        # Deactivate instead of delete to preserve data integrity
        user.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'User deactivated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses', methods=['GET'])
@admin_required
def get_all_courses():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        instructor_id = request.args.get('instructor_id', type=int)
        
        query = Course.query
        
        if status:
            query = query.filter_by(status=CourseStatus(status))
        
        if instructor_id:
            query = query.filter_by(instructor_id=instructor_id)
        
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

@admin_bp.route('/courses/<int:course_id>/status', methods=['PUT'])
@admin_required
def update_course_status(course_id):
    try:
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        data = request.get_json()
        if 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        course.status = CourseStatus(data['status'])
        db.session.commit()
        
        return jsonify({
            'message': 'Course status updated successfully',
            'course': course.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/payments', methods=['GET'])
@admin_required
def get_all_payments():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        user_id = request.args.get('user_id', type=int)
        course_id = request.args.get('course_id', type=int)
        
        query = Payment.query
        
        if status:
            query = query.filter_by(status=PaymentStatus(status))
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        payments = query.order_by(Payment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Include user and course details
        payment_data = []
        for payment in payments.items:
            payment_dict = payment.to_dict()
            payment_dict['user'] = payment.user.to_dict()
            payment_dict['course'] = payment.course.to_dict()
            payment_data.append(payment_dict)
        
        return jsonify({
            'payments': payment_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': payments.total,
                'pages': payments.pages,
                'has_next': payments.has_next,
                'has_prev': payments.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/enrollments', methods=['GET'])
@admin_required
def get_all_enrollments():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        course_id = request.args.get('course_id', type=int)
        user_id = request.args.get('user_id', type=int)
        
        query = Enrollment.query
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        enrollments = query.order_by(Enrollment.enrolled_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Include user and course details
        enrollment_data = []
        for enrollment in enrollments.items:
            enrollment_dict = enrollment.to_dict()
            enrollment_dict['user'] = enrollment.user.to_dict()
            enrollment_dict['course'] = enrollment.course.to_dict()
            enrollment_data.append(enrollment_dict)
        
        return jsonify({
            'enrollments': enrollment_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': enrollments.total,
                'pages': enrollments.pages,
                'has_next': enrollments.has_next,
                'has_prev': enrollments.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics():
    try:
        # Revenue analytics
        revenue_by_month = db.session.query(
            func.date_trunc('month', Payment.created_at).label('month'),
            func.sum(Payment.amount).label('revenue')
        ).filter_by(status=PaymentStatus.COMPLETED).group_by('month').order_by('month').all()
        
        # Enrollment analytics
        enrollments_by_month = db.session.query(
            func.date_trunc('month', Enrollment.enrolled_at).label('month'),
            func.count(Enrollment.id).label('enrollments')
        ).group_by('month').order_by('month').all()
        
        # Popular courses
        popular_courses = db.session.query(
            Course.id,
            Course.title,
            func.count(Enrollment.id).label('enrollment_count')
        ).join(Enrollment).group_by(Course.id, Course.title)\
         .order_by(func.count(Enrollment.id).desc()).limit(10).all()
        
        return jsonify({
            'revenue_by_month': [
                {
                    'month': revenue.month.strftime('%Y-%m'),
                    'revenue': float(revenue.revenue)
                }
                for revenue in revenue_by_month
            ],
            'enrollments_by_month': [
                {
                    'month': enrollment.month.strftime('%Y-%m'),
                    'enrollments': enrollment.enrollments
                }
                for enrollment in enrollments_by_month
            ],
            'popular_courses': [
                {
                    'course_id': course.id,
                    'title': course.title,
                    'enrollment_count': course.enrollment_count
                }
                for course in popular_courses
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>/promote-instructor', methods=['POST'])
@admin_required
def promote_to_instructor(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role == UserRole.INSTRUCTOR:
            return jsonify({'error': 'User is already an instructor'}), 400
        
        user.role = UserRole.INSTRUCTOR
        db.session.commit()
        
        return jsonify({
            'message': 'User promoted to instructor successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
