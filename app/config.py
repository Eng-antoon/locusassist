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
    BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4NzQxMjIsImV4cCI6MTc1ODkxNzMyMiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.lZGb9MynHmGDDUsPTT6PMfCosS3Dkzwd6vBEsneW3pn_w4rJjkby-jMSo8ljBrMhc9AypY43bX8Kfs86FZ2j3NNo_lUi9epSur1GyZf11S8GiH_lXlcHk-Kf-a47vimzo-ccmMJ-15UMYK9ekbWRUeg1-2Dbm-ENXkgIT-T58qh9FN7qf7zqOgPOFyLwBdCQLFF7su3Opzm7TTW1VLrt0_CBfczq_bcJ9sdl_iTYCTXlIBIwdeoqTwYXZoW7O9Ndprl9sp__h3_6QLHXnrdtEw8H3vcpeDc-Cke4iZZNvDdq8f3gIwEQVLyEAkrT_hpZfYFYDnc8xy0SQnQhiZ1mJw"

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