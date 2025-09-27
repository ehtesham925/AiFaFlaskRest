from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from models import Certificate, Enrollment, Course, User
from auth import get_current_user, admin_required
from services.certificate_service import CertificateService
import uuid

certificate_bp = Blueprint('certificates', __name__)

""" Get all certifications  """
@certificate_bp.route('/', methods=['GET'])
@jwt_required()
def get_user_certificates():
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificates = Certificate.query.filter_by(user_id=user.id).all()
        
        certificate_data = []
        for cert in certificates:
            cert_dict = cert.to_dict()
            cert_dict['course'] = cert.course.to_dict()
            certificate_data.append(cert_dict)
        
        return jsonify({'certificates': certificate_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

""" Generate Certificate  """
@certificate_bp.route('/generate/<int:course_id>', methods=['POST'])
@jwt_required()
def generate_certificate(course_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has completed the course
        enrollment = Enrollment.query.filter_by(
            user_id=user.id,
            course_id=course_id,
            is_active=True
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this course'}), 404
        
        if not enrollment.completed_at:
            return jsonify({'error': 'Course not completed yet'}), 400
        
        # Check if certificate already exists
        existing_certificate = Certificate.query.filter_by(
            user_id=user.id,
            course_id=course_id
        ).first()
        
        if existing_certificate:
            return jsonify({
                'message': 'Certificate already exists',
                'certificate': existing_certificate.to_dict()
            }), 200
        
        # Generate certificate
        course = Course.query.get(course_id)
        certificate_service = CertificateService()
        
        # Generate unique certificate number
        certificate_number = f"AIFA-{course_id}-{user.id}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create certificate record
        certificate = Certificate(
            user_id=user.id,
            course_id=course_id,
            certificate_number=certificate_number
        )
        
        db.session.add(certificate)
        db.session.flush()  # Get the certificate ID
        
        # Generate PDF certificate
        pdf_path = certificate_service.generate_certificate_pdf(
            user=user,
            course=course,
            certificate=certificate
        )
        
        # Update certificate with file path and verification URL
        certificate.file_path = pdf_path
        certificate.verification_url = f"/api/v1/certificates/verify/{certificate.certificate_number}"
        
        db.session.commit()
        
        return jsonify({
            'message': 'Certificate generated successfully',
            'certificate': certificate.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

"""Download Certificate"""
@certificate_bp.route('/download/<int:certificate_id>', methods=['GET'])
@jwt_required()
def download_certificate(certificate_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = Certificate.query.get(certificate_id)
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        # Check if user owns the certificate or is admin/instructor
        if (certificate.user_id != user.id and 
            user.role.value != 'admin' and 
            certificate.course.instructor_id != user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        if not certificate.file_path:
            return jsonify({'error': 'Certificate file not found'}), 404
        
        from services.file_service import FileService
        file_service = FileService()

        response_file = file_service.send_file(certificate.file_path, 
            f"Certificate_{certificate.certificate_number}.pdf")
        
        return file_service.send_file(
            certificate.file_path, 
            f"Certificate_{certificate.certificate_number}.pdf"
        )
        # print(response_file)

        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""Verify Certificate"""
@certificate_bp.route('/verify/<certificate_number>', methods=['GET'])
def verify_certificate(certificate_number):
    try:
        certificate = Certificate.query.filter_by(certificate_number=certificate_number).first()
        
        if not certificate:
            return jsonify({
                'valid': False,
                'error': 'Certificate not found'
            }), 404
        
        return jsonify({
            'valid': True,
            'certificate': {
                'certificate_number': certificate.certificate_number,
                'issued_at': certificate.issued_at.isoformat(),
                'user_name': f"{certificate.user.first_name} {certificate.user.last_name}",
                'course_title': certificate.course.title,
                'instructor_name': f"{certificate.course.instructor.first_name} {certificate.course.instructor.last_name}",
                'issued_by': 'AI First Academy'
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

""" Regenerate Certificate """
@certificate_bp.route('/regenerate/<int:certificate_id>', methods=['POST'])
@jwt_required()
def regenerate_certificate(certificate_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = Certificate.query.get(certificate_id)
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        # Check if user owns the certificate
        if certificate.user_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Regenerate certificate PDF
        certificate_service = CertificateService()
        
        # Delete old file if exists
        if certificate.file_path:
            from services.file_service import FileService
            file_service = FileService()
            file_service.delete_file(certificate.file_path)
        
        # Generate new PDF
        pdf_path = certificate_service.generate_certificate_pdf(
            user=user,
            course=certificate.course,
            certificate=certificate
        )
        
        certificate.file_path = pdf_path
        db.session.commit()
        
        return jsonify({
            'message': 'Certificate regenerated successfully',
            'certificate': certificate.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

"""Get All Certificates """
@certificate_bp.route('/admin/all', methods=['GET'])
@admin_required
def get_all_certificates():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        course_id = request.args.get('course_id', type=int)
        user_id = request.args.get('user_id', type=int)
        
        query = Certificate.query
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        certificates = query.order_by(Certificate.issued_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        certificate_data = []
        for cert in certificates.items:
            cert_dict = cert.to_dict()
            cert_dict['user'] = cert.user.to_dict()
            cert_dict['course'] = cert.course.to_dict()
            certificate_data.append(cert_dict)
        
        return jsonify({
            'certificates': certificate_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': certificates.total,
                'pages': certificates.pages,
                'has_next': certificates.has_next,
                'has_prev': certificates.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
""" Generate bulk Certificates """
@certificate_bp.route('/admin/bulk-generate', methods=['POST'])
@admin_required
def bulk_generate_certificates():
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'error': 'Course ID is required'}), 400
        
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Get all completed enrollments for this course that don't have certificates
        completed_enrollments = db.session.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.completed_at.isnot(None),
            ~Enrollment.user_id.in_(
                db.session.query(Certificate.user_id).filter_by(course_id=course_id)
            )
        ).all()
        
        if not completed_enrollments:
            return jsonify({
                'message': 'No eligible enrollments found for certificate generation',
                'certificates_generated': 0
            }), 200
        
        certificate_service = CertificateService()
        certificates_generated = []
        
        for enrollment in completed_enrollments:
            try:
                # Generate unique certificate number
                certificate_number = f"AIFA-{course_id}-{enrollment.user_id}-{uuid.uuid4().hex[:8].upper()}"
                
                # Create certificate record
                certificate = Certificate(
                    user_id=enrollment.user_id,
                    course_id=course_id,
                    certificate_number=certificate_number
                )
                
                db.session.add(certificate)
                db.session.flush()
                
                # Generate PDF certificate
                pdf_path = certificate_service.generate_certificate_pdf(
                    user=enrollment.user,
                    course=course,
                    certificate=certificate
                )
                
                certificate.file_path = pdf_path
                certificate.verification_url = f"/api/v1/certificates/verify/{certificate.certificate_number}"
                
                certificates_generated.append(certificate)
                
            except Exception as e:
                print(f"Failed to generate certificate for user {enrollment.user_id}: {str(e)}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'message': f'Bulk certificate generation completed',
            'certificates_generated': len(certificates_generated),
            'course_id': course_id,
            'course_title': course.title
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
""" Get certifications for the specific courses  """
@certificate_bp.route('/course/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course_certificates(course_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if user is instructor or admin
        if course.instructor_id != user.id and user.role.value != 'admin':
            return jsonify({'error': 'Access denied'}), 403
        
        certificates = Certificate.query.filter_by(course_id=course_id).all()
        
        certificate_data = []
        for cert in certificates:
            cert_dict = cert.to_dict()
            cert_dict['user'] = cert.user.to_dict()
            certificate_data.append(cert_dict)
        
        return jsonify({
            'course_id': course_id,
            'course_title': course.title,
            'certificates': certificate_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
