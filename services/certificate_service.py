from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.colors import Color, black, blue
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import os
import uuid
from datetime import datetime
from io import BytesIO

class CertificateService:
    def __init__(self):
        self.upload_folder = os.environ.get('UPLOAD_FOLDER', 'uploads')
        self.certificates_folder = os.path.join(self.upload_folder, 'certificates')
        
        # Create certificates directory if it doesn't exist
        os.makedirs(self.certificates_folder, exist_ok=True)
    
    def generate_certificate_pdf(self, user, course, certificate):
        """Generate a PDF certificate for course completion"""
        try:
            # Generate unique filename
            filename = f"certificate_{certificate.id}_{uuid.uuid4().hex[:8]}.pdf"
            file_path = os.path.join(self.certificates_folder, filename)
            
            # Create the PDF document
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=28,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=blue
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=black
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=14,
                spaceAfter=12,
                alignment=TA_CENTER,
                textColor=black
            )
            
            large_body_style = ParagraphStyle(
                'LargeBody',
                parent=styles['Normal'],
                fontSize=16,
                spaceAfter=15,
                alignment=TA_CENTER,
                textColor=black
            )
            
            # Build the content
            content = []
            
            # Add some space from top
            content.append(Spacer(1, 0.5*inch))
            
            # Certificate header
            content.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
            content.append(Spacer(1, 0.3*inch))
            
            # Subtitle
            content.append(Paragraph("AI First Academy", subtitle_style))
            content.append(Spacer(1, 0.5*inch))
            
            # This certifies that
            content.append(Paragraph("This is to certify that", body_style))
            content.append(Spacer(1, 0.2*inch))
            
            # Student name (larger, bold)
            student_name_style = ParagraphStyle(
                'StudentName',
                parent=styles['Normal'],
                fontSize=24,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=blue,
                fontName='Helvetica-Bold'
            )
            content.append(Paragraph(f"{user.first_name} {user.last_name}", student_name_style))
            
            # Has successfully completed
            content.append(Paragraph("has successfully completed the course", body_style))
            content.append(Spacer(1, 0.2*inch))
            
            # Course name (larger, bold)
            course_name_style = ParagraphStyle(
                'CourseName',
                parent=styles['Normal'],
                fontSize=20,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=black,
                fontName='Helvetica-Bold'
            )
            content.append(Paragraph(course.title, course_name_style))
            
            # Course details
            if course.duration_hours:
                content.append(Paragraph(f"Duration: {course.duration_hours} hours", body_style))
            
            if course.difficulty_level:
                content.append(Paragraph(f"Level: {course.difficulty_level.title()}", body_style))
            
            content.append(Spacer(1, 0.3*inch))
            
            # Issue date
            issue_date = certificate.issued_at.strftime("%B %d, %Y")
            content.append(Paragraph(f"Issued on: {issue_date}", large_body_style))
            content.append(Spacer(1, 0.2*inch))
            
            # Certificate number
            content.append(Paragraph(f"Certificate Number: {certificate.certificate_number}", body_style))
            content.append(Spacer(1, 0.4*inch))
            
            # Instructor signature section
            signature_style = ParagraphStyle(
                'Signature',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=8,
                alignment=TA_CENTER,
                textColor=black
            )
            
            content.append(Paragraph("_" * 40, signature_style))
            content.append(Paragraph(f"{course.instructor.first_name} {course.instructor.last_name}", signature_style))
            content.append(Paragraph("Course Instructor", signature_style))
            content.append(Spacer(1, 0.3*inch))
            
            # Academy signature
            content.append(Paragraph("_" * 40, signature_style))
            content.append(Paragraph("AI First Academy", signature_style))
            content.append(Paragraph("Certificate Authority", signature_style))
            content.append(Spacer(1, 0.2*inch))
            
            # Verification note
            verification_style = ParagraphStyle(
                'Verification',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=Color(0.5, 0.5, 0.5)
            )
            content.append(Paragraph(
                f"This certificate can be verified at: {certificate.verification_url}",
                verification_style
            ))
            
            # Build the PDF
            doc.build(content)
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Certificate generation error: {str(e)}")
    
    def generate_simple_certificate_pdf(self, user, course, certificate):
        """Generate a simple certificate using canvas for more control"""
        try:
            filename = f"certificate_{certificate.id}_{uuid.uuid4().hex[:8]}.pdf"
            file_path = os.path.join(self.certificates_folder, filename)
            
            # Create canvas
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
            
            # Set up fonts and colors
            c.setTitle(f"Certificate - {user.first_name} {user.last_name}")
            
            # Draw border
            border_margin = 50
            c.setStrokeColor(blue)
            c.setLineWidth(3)
            c.rect(border_margin, border_margin, width - 2*border_margin, height - 2*border_margin)
            
            # Inner border
            inner_margin = 60
            c.setLineWidth(1)
            c.rect(inner_margin, inner_margin, width - 2*inner_margin, height - 2*inner_margin)
            
            # Title
            c.setFont("Helvetica-Bold", 32)
            c.setFillColor(blue)
            title_y = height - 150
            c.drawCentredText(width/2, title_y, "CERTIFICATE OF COMPLETION")
            
            # Subtitle
            c.setFont("Helvetica", 20)
            c.setFillColor(black)
            c.drawCentredText(width/2, title_y - 50, "AI First Academy")
            
            # "This certifies that"
            c.setFont("Helvetica", 16)
            c.drawCentredText(width/2, title_y - 100, "This is to certify that")
            
            # Student name
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(blue)
            c.drawCentredText(width/2, title_y - 150, f"{user.first_name} {user.last_name}")
            
            # "has successfully completed"
            c.setFont("Helvetica", 16)
            c.setFillColor(black)
            c.drawCentredText(width/2, title_y - 190, "has successfully completed the course")
            
            # Course name
            c.setFont("Helvetica-Bold", 22)
            course_title = course.title
            # Split long titles into multiple lines
            if len(course_title) > 50:
                words = course_title.split()
                line1 = " ".join(words[:len(words)//2])
                line2 = " ".join(words[len(words)//2:])
                c.drawCentredText(width/2, title_y - 240, line1)
                c.drawCentredText(width/2, title_y - 270, line2)
                course_y = title_y - 300
            else:
                c.drawCentredText(width/2, title_y - 240, course_title)
                course_y = title_y - 270
            
            # Course details
            c.setFont("Helvetica", 14)
            if course.duration_hours:
                c.drawCentredText(width/2, course_y - 30, f"Duration: {course.duration_hours} hours")
            if course.difficulty_level:
                c.drawCentredText(width/2, course_y - 50, f"Level: {course.difficulty_level.title()}")
            
            # Issue date
            c.setFont("Helvetica", 16)
            issue_date = certificate.issued_at.strftime("%B %d, %Y")
            c.drawCentredText(width/2, course_y - 90, f"Issued on: {issue_date}")
            
            # Certificate number
            c.setFont("Helvetica", 12)
            c.drawCentredText(width/2, course_y - 120, f"Certificate Number: {certificate.certificate_number}")
            
            # Signatures
            signature_y = 200
            
            # Instructor signature
            c.setFont("Helvetica", 12)
            instructor_x = width/4
            c.line(instructor_x - 60, signature_y, instructor_x + 60, signature_y)
            c.drawCentredText(instructor_x, signature_y - 20, f"{course.instructor.first_name} {course.instructor.last_name}")
            c.drawCentredText(instructor_x, signature_y - 35, "Course Instructor")
            
            # Academy signature
            academy_x = 3 * width/4
            c.line(academy_x - 60, signature_y, academy_x + 60, signature_y)
            c.drawCentredText(academy_x, signature_y - 20, "AI First Academy")
            c.drawCentredText(academy_x, signature_y - 35, "Certificate Authority")
            
            # Verification URL
            c.setFont("Helvetica", 8)
            c.setFillColor(Color(0.5, 0.5, 0.5))
            c.drawCentredText(width/2, 100, f"Verify this certificate at: {certificate.verification_url}")
            
            # Save the PDF
            c.save()
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Certificate generation error: {str(e)}")
    
    def delete_certificate_file(self, file_path):
        """Delete certificate file from filesystem"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting certificate file {file_path}: {str(e)}")
            return False
    
    def get_certificate_file_path(self, certificate_id, filename):
        """Get the full file path for a certificate"""
        return os.path.join(self.certificates_folder, filename)
    
    def validate_certificate_data(self, user, course, enrollment):
        """Validate that all required data is present for certificate generation"""
        errors = []
        
        if not user:
            errors.append("User data is required")
        elif not user.first_name or not user.last_name:
            errors.append("User must have first and last name")
        
        if not course:
            errors.append("Course data is required")
        elif not course.title:
            errors.append("Course must have a title")
        
        if not enrollment:
            errors.append("Enrollment data is required")
        elif not enrollment.completed_at:
            errors.append("Course must be completed before certificate generation")
        
        return errors
    
    def bulk_generate_certificates(self, enrollments):
        """Generate certificates for multiple enrollments"""
        results = {
            'success': [],
            'failed': [],
            'total': len(enrollments)
        }
        
        for enrollment in enrollments:
            try:
                # Validate data
                validation_errors = self.validate_certificate_data(
                    enrollment.user, 
                    enrollment.course, 
                    enrollment
                )
                
                if validation_errors:
                    results['failed'].append({
                        'enrollment_id': enrollment.id,
                        'user': f"{enrollment.user.first_name} {enrollment.user.last_name}",
                        'course': enrollment.course.title,
                        'errors': validation_errors
                    })
                    continue
                
                # Generate certificate (this would be done in the route)
                results['success'].append({
                    'enrollment_id': enrollment.id,
                    'user': f"{enrollment.user.first_name} {enrollment.user.last_name}",
                    'course': enrollment.course.title
                })
                
            except Exception as e:
                results['failed'].append({
                    'enrollment_id': enrollment.id,
                    'user': f"{enrollment.user.first_name} {enrollment.user.last_name}" if enrollment.user else "Unknown",
                    'course': enrollment.course.title if enrollment.course else "Unknown",
                    'errors': [str(e)]
                })
        
        return results
