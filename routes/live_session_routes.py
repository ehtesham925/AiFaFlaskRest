from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from models import LiveSession, Course, User, Enrollment, UserRole
from auth import get_current_user, instructor_required
from datetime import datetime, timedelta,timezone
from services.email_service import EmailService

live_session_bp = Blueprint('live_sessions', __name__)

# get live sessions 
""" Get Live Sessions    """
@live_session_bp.route('/', methods=['GET'])
@jwt_required()
def get_live_sessions():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        course_id = request.args.get('course_id', type=int)
        upcoming_only = request.args.get('upcoming_only', 'false').lower() == 'true'
        
        # Build query based on user role
        if user.role == UserRole.ADMIN:
            query = LiveSession.query
        elif user.role == UserRole.INSTRUCTOR:
            # Instructors can see sessions for their courses
            course_ids = [course.id for course in user.courses_taught]
            query = LiveSession.query.filter(LiveSession.course_id.in_(course_ids))
        else:
            # Students can see sessions for courses they're enrolled in
            enrolled_course_ids = [enrollment.course_id for enrollment in user.enrollments if enrollment.is_active]
            query = LiveSession.query.filter(LiveSession.course_id.in_(enrolled_course_ids))
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        if upcoming_only:
            query = query.filter(LiveSession.scheduled_at > datetime.utcnow())
        
        sessions = query.order_by(LiveSession.scheduled_at.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        session_data = []
        for session in sessions.items:
            session_dict = session.to_dict()
            session_dict['course'] = session.course.to_dict()
            session_data.append(session_dict)
        
        return jsonify({
            'live_sessions': session_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': sessions.total,
                'pages': sessions.pages,
                'has_next': sessions.has_next,
                'has_prev': sessions.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# create live sessions
"""  Create live sessions and demo here       """ 
@live_session_bp.route('/', methods=['POST'])
@instructor_required
def create_live_session():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['course_id', 'title', 'scheduled_at', 'duration_minutes']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        course_id = data['course_id']
        
        # Verify course exists and user has permission
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to create sessions for this course'}), 403
        
        # Parse scheduled time
        try:
            scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid scheduled_at format. Use ISO format.'}), 400
        
        # Validate scheduled time is in the future
        if scheduled_at <= datetime.now(timezone.utc):
            return jsonify({'error': 'Scheduled time must be in the future'}), 400
        
        # Create live session
        live_session = LiveSession(
            course_id=course_id,
            title=data['title'],
            description=data.get('description'),
            scheduled_at=scheduled_at,
            duration_minutes=data['duration_minutes'],
            meeting_url=data.get('meeting_url'),
            meeting_id=data.get('meeting_id'),
            meeting_password=data.get('meeting_password'),
            is_recorded=data.get('is_recorded', False)
        )
        
        db.session.add(live_session)
        db.session.commit()
        
        # Send notifications to enrolled students
        try:
            email_service = EmailService()
            enrollments = Enrollment.query.filter_by(course_id=course_id, is_active=True).all()
            
            for enrollment in enrollments:
                email_service.send_live_session_notification(
                    user=enrollment.user,
                    course=course,
                    session=live_session
                )
        except Exception as e:
            # Log email error but don't fail the session creation
            print(f"Failed to send session notifications: {str(e)}")
        
        return jsonify({
            'message': 'Live session created successfully',
            'live_session': live_session.to_dict()
        }), 201
        
    except Exception as e:  
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# get perticular session
""" get perticular session  """ 
@live_session_bp.route('/<int:session_id>', methods=['GET'])
@jwt_required()
def get_live_session(session_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        session = LiveSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Live session not found'}), 404
        
        course = session.course
        
        # Check if user has access to this session
        has_access = False
        
        if user.role == UserRole.ADMIN or course.instructor_id == user.id:
            has_access = True
        else:
            # Check if user is enrolled in the course
            enrollment = Enrollment.query.filter_by(
                user_id=user.id,
                course_id=course.id,
                is_active=True
            ).first()
            has_access = enrollment is not None
        
        if not has_access:
            return jsonify({'error': 'Access denied'}), 403
        
        session_dict = session.to_dict()
        session_dict['course'] = course.to_dict()
        
        return jsonify({'live_session': session_dict}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# update perticular session
""" update perticular session """ 
@live_session_bp.route('/<int:session_id>', methods=['PUT'])
@instructor_required
def update_live_session(session_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        session = LiveSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Live session not found'}), 404
        
        course = session.course
        
        # Check if user has permission to update
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to update this session'}), 403
        
        data = request.get_json()
        
        # Update session fields
        if 'title' in data:
            session.title = data['title']
        if 'description' in data:
            session.description = data['description']
        if 'scheduled_at' in data:
            try:
                scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
                if scheduled_at <= datetime.utcnow():
                    return jsonify({'error': 'Scheduled time must be in the future'}), 400
                session.scheduled_at = scheduled_at
            except ValueError:
                return jsonify({'error': 'Invalid scheduled_at format. Use ISO format.'}), 400
        if 'duration_minutes' in data:
            session.duration_minutes = data['duration_minutes']
        if 'meeting_url' in data:
            session.meeting_url = data['meeting_url']
        if 'meeting_id' in data:
            session.meeting_id = data['meeting_id']
        if 'meeting_password' in data:
            session.meeting_password = data['meeting_password']
        if 'is_recorded' in data:
            session.is_recorded = data['is_recorded']
        if 'recording_url' in data:
            session.recording_url = data['recording_url']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Live session updated successfully',
            'live_session': session.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# delete session
""" Delete perticular session """
@live_session_bp.route('/<int:session_id>', methods=['DELETE'])
@instructor_required
def delete_live_session(session_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        session = LiveSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Live session not found'}), 404
        
        course = session.course
        
        # Check if user has permission to delete
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return jsonify({'error': 'Unauthorized to delete this session'}), 403
        
        # Check if session has already started
        if session.scheduled_at <= datetime.utcnow():
            return jsonify({'error': 'Cannot delete a session that has already started'}), 400
        
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({'message': 'Live session deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

""" Get Upcomming Courses   """
@live_session_bp.route('/upcoming', methods=['GET'])
@jwt_required()
def get_upcoming_sessions():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get sessions for the next 7 days
        end_date = datetime.utcnow() + timedelta(days=7)
        
        # Build query based on user role
        if user.role == UserRole.ADMIN:
            sessions = LiveSession.query.filter(
                LiveSession.scheduled_at.between(datetime.utcnow(), end_date)
            ).order_by(LiveSession.scheduled_at.asc()).all()
        elif user.role == UserRole.INSTRUCTOR:
            course_ids = [course.id for course in user.courses_taught]
            sessions = LiveSession.query.filter(
                LiveSession.course_id.in_(course_ids),
                LiveSession.scheduled_at.between(datetime.utcnow(), end_date)
            ).order_by(LiveSession.scheduled_at.asc()).all()
        else:
            enrolled_course_ids = [enrollment.course_id for enrollment in user.enrollments if enrollment.is_active]
            sessions = LiveSession.query.filter(
                LiveSession.course_id.in_(enrolled_course_ids),
                LiveSession.scheduled_at.between(datetime.utcnow(), end_date)
            ).order_by(LiveSession.scheduled_at.asc()).all()
        
        session_data = []
        for session in sessions:
            session_dict = session.to_dict()
            session_dict['course'] = session.course.to_dict()
            session_data.append(session_dict)
        
        return jsonify({'upcoming_sessions': session_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

""" Get live sessions of perticular course   """
@live_session_bp.route('/course/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course_sessions(course_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user has access to this course
        has_access = False
        
        if user.role == UserRole.ADMIN or course.instructor_id == user.id:
            has_access = True
        else:
            enrollment = Enrollment.query.filter_by(
                user_id=user.id,
                course_id=course_id,
                is_active=True
            ).first()
            has_access = enrollment is not None
        
        if not has_access:
            return jsonify({'error': 'Access denied'}), 403
        
        sessions = LiveSession.query.filter_by(course_id=course_id)\
            .order_by(LiveSession.scheduled_at.asc()).all()
        
        return jsonify({
            'course_id': course_id,
            'course_title': course.title,
            'live_sessions': [session.to_dict() for session in sessions]
        }), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@live_session_bp.route('/<int:session_id>/join', methods=['GET'])
@jwt_required()
def join_session(session_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        session = LiveSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Live session not found'}), 404
        
        course = session.course
        
        # Check if user has access to this session
        has_access = False
        
        if user.role == UserRole.ADMIN or course.instructor_id == user.id:
            has_access = True
        else:
            enrollment = Enrollment.query.filter_by(
                user_id=user.id,
                course_id=course.id,
                is_active=True
            ).first()
            has_access = enrollment is not None
        
        if not has_access:
            return jsonify({'error': 'Access denied. Please enroll in the course first.'}), 403
        
        # Check if session is happening now (within 15 minutes before or after start time)
        session_start = session.scheduled_at
        session_end = session_start + timedelta(minutes=session.duration_minutes)
        now = datetime.utcnow()
        
        if now < session_start - timedelta(minutes=15):
            return jsonify({
                'error': 'Session has not started yet',
                'scheduled_at': session.scheduled_at.isoformat(),
                'can_join_at': (session_start - timedelta(minutes=15)).isoformat()
            }), 400
        
        if now > session_end:
            return jsonify({
                'error': 'Session has ended',
                'ended_at': session_end.isoformat(),
                'recording_url': session.recording_url
            }), 400
        
        # Return join information
        join_info = {
            'session_id': session.id,
            'title': session.title,
            'meeting_url': session.meeting_url,
            'meeting_id': session.meeting_id,
            'meeting_password': session.meeting_password,
            'scheduled_at': session.scheduled_at.isoformat(),
            'duration_minutes': session.duration_minutes,
            'course': course.to_dict()
        }
        
        return jsonify({'join_info': join_info}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
