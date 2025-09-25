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
    BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg3ODkzNDcsImV4cCI6MTc1ODgzMjU0Nywic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.kuies9vwY2S8FHpgBzFKKfvl2v0St2DpPfJEQ5KO6Tyhjf9_ORx3fZMkpc5fKo39d-yAz5G0x8xvcaQynPQJ8NAhpC9xErOW0bD2d3Soy8BmKOafoJkHHB7m-LnsJZMjyHhqEYzE8lsvPSHkLQkRoXjmWBrHJicshf1qPbs6DdM_XSneSfXUK8B1wJxyoRTFs2F_rD44WXdBmWuZsu8xn-rW6wGNtNXjwjBhsGiKhO1EN5BrVgv-X0px60pSRNxgdul-77D9vIx_Wj8ev5WwUXL_B3qNU5JQMDUd_Az1JvR_etQg2NogjN_V-n5vsqJEZUismpfp-qXqp39pPp3jwQ"

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