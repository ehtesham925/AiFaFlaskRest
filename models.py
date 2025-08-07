from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum
from sqlalchemy import Numeric

class UserRole(Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"

class CourseStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(255))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='user', lazy='dynamic')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    certificates = db.relationship('Certificate', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'phone': self.phone,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(500))
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    price = db.Column(Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    duration_hours = db.Column(db.Integer)
    difficulty_level = db.Column(db.String(20))  # beginner, intermediate, advanced
    thumbnail = db.Column(db.String(255))
    status = db.Column(db.Enum(CourseStatus), default=CourseStatus.DRAFT)
    max_students = db.Column(db.Integer)
    prerequisites = db.Column(db.Text)
    learning_outcomes = db.Column(db.Text)
    # banner_picture = db.Column(db.String(255),nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instructor = db.relationship('User', backref='courses_taught')
    modules = db.relationship('CourseModule', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic')
    payments = db.relationship('Payment', backref='course', lazy='dynamic')
    certificates = db.relationship('Certificate', backref='course', lazy='dynamic')
    live_sessions = db.relationship('LiveSession', backref='course', lazy='dynamic')
    
    def to_dict(self, include_modules=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'short_description': self.short_description,
            'instructor_id': self.instructor_id,
            'instructor_name': f"{self.instructor.first_name} {self.instructor.last_name}",
            'price': float(self.price),
            'currency': self.currency,
            'duration_hours': self.duration_hours,
            'difficulty_level': self.difficulty_level,
            'thumbnail': self.thumbnail,
            'status': self.status.value,
            'max_students': self.max_students,
            'prerequisites': self.prerequisites,
            'learning_outcomes': self.learning_outcomes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'enrollment_count': self.enrollments.count()
        }
        
        if include_modules:
            data['modules'] = [module.to_dict(include_lessons=True) for module in self.modules.order_by(CourseModule.order)]
        
        return data

class CourseModule(db.Model):
    __tablename__ = 'course_modules'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False)
    is_preview = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    lessons = db.relationship('Lesson', backref='module', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_lessons=False):
        data = {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'order': self.order,
            'is_preview': self.is_preview,
            'created_at': self.created_at.isoformat()
        }
        
        if include_lessons:
            data['lessons'] = [lesson.to_dict() for lesson in self.lessons.order_by(Lesson.order)]
        
        return data

class Lesson(db.Model):
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('course_modules.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    video_url = db.Column(db.String(500))
    duration_minutes = db.Column(db.Integer)
    order = db.Column(db.Integer, nullable=False)
    is_preview = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resources = db.relationship('LessonResource', backref='lesson', lazy='dynamic', cascade='all, delete-orphan')
    progress = db.relationship('LessonProgress', backref='lesson', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'content': self.content,
            'video_url': self.video_url,
            'duration_minutes': self.duration_minutes,
            'order': self.order,
            'is_preview': self.is_preview,
            'created_at': self.created_at.isoformat(),
            'resources': [resource.to_dict() for resource in self.resources]
        }

class LessonResource(db.Model):
    __tablename__ = 'lesson_resources'
    
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # pdf, video, audio, image, etc.
    file_size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'title': self.title,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat()
        }

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    progress_percentage = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    lesson_progress = db.relationship('LessonProgress', backref='enrollment', lazy='dynamic')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'course_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'enrolled_at': self.enrolled_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress_percentage': self.progress_percentage,
            'is_active': self.is_active
        }

class LessonProgress(db.Model):
    __tablename__ = 'lesson_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    watch_time_seconds = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('enrollment_id', 'lesson_id'),)

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    stripe_payment_intent_id = db.Column(db.String(255))
    stripe_session_id = db.Column(db.String(255))
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status.value,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_number = db.Column(db.String(100), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500))
    verification_url = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'certificate_number': self.certificate_number,
            'issued_at': self.issued_at.isoformat(),
            'file_path': self.file_path,
            'verification_url': self.verification_url
        }

class LiveSession(db.Model):
    __tablename__ = 'live_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    meeting_url = db.Column(db.String(500))
    meeting_id = db.Column(db.String(100))
    meeting_password = db.Column(db.String(100))
    is_recorded = db.Column(db.Boolean, default=False)
    recording_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'scheduled_at': self.scheduled_at.isoformat(),
            'duration_minutes': self.duration_minutes,
            'meeting_url': self.meeting_url,
            'meeting_id': self.meeting_id,
            'meeting_password': self.meeting_password,
            'is_recorded': self.is_recorded,
            'recording_url': self.recording_url,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # course_update, payment, certificate, live_session, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

class TokenBlacklist(db.Model):
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
