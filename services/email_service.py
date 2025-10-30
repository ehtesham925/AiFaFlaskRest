from flask_mail import Message
from app import mail
from flask import current_app
import os
from datetime import datetime

class EmailService:
    def __init__(self):
        self.sender = os.environ.get('MAIL_DEFAULT_SENDER', 'mohammed.ehtesham@aimtechnologies.in')
    
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
        subject = "Welcome Python Training Management System!"
        
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
The AI First Python Training Management System
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
The AI First Python Training Management System Team</p>
</body>
</html>
"""
        
        return self.send_email(user.email, subject, body, html_body)
