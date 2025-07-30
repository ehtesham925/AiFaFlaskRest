import hashlib
import secrets
import string
import uuid
from datetime import datetime, timedelta
import re
import os
from urllib.parse import urljoin, urlparse

def generate_random_string(length=32, use_digits=True, use_uppercase=True, use_lowercase=True, use_symbols=False):
    """Generate a random string of specified length"""
    characters = ""
    
    if use_lowercase:
        characters += string.ascii_lowercase
    if use_uppercase:
        characters += string.ascii_uppercase
    if use_digits:
        characters += string.digits
    if use_symbols:
        characters += "!@#$%^&*"
    
    if not characters:
        characters = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_unique_filename(original_filename, prefix=None):
    """Generate a unique filename while preserving extension"""
    if not original_filename:
        return str(uuid.uuid4()) + '.tmp'
    
    name, ext = os.path.splitext(original_filename)
    unique_id = uuid.uuid4().hex[:8]
    
    if prefix:
        return f"{prefix}_{unique_id}{ext}"
    else:
        return f"{name}_{unique_id}{ext}"

def hash_string(text, algorithm='sha256'):
    """Hash a string using specified algorithm"""
    if algorithm == 'md5':
        return hashlib.md5(text.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(text.encode()).hexdigest()
    elif algorithm == 'sha256':
        return hashlib.sha256(text.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def format_duration(minutes):
    """Convert minutes to human readable duration"""
    if not minutes or minutes <= 0:
        return "0 minutes"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{hours}h"
    else:
        return f"{mins}m"

def truncate_text(text, max_length=100, suffix="..."):
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def slugify(text):
    """Convert text to URL-friendly slug"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text

def parse_bool(value):
    """Parse various boolean representations"""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    
    return bool(value)

def get_client_ip(request):
    """Get client IP address from request"""
    # Check for forwarded IP (when behind proxy/load balancer)
    if 'X-Forwarded-For' in request.headers:
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    elif 'X-Real-IP' in request.headers:
        return request.headers['X-Real-IP']
    else:
        return request.remote_addr

def is_safe_url(target, host_url):
    """Check if redirect URL is safe"""
    if not target:
        return False
    
    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))
    
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    today = datetime.now().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def time_ago(dt):
    """Convert datetime to human readable 'time ago' format"""
    if not dt:
        return "Unknown"
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 2592000:  # 30 days
        days = int(seconds // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 31536000:  # 365 days
        months = int(seconds // 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds // 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"

def merge_dicts(*dicts):
    """Merge multiple dictionaries"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary"""
    items = []
    
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    
    return dict(items)

def chunk_list(lst, chunk_size):
    """Split list into chunks of specified size"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def extract_numbers(text):
    """Extract all numbers from text"""
    if not text:
        return []
    
    return [float(x) for x in re.findall(r'-?\d+\.?\d*', str(text))]

def mask_email(email):
    """Mask email address for privacy"""
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"

def mask_phone(phone):
    """Mask phone number for privacy"""
    if not phone:
        return phone
    
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) < 4:
        return '*' * len(digits)
    
    # Show last 4 digits
    return '*' * (len(digits) - 4) + digits[-4:]

def generate_otp(length=6):
    """Generate numeric OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def validate_json_structure(data, schema):
    """Basic JSON schema validation"""
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return False
    
    for key, expected_type in schema.items():
        if key not in data:
            return False
        
        if not isinstance(data[key], expected_type):
            return False
    
    return True

def safe_int(value, default=0):
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_file_extension(filename):
    """Get file extension from filename"""
    if not filename or '.' not in filename:
        return ''
    
    return filename.rsplit('.', 1)[1].lower()

def is_image_file(filename):
    """Check if file is an image based on extension"""
    image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}
    return get_file_extension(filename) in image_extensions

def is_video_file(filename):
    """Check if file is a video based on extension"""
    video_extensions = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
    return get_file_extension(filename) in video_extensions

def is_audio_file(filename):
    """Check if file is audio based on extension"""
    audio_extensions = {'mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a'}
    return get_file_extension(filename) in audio_extensions

def is_document_file(filename):
    """Check if file is a document based on extension"""
    document_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf'}
    return get_file_extension(filename) in document_extensions

def format_currency(amount, currency='USD', decimal_places=2):
    """Format currency amount"""
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'INR': '₹',
        'CAD': 'C$',
        'AUD': 'A$'
    }
    
    symbol = currency_symbols.get(currency, currency)
    formatted_amount = f"{float(amount):.{decimal_places}f}"
    
    return f"{symbol}{formatted_amount}"

def calculate_discount_price(original_price, discount_percentage):
    """Calculate discounted price"""
    if not original_price or not discount_percentage:
        return original_price
    
    discount_amount = (original_price * discount_percentage) / 100
    return original_price - discount_amount

def generate_referral_code(length=8):
    """Generate referral code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def format_percentage(value, decimal_places=1):
    """Format percentage value"""
    return f"{float(value):.{decimal_places}f}%"

def clean_filename(filename):
    """Clean filename for safe storage"""
    if not filename:
        return "unnamed"
    
    # Remove path separators and special characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename or "unnamed"
