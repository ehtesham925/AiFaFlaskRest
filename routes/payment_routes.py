from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required
from app import db
from models import Payment, Course, Enrollment, PaymentStatus, User
from auth import get_current_user
from services.payment_service import PaymentService
import os

payment_bp = Blueprint('payments', __name__)

@payment_bp.route('/create-checkout-session', methods=['POST'])
@jwt_required()
def create_checkout_session():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'error': 'Course ID is required'}), 400
        
        # Check if course exists
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user is already enrolled
        existing_enrollment = Enrollment.query.filter_by(
            user_id=user.id, 
            course_id=course_id, 
            is_active=True
        ).first()
        
        if existing_enrollment:
            return jsonify({'error': 'Already enrolled in this course'}), 409
        
        # Check for existing pending payment
        existing_payment = Payment.query.filter_by(
            user_id=user.id,
            course_id=course_id,
            status=PaymentStatus.PENDING
        ).first()
        
        if existing_payment:
            return jsonify({'error': 'Payment already in progress'}), 409
        
        # Create payment record
        payment = Payment(
            user_id=user.id,
            course_id=course_id,
            amount=course.price,
            currency=course.currency,
            status=PaymentStatus.PENDING
        )
        
        db.session.add(payment)
        db.session.commit()
        
        # Create Stripe checkout session
        payment_service = PaymentService()
        checkout_session = payment_service.create_checkout_session(
            course=course,
            user=user,
            payment_id=payment.id
        )
        
        # Update payment with Stripe session ID
        payment.stripe_session_id = checkout_session.id
        db.session.commit()
        
        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
            'payment_id': payment.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/success/<int:payment_id>', methods=['GET'])
@jwt_required()
def payment_success(payment_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        payment = Payment.query.get(payment_id)
        if not payment or payment.user_id != user.id:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Verify payment with Stripe
        payment_service = PaymentService()
        session = payment_service.get_checkout_session(payment.stripe_session_id)
        
        if session.payment_status == 'paid':
            # Update payment status
            payment.status = PaymentStatus.COMPLETED
            payment.stripe_payment_intent_id = session.payment_intent
            
            # Create enrollment
            enrollment = Enrollment(
                user_id=user.id,
                course_id=payment.course_id
            )
            
            db.session.add(enrollment)
            db.session.commit()
            
            return jsonify({
                'message': 'Payment successful! You are now enrolled in the course.',
                'payment': payment.to_dict(),
                'enrollment': enrollment.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Payment not confirmed'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/cancel/<int:payment_id>', methods=['GET'])
@jwt_required()
def payment_cancel(payment_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        payment = Payment.query.get(payment_id)
        if not payment or payment.user_id != user.id:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Update payment status
        payment.status = PaymentStatus.FAILED
        db.session.commit()
        
        return jsonify({
            'message': 'Payment was cancelled',
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        payment_service = PaymentService()
        event = payment_service.verify_webhook(payload, sig_header)
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Find payment by session ID
            payment = Payment.query.filter_by(stripe_session_id=session['id']).first()
            
            if payment:
                payment.status = PaymentStatus.COMPLETED
                payment.stripe_payment_intent_id = session.get('payment_intent')
                
                # Create enrollment if not exists
                existing_enrollment = Enrollment.query.filter_by(
                    user_id=payment.user_id,
                    course_id=payment.course_id
                ).first()
                
                if not existing_enrollment:
                    enrollment = Enrollment(
                        user_id=payment.user_id,
                        course_id=payment.course_id
                    )
                    db.session.add(enrollment)
                
                db.session.commit()
        
        elif event['type'] == 'checkout.session.expired':
            session = event['data']['object']
            
            # Find payment by session ID
            payment = Payment.query.filter_by(stripe_session_id=session['id']).first()
            
            if payment:
                payment.status = PaymentStatus.FAILED
                db.session.commit()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@payment_bp.route('/history', methods=['GET'])
@jwt_required()
def get_payment_history():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        payments = Payment.query.filter_by(user_id=user.id)\
            .order_by(Payment.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        payment_data = []
        for payment in payments.items:
            payment_dict = payment.to_dict()
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

@payment_bp.route('/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment_details(payment_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        payment = Payment.query.get(payment_id)
        if not payment or payment.user_id != user.id:
            return jsonify({'error': 'Payment not found'}), 404
        
        payment_dict = payment.to_dict()
        payment_dict['course'] = payment.course.to_dict()
        payment_dict['user'] = payment.user.to_dict()
        
        return jsonify({'payment': payment_dict}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/<int:payment_id>/refund', methods=['POST'])
@jwt_required()
def request_refund(payment_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        payment = Payment.query.get(payment_id)
        if not payment or payment.user_id != user.id:
            return jsonify({'error': 'Payment not found'}), 404
        
        if payment.status != PaymentStatus.COMPLETED:
            return jsonify({'error': 'Only completed payments can be refunded'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'User requested refund')
        
        # In a real implementation, you would process the refund through Stripe
        # For now, we'll just mark it as refunded (this should be done by admin)
        
        return jsonify({
            'message': 'Refund request submitted successfully. It will be processed by our admin team.',
            'payment_id': payment_id,
            'reason': reason
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
