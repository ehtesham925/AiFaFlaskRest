from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
import time
from collections import defaultdict
import re

# Simple in-memory rate limiter (in production, use Redis)
rate_limit_storage = defaultdict(list)

def rate_limit(max_requests=60, per_seconds=60, key_func=None):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get('TESTING', False):  # Skip rate limiting in tests
                # Determine the key for rate limiting
                if key_func:
                    key = key_func()
                else:
                    # Default to IP address
                    key = request.remote_addr
                
                current_time = time.time()
                
                # Clean old requests
                rate_limit_storage[key] = [
                    req_time for req_time in rate_limit_storage[key]
                    if current_time - req_time < per_seconds
                ]
                
                # Check if limit exceeded
                if len(rate_limit_storage[key]) >= max_requests:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': per_seconds
                    }), 429
                
                # Add current request
                rate_limit_storage[key].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def jwt_rate_limit(max_requests=100, per_seconds=60):
    """Rate limiting based on JWT user identity"""
    def get_user_key():
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            return f"user:{user_id}"
        except:
            return f"ip:{request.remote_addr}"
    
    return rate_limit(max_requests, per_seconds, get_user_key)

def validate_json(*required_fields):
    """Validate that request contains JSON with required fields"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None or data[field] == '':
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_pagination():
    """Validate pagination parameters"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            page = request.args.get('page', 1)
            per_page = request.args.get('per_page', 20)
            
            try:
                page = int(page)
                per_page = int(per_page)
            except ValueError:
                return jsonify({'error': 'Page and per_page must be integers'}), 400
            
            if page < 1:
                return jsonify({'error': 'Page must be greater than 0'}), 400
            
            if per_page < 1 or per_page > 100:
                return jsonify({'error': 'Per_page must be between 1 and 100'}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_api_call(include_request_data=False):
    """Log API calls for monitoring"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Log request
            log_data = {
                'endpoint': request.endpoint,
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
            }
            
            if include_request_data and request.is_json:
                log_data['request_data'] = request.get_json()
            
            try:
                # Execute the function
                result = f(*args, **kwargs)
                
                # Log success
                execution_time = time.time() - start_time
                log_data.update({
                    'status': 'success',
                    'execution_time': execution_time
                })
                
                current_app.logger.info(f"API Call: {log_data}")
                return result
                
            except Exception as e:
                # Log error
                execution_time = time.time() - start_time
                log_data.update({
                    'status': 'error',
                    'error': str(e),
                    'execution_time': execution_time
                })
                
                current_app.logger.error(f"API Error: {log_data}")
                raise
        return decorated_function
    return decorator

def sanitize_input():
    """Sanitize input data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
                if data:
                    sanitized_data = {}
                    for key, value in data.items():
                        if isinstance(value, str):
                            # Basic HTML tag removal
                            sanitized_value = re.sub(r'<[^>]+>', '', value).strip()
                            sanitized_data[key] = sanitized_value
                        else:
                            sanitized_data[key] = value
                    
                    # Replace the original data
                    request._cached_json = sanitized_data
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def cache_response(timeout=300):
    """Simple response caching decorator"""
    cache = {}
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create cache key from request
            cache_key = f"{request.endpoint}:{request.query_string.decode()}"
            
            current_time = time.time()
            
            # Check if cached response exists and is still valid
            if cache_key in cache:
                cached_response, timestamp = cache[cache_key]
                if current_time - timestamp < timeout:
                    return cached_response
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            
            # Clean old cache entries (simple cleanup)
            if len(cache) > 1000:  # Limit cache size
                expired_keys = [
                    key for key, (_, timestamp) in cache.items()
                    if current_time - timestamp > timeout
                ]
                for key in expired_keys:
                    del cache[key]
            
            return result
        return decorated_function
    return decorator

def require_api_key(header_name='X-API-Key'):
    """Require API key for access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get(header_name)
            expected_key = current_app.config.get('API_KEY')
            
            if not expected_key:
                return jsonify({'error': 'API key authentication not configured'}), 500
            
            if not api_key:
                return jsonify({'error': f'Missing {header_name} header'}), 401
            
            if api_key != expected_key:
                return jsonify({'error': 'Invalid API key'}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def conditional_decorator(condition, decorator):
    """Apply decorator only if condition is met"""
    def wrapper(f):
        if condition:
            return decorator(f)
        return f
    return wrapper

def validate_file_upload(allowed_extensions=None, max_size=None):
    """Validate file uploads"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Check file extension
            if allowed_extensions:
                if not ('.' in file.filename and 
                       file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                    return jsonify({
                        'error': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
                    }), 400
            
            # Check file size
            if max_size and hasattr(file, 'content_length') and file.content_length:
                if file.content_length > max_size:
                    return jsonify({
                        'error': f'File size exceeds maximum allowed size of {max_size // (1024*1024)}MB'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
