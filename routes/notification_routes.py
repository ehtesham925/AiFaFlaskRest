from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from models import Notification, User
from auth import get_current_user, admin_required
from services.email_service import EmailService

notification_bp = Blueprint('notifications', __name__)

# get notifications 
@notification_bp.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = Notification.query.filter_by(user_id=user.id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'notifications': [notification.to_dict() for notification in notifications.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': notifications.total,
                'pages': notifications.pages,
                'has_next': notifications.has_next,
                'has_prev': notifications.has_prev
            },
            'unread_count': Notification.query.filter_by(user_id=user.id, is_read=False).count()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# mark as read for specific  notifications
@notification_bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        notification = Notification.query.get(notification_id)
        if not notification or notification.user_id != user.id:
            return jsonify({'error': 'Notification not found'}), 404
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'message': 'Notification marked as read',
            'notification': notification.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# mark all as read for notifications
@notification_bp.route('/mark-all-read', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        
        return jsonify({'message': 'All notifications marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# delete notification
@notification_bp.route('/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        notification = Notification.query.get(notification_id)
        if not notification or notification.user_id != user.id:
            return jsonify({'error': 'Notification not found'}), 404
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({'message': 'Notification deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# create / send notification
@notification_bp.route('/send', methods=['POST'])
@admin_required
def send_notification():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'message', 'user_ids']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        user_ids = data['user_ids']
        title = data['title']
        message = data['message']
        notification_type = data.get('type', 'general')
        send_email = data.get('send_email', False)
        
        # Validate user IDs
        if not isinstance(user_ids, list):
            return jsonify({'error': 'user_ids must be a list'}), 400
        
        # Get valid users
        users = User.query.filter(User.id.in_(user_ids), User.is_active == True).all()
        if not users:
            return jsonify({'error': 'No valid users found'}), 400
        
        notifications_created = []
        email_service = EmailService() if send_email else None
        
        for user in users:
            # Create notification
            notification = Notification(
                user_id=user.id,
                title=title,
                message=message,
                type=notification_type
            )
            db.session.add(notification)
            notifications_created.append(notification)
            
            # Send email if requested
            if send_email and email_service:
                try:
                    email_service.send_notification_email(user, title, message)
                except Exception as e:
                    # Log email error but don't fail the whole operation
                    print(f"Failed to send email to {user.email}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'message': f'Notifications sent to {len(notifications_created)} users',
            'notifications_sent': len(notifications_created),
            'email_sent': send_email
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# send notifications for all users 
@notification_bp.route('/broadcast', methods=['POST'])
@admin_required
def broadcast_notification():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'message']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        title = data['title']
        message = data['message']
        notification_type = data.get('type', 'general')
        send_email = data.get('send_email', False)
        user_role = data.get('user_role')  # optional: target specific role
        
        # Get target users
        query = User.query.filter_by(is_active=True)
        if user_role:
            from models import UserRole
            query = query.filter_by(role=UserRole(user_role))
        
        users = query.all()
        
        if not users:
            return jsonify({'error': 'No users found to send notifications to'}), 400
        
        notifications_created = []
        email_service = EmailService() if send_email else None
        
        for user in users:
            # Create notification
            notification = Notification(
                user_id=user.id,
                title=title,
                message=message,
                type=notification_type
            )
            db.session.add(notification)
            notifications_created.append(notification)
            
            # Send email if requested
            if send_email and email_service:
                try:
                    email_service.send_notification_email(user, title, message)
                except Exception as e:
                    # Log email error but don't fail the whole operation
                    print(f"Failed to send email to {user.email}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'message': f'Broadcast notification sent to {len(notifications_created)} users',
            'notifications_sent': len(notifications_created),
            'email_sent': send_email,
            'target_role': user_role or 'all'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# notifications unread count 
@notification_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
        
        return jsonify({'unread_count': unread_count}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# notification settings 
@notification_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_notification_settings():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # In a real implementation, you would have a notification_settings table
        # For now, return default settings
        settings = {
            'email_notifications': True,
            'course_updates': True,
            'payment_notifications': True,
            'certificate_notifications': True,
            'live_session_reminders': True,
            'marketing_emails': False
        }
        
        return jsonify({'settings': settings}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# updating notification settings 
@notification_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_notification_settings():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # In a real implementation, you would update the notification_settings table
        # For now, just return success
        
        return jsonify({
            'message': 'Notification settings updated successfully',
            'settings': data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
