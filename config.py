import os
from datetime import timedelta

# Get the project base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or '5ccd0e882a4ab8801e60b7fd9a0fc2081993fca07d9d3d5270372e6e5712b25c'
    
    # Database - MySQL/MariaDB Configuration (SQLAlchemy)
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Suppress overhead warning
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or '87ffb15a41b02dcea7b5f83160c5edb7c388d2c83fbbeece02ac67c33d14c5f6'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # File Upload Configuration
    # We place uploads in 'static/uploads' so they can be served by Flask easily
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'mp3', 'mp4', 'txt', 'webp'}
    
    # CORS
    CORS_HEADERS = 'Content-Type'
    
    # Pagination
    ITEMS_PER_PAGE = 20

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
    # Database Connection String
    # Format: mysql+pymysql://username:password@host:port/database_name
    # Defaulting to XAMPP standard (root user, no password)
    # If you have a password, change to: 'mysql+pymysql://root:YOUR_PASSWORD@localhost/agridata'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql://root:feacOPHmpmANpLLiypCFnFKYKQBgzMTx@centerbeam.proxy.rlwy.net:31192/agridata'
        # 'mysql+pymysql://root:@localhost/agridata'
        #'mysql+pymysql://if0_41160083:ylbXbC9eJk6iSn@sql213.infinityfree.com/if0_41160083_agridata'
        

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, require the environment variable to be set
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://user:@localhost/agridata_prod'
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    # Use a separate test database
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'mysql+pymysql://root:@localhost/agridata_test'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}