import time
import threading
import logging
from datetime import datetime, timedelta
import json
import base64
from PIL import Image
import io
from models import db

# Global rate limiting for Google API calls
# Google Gemini API has limits: 15 requests per minute for free tier, 1000 for paid
# We'll use a conservative approach: max 10 concurrent API calls + small delays
api_rate_limiter = threading.Semaphore(10)  # Max 10 concurrent API calls
api_call_times = []  # Track API call timing for rate limiting
api_timing_lock = threading.Lock()

# Setup logging
logger = logging.getLogger(__name__)

def rate_limit_api_call():
    """Rate limit Google API calls to respect billing limits"""
    with api_timing_lock:
        current_time = time.time()
        # Remove API calls older than 60 seconds
        global api_call_times
        api_call_times = [t for t in api_call_times if current_time - t < 60]

        # If we've made more than 12 calls in the last minute, add delay
        if len(api_call_times) >= 12:
            sleep_time = 60 - (current_time - api_call_times[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limiting: sleeping {sleep_time:.1f} seconds to respect API limits")
                time.sleep(sleep_time)

        # Record this API call
        api_call_times.append(current_time)

def create_tables(app):
    """Create database tables if they don't exist"""
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")

def init_db_connection(app):
    """Initialize database connection and create tables"""
    try:
        create_tables(app)
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def process_image_data(image_data):
    """Process base64 image data"""
    try:
        if isinstance(image_data, str) and image_data.startswith('data:'):
            # Remove data URL prefix if present
            image_data = image_data.split(',')[1]

        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        return image
    except Exception as e:
        logger.error(f"Error processing image data: {e}")
        return None

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return "N/A"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt

    return dt.strftime('%Y-%m-%d %H:%M:%S')

def safe_json_loads(json_str, default=None):
    """Safely load JSON string"""
    if not json_str:
        return default

    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def calculate_percentage(numerator, denominator):
    """Calculate percentage safely"""
    if not denominator or denominator == 0:
        return 0
    return round((numerator / denominator) * 100, 1)

def validate_required_fields(data, required_fields):
    """Validate required fields in data dictionary"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, "All required fields present"

def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    return filename or 'unnamed_file'