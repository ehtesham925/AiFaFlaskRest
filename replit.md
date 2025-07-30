# AI First Academy - Online Learning Platform

## Overview

This is a comprehensive online learning platform built with Flask, designed for AI education courses. The platform supports multiple user roles (students, instructors, admins), course management, payment processing, live sessions, and certificate generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a Flask-based REST API architecture with a modular design:

- **Backend Framework**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL (configured but can work with other databases)
- **Authentication**: JWT-based authentication with role-based access control
- **File Handling**: Custom file service for uploads and downloads
- **Payment Processing**: Stripe integration for course purchases
- **Email Service**: Flask-Mail for notifications and communications
- **PDF Generation**: ReportLab for certificate generation

## Key Components

### Database Models
- **User Management**: Users with roles (student, instructor, admin)
- **Course Structure**: Courses, modules, lessons with hierarchical organization
- **Enrollment System**: Track student progress and course completion
- **Payment Processing**: Payment records with status tracking
- **Certification**: Certificate generation and management
- **Live Sessions**: Scheduled live learning sessions
- **Notifications**: User notification system

### API Structure
The API is organized into focused blueprints:
- `/api/v1/auth` - Authentication (register, login, logout)
- `/api/v1/users` - User profile management
- `/api/v1/courses` - Course catalog and management
- `/api/v1/admin` - Administrative functions
- `/api/v1/payments` - Payment processing with Stripe
- `/api/v1/files` - File upload and download
- `/api/v1/notifications` - User notifications
- `/api/v1/certificates` - Certificate generation
- `/api/v1/live-sessions` - Live session management

### Authentication & Authorization
- JWT tokens for stateless authentication
- Role-based access control (RBAC) with decorators
- Token blacklisting for secure logout
- Password strength validation

### File Management
- Secure file upload with type validation
- Unique filename generation to prevent conflicts
- Size limits and security checks
- Support for various file types (documents, media, images)

## Data Flow

1. **User Registration/Login**: Users register and receive JWT tokens
2. **Course Discovery**: Students browse published courses
3. **Payment Processing**: Stripe handles secure payments
4. **Enrollment**: Successful payments create course enrollments
5. **Learning Progress**: System tracks lesson completion and progress
6. **Certificate Generation**: Completed courses generate PDF certificates
7. **Live Sessions**: Instructors can schedule and manage live sessions
8. **Notifications**: System sends email notifications for important events

## External Dependencies

### Payment Processing
- **Stripe**: Handles all payment processing with webhook support
- Secure checkout sessions with automatic enrollment on success

### Email Service
- **Flask-Mail**: SMTP-based email delivery
- Welcome emails, notifications, and course updates
- Configurable email templates

### File Storage
- Local file system storage with organized folder structure
- Support for course materials, user uploads, and certificates
- Secure filename handling and type validation

### PDF Generation
- **ReportLab**: Professional certificate generation
- Custom styling and branding support

## Deployment Strategy

The application is configured for flexible deployment:

- **Environment Variables**: All sensitive configuration through environment variables
- **Database**: PostgreSQL with connection pooling and health checks
- **Proxy Support**: ProxyFix middleware for reverse proxy deployment
- **CORS**: Cross-origin support for frontend integration
- **Rate Limiting**: Built-in rate limiting for API protection
- **Security**: Secure headers and input validation

### Key Configuration Areas
- Database connection with fallback to local PostgreSQL
- JWT secret keys for token security
- SMTP configuration for email delivery
- Stripe API keys for payment processing
- File upload paths and size limits
- CORS settings for frontend integration

The application uses Flask's application factory pattern for easy testing and deployment configuration management.