from flask_mail import Message
from app import mail
from flask import current_app
import os
from datetime import datetime

class EmailService:
    def __init__(self):
        self.sender = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@aifirstacademy.com')
    
    def send_email(self, recipient, subject, body, html_body=None):
        """Send email using Flask-Mail"""
        try:
            msg = Message(
                subject=subject,
                sender=self.sender,
                recipients=[recipient] if isinstance(recipient, str) else recipient
            )
            msg.body = body
            if html_body:
                msg.html = html_body
            
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Failed to send email to {recipient}: {str(e)}")
            return False
    
    def send_welcome_email(self, user):
        """Send welcome email to new users"""
        subject = "Welcome to AI First Academy!"
        
        body = f"""
Dear {user.first_name},

Welcome to AI First Academy! We're excited to have you join our community of AI enthusiasts and learners.

Your account has been successfully created with the email: {user.email}

What's next?
- Browse our course catalog to find courses that interest you
- Complete your profile to get personalized recommendations
- Join our community forums to connect with other learners

If you have any questions, feel free to reach out to our support team.

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>Welcome to AI First Academy!</h2>

<p>Dear {user.first_name},</p>

<p>Welcome to AI First Academy! We're excited to have you join our community of AI enthusiasts and learners.</p>

<p>Your account has been successfully created with the email: <strong>{user.email}</strong></p>

<h3>What's next?</h3>
<ul>
    <li>Browse our course catalog to find courses that interest you</li>
    <li>Complete your profile to get personalized recommendations</li>
    <li>Join our community forums to connect with other learners</li>
</ul>

<p>If you have any questions, feel free to reach out to our support team.</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_enrollment_confirmation(self, user, course):
        """Send enrollment confirmation email"""
        subject = f"Enrollment Confirmed: {course.title}"
        
        body = f"""
Dear {user.first_name},

Congratulations! You have successfully enrolled in "{course.title}".

Course Details:
- Title: {course.title}
- Instructor: {course.instructor.first_name} {course.instructor.last_name}
- Duration: {course.duration_hours} hours
- Difficulty: {course.difficulty_level}

You can now access your course materials through your dashboard.

Happy learning!

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>Enrollment Confirmed!</h2>

<p>Dear {user.first_name},</p>

<p>Congratulations! You have successfully enrolled in "<strong>{course.title}</strong>".</p>

<h3>Course Details:</h3>
<ul>
    <li><strong>Title:</strong> {course.title}</li>
    <li><strong>Instructor:</strong> {course.instructor.first_name} {course.instructor.last_name}</li>
    <li><strong>Duration:</strong> {course.duration_hours} hours</li>
    <li><strong>Difficulty:</strong> {course.difficulty_level}</li>
</ul>

<p>You can now access your course materials through your dashboard.</p>

<p>Happy learning!</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_payment_confirmation(self, user, course, payment):
        """Send payment confirmation email"""
        subject = f"Payment Confirmed: {course.title}"
        
        body = f"""
Dear {user.first_name},

Your payment for "{course.title}" has been successfully processed.

Payment Details:
- Amount: {payment.currency} {payment.amount}
- Course: {course.title}
- Payment Date: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- Payment ID: {payment.id}

You are now enrolled in the course and can access all course materials.

Thank you for your purchase!

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>Payment Confirmed!</h2>

<p>Dear {user.first_name},</p>

<p>Your payment for "<strong>{course.title}</strong>" has been successfully processed.</p>

<h3>Payment Details:</h3>
<ul>
    <li><strong>Amount:</strong> {payment.currency} {payment.amount}</li>
    <li><strong>Course:</strong> {course.title}</li>
    <li><strong>Payment Date:</strong> {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}</li>
    <li><strong>Payment ID:</strong> {payment.id}</li>
</ul>

<p>You are now enrolled in the course and can access all course materials.</p>

<p>Thank you for your purchase!</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_certificate_notification(self, user, course, certificate):
        """Send certificate issued notification"""
        subject = f"Certificate Issued: {course.title}"
        
        body = f"""
Dear {user.first_name},

Congratulations! You have successfully completed "{course.title}" and your certificate is now available.

Certificate Details:
- Course: {course.title}
- Certificate Number: {certificate.certificate_number}
- Issue Date: {certificate.issued_at.strftime('%Y-%m-%d')}
- Verification URL: {certificate.verification_url}

You can download your certificate from your dashboard or verify it using the verification URL above.

Well done on completing the course!

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>Certificate Issued!</h2>

<p>Dear {user.first_name},</p>

<p>Congratulations! You have successfully completed "<strong>{course.title}</strong>" and your certificate is now available.</p>

<h3>Certificate Details:</h3>
<ul>
    <li><strong>Course:</strong> {course.title}</li>
    <li><strong>Certificate Number:</strong> {certificate.certificate_number}</li>
    <li><strong>Issue Date:</strong> {certificate.issued_at.strftime('%Y-%m-%d')}</li>
    <li><strong>Verification URL:</strong> <a href="{certificate.verification_url}">{certificate.verification_url}</a></li>
</ul>

<p>You can download your certificate from your dashboard or verify it using the verification URL above.</p>

<p>Well done on completing the course!</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_live_session_notification(self, user, course, session):
        """Send live session notification"""
        subject = f"Live Session Scheduled: {session.title}"
        
        session_time = session.scheduled_at.strftime('%Y-%m-%d at %H:%M UTC')
        
        body = f"""
Dear {user.first_name},

A new live session has been scheduled for your course "{course.title}".

Session Details:
- Title: {session.title}
- Course: {course.title}
- Scheduled Time: {session_time}
- Duration: {session.duration_minutes} minutes
- Meeting ID: {session.meeting_id or 'Will be provided before session'}

{f"Description: {session.description}" if session.description else ""}

Make sure to mark your calendar and join on time!

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>Live Session Scheduled!</h2>

<p>Dear {user.first_name},</p>

<p>A new live session has been scheduled for your course "<strong>{course.title}</strong>".</p>

<h3>Session Details:</h3>
<ul>
    <li><strong>Title:</strong> {session.title}</li>
    <li><strong>Course:</strong> {course.title}</li>
    <li><strong>Scheduled Time:</strong> {session_time}</li>
    <li><strong>Duration:</strong> {session.duration_minutes} minutes</li>
    <li><strong>Meeting ID:</strong> {session.meeting_id or 'Will be provided before session'}</li>
</ul>

{f"<p><strong>Description:</strong> {session.description}</p>" if session.description else ""}

<p>Make sure to mark your calendar and join on time!</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_notification_email(self, user, title, message):
        """Send general notification email"""
        subject = f"AI First Academy: {title}"
        
        body = f"""
Dear {user.first_name},

{message}

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>{title}</h2>

<p>Dear {user.first_name},</p>

<p>{message}</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_password_reset_email(self, user, reset_token):
        """Send password reset email"""
        subject = "Password Reset - AI First Academy"
        
        reset_url = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={reset_token}"
        
        body = f"""
Dear {user.first_name},

We received a request to reset your password for your AI First Academy account.

If you requested this password reset, please click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you did not request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
The AI First Academy Team
        """
        
        html_body = f"""
<html>
<body>
<h2>Password Reset Request</h2>

<p>Dear {user.first_name},</p>

<p>We received a request to reset your password for your AI First Academy account.</p>

<p>If you requested this password reset, please click the link below to reset your password:</p>
<p><a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>

<p>This link will expire in 1 hour for security reasons.</p>

<p>If you did not request a password reset, please ignore this email and your password will remain unchanged.</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
        """
        
        return self.send_email(user.email, subject, body, html_body)
    
    def send_course_update_notification(self, users, course, update_message):
        """Send course update notification to multiple users"""
        subject = f"Course Update: {course.title}"
        
        for user in users:
            body = f"""
Dear {user.first_name},

There's an update for your enrolled course "{course.title}".

Update:
{update_message}

You can access the course through your dashboard to see the latest content.

Best regards,
The AI First Academy Team
            """
            
            html_body = f"""
<html>
<body>
<h2>Course Update</h2>

<p>Dear {user.first_name},</p>

<p>There's an update for your enrolled course "<strong>{course.title}</strong>".</p>

<h3>Update:</h3>
<p>{update_message}</p>

<p>You can access the course through your dashboard to see the latest content.</p>

<p>Best regards,<br>
The AI First Academy Team</p>
</body>
</html>
            """
            
            self.send_email(user.email, subject, body, html_body)
