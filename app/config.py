import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""

    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:@localhost:5432/locus_assistant')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API Configuration
    BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4MzA2NTIsImV4cCI6MTc1ODg3Mzg1Miwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.jNIJoulmMmvfbS8R0_1NvF-kXlzmWtCBxbCJTAXPU0HE3b7q7Qwr5digjW58L5a3Ny8rNjNam3YaIvzhcV-itmcCmbI1LuuCBwPjNEMJwBMAVI6asiqGm0l2buX1k5roJsh7nK3b0HpY3ZTZqxurWO8CiO6dzNcYrPqUvYYCkBOkx_VSnaSD9ABQ0PZYb28wAB-EY2puB3itNAuB3PTAbjsI90fS7A55nJ1VcmFZFx9-xsQBVtusDAQyr4tICCRyzl-0FKeNl_e0_ytlboIrHIbe-76eHVgxSJdoxwYlLXSVEOjBwPbB3oRbfELEsoB7l3cFdbY34eX_Iskh9A3hjg"

    # Google AI Studio Configuration
    GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
    GOOGLE_AI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

    # Rate Limiting Configuration
    MAX_CONCURRENT_API_CALLS = 10
    MAX_API_CALLS_PER_MINUTE = 12

    # Locus API URLs
    LOCUS_BASE_URL = "https://dash.locus-api.com"
    LOCUS_AUTH_URL = "https://accounts.locus-dashboard.com"
    LOCUS_API_URL = "https://oms.locus-api.com"

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}