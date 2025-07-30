import re
from email_validator import validate_email as email_validate, EmailNotValidError
from datetime import datetime
import uuid

def validate_email(email):
    """Validate email address format"""
    try:
        # Use email-validator library for comprehensive validation
        valid = email_validate(email)
        return True
    except EmailNotValidError:
        # Fallback to regex if library not available
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    except ImportError:
        # Fallback to regex if library not available
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True

def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True  # Phone is optional
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (10-15 digits)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False
    
    return True

def validate_name(name):
    """Validate name fields (first name, last name)"""
    if not name or len(name.strip()) < 1:
        return False
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    pattern = r"^[a-zA-Z\s\-']+$"
    return re.match(pattern, name.strip()) is not None

def validate_course_data(data):
    """Validate course creation/update data"""
    errors = []
    
    # Required fields
    if not data.get('title') or len(data['title'].strip()) < 3:
        errors.append('Title must be at least 3 characters long')
    
    if 'price' not in data:
        errors.append('Price is required')
    else:
        try:
            price = float(data['price'])
            if price < 0:
                errors.append('Price cannot be negative')
        except (ValueError, TypeError):
            errors.append('Price must be a valid number')
    
    # Optional field validations
    if 'duration_hours' in data and data['duration_hours'] is not None:
        try:
            duration = int(data['duration_hours'])
            if duration <= 0:
                errors.append('Duration must be positive')
        except (ValueError, TypeError):
            errors.append('Duration must be a valid integer')
    
    if 'difficulty_level' in data and data['difficulty_level']:
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if data['difficulty_level'].lower() not in valid_levels:
            errors.append(f'Difficulty level must be one of: {", ".join(valid_levels)}')
    
    if 'max_students' in data and data['max_students'] is not None:
        try:
            max_students = int(data['max_students'])
            if max_students <= 0:
                errors.append('Maximum students must be positive')
        except (ValueError, TypeError):
            errors.append('Maximum students must be a valid integer')
    
    # Currency validation
    if 'currency' in data and data['currency']:
        valid_currencies = ['USD', 'EUR', 'GBP', 'INR', 'CAD', 'AUD']
        if data['currency'].upper() not in valid_currencies:
            errors.append(f'Currency must be one of: {", ".join(valid_currencies)}')
    
    return errors[0] if errors else None

def validate_url(url):
    """Validate URL format"""
    if not url:
        return True  # URL is optional
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def validate_uuid(uuid_string):
    """Validate UUID format"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

def validate_date_string(date_string, date_format='%Y-%m-%d'):
    """Validate date string format"""
    try:
        datetime.strptime(date_string, date_format)
        return True
    except (ValueError, TypeError):
        return False

def validate_datetime_string(datetime_string):
    """Validate ISO datetime string format"""
    try:
        # Try parsing ISO format
        datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False

def validate_file_extension(filename, allowed_extensions):
    """Validate file extension"""
    if not filename or not allowed_extensions:
        return False
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_course_status(status):
    """Validate course status"""
    valid_statuses = ['draft', 'published', 'archived']
    return status.lower() in valid_statuses

def validate_user_role(role):
    """Validate user role"""
    valid_roles = ['student', 'instructor', 'admin']
    return role.lower() in valid_roles

def validate_payment_status(status):
    """Validate payment status"""
    valid_statuses = ['pending', 'completed', 'failed', 'refunded']
    return status.lower() in valid_statuses

def validate_json_data(data, required_fields=None, optional_fields=None):
    """Validate JSON data structure"""
    errors = []
    
    if not isinstance(data, dict):
        return ['Data must be a JSON object']
    
    # Check required fields
    if required_fields:
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                errors.append(f'Field "{field}" is required')
    
    # Check for unexpected fields
    if optional_fields is not None:
        allowed_fields = set(required_fields or []) | set(optional_fields or [])
        unexpected_fields = set(data.keys()) - allowed_fields
        if unexpected_fields:
            errors.append(f'Unexpected fields: {", ".join(unexpected_fields)}')
    
    return errors

def validate_pagination_params(page, per_page, max_per_page=100):
    """Validate pagination parameters"""
    errors = []
    
    try:
        page = int(page)
        if page < 1:
            errors.append('Page must be greater than 0')
    except (ValueError, TypeError):
        errors.append('Page must be a valid integer')
    
    try:
        per_page = int(per_page)
        if per_page < 1:
            errors.append('Per_page must be greater than 0')
        elif per_page > max_per_page:
            errors.append(f'Per_page cannot exceed {max_per_page}')
    except (ValueError, TypeError):
        errors.append('Per_page must be a valid integer')
    
    return errors

def validate_search_query(query, min_length=2, max_length=100):
    """Validate search query"""
    if not query:
        return True  # Empty query is allowed
    
    if len(query) < min_length:
        return False
    
    if len(query) > max_length:
        return False
    
    # Check for malicious patterns
    malicious_patterns = [
        r'<script',
        r'javascript:',
        r'onload=',
        r'onerror=',
        r'<iframe',
        r'<object',
        r'<embed'
    ]
    
    query_lower = query.lower()
    for pattern in malicious_patterns:
        if re.search(pattern, query_lower):
            return False
    
    return True

def sanitize_string(text, max_length=None):
    """Sanitize string input"""
    if not text:
        return text
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length].strip()
    
    return text

def validate_module_order(order, course_id=None):
    """Validate module order number"""
    try:
        order = int(order)
        if order < 1:
            return False, "Order must be greater than 0"
        return True, None
    except (ValueError, TypeError):
        return False, "Order must be a valid integer"

def validate_lesson_content(content):
    """Validate lesson content"""
    if not content:
        return True  # Content is optional
    
    # Basic content validation
    if len(content) > 10000:  # 10KB limit
        return False
    
    return True

def validate_certificate_number(cert_number):
    """Validate certificate number format"""
    if not cert_number:
        return False
    
    # Expected format: AIFA-{course_id}-{user_id}-{random}
    pattern = r'^AIFA-\d+-\d+-[A-F0-9]{8}$'
    return re.match(pattern, cert_number) is not None

def validate_meeting_id(meeting_id):
    """Validate meeting ID format (for Zoom, Google Meet, etc.)"""
    if not meeting_id:
        return True  # Meeting ID is optional
    
    # Allow alphanumeric characters, hyphens, and spaces
    pattern = r'^[a-zA-Z0-9\s\-]+$'
    return re.match(pattern, meeting_id) is not None and len(meeting_id) <= 50
