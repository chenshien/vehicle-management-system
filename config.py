import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_123'
    
    # 数据库配置
    DB_TYPE = os.environ.get('DB_TYPE') or 'sqlite'
    
    # SQLite配置
    SQLITE_DB_PATH = os.path.join(basedir, 'data', 'app.db')
    
    # MySQL配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_PORT = os.environ.get('MYSQL_PORT') or '3306'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'password'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'vehicle_management'
    
    # 数据库URI
    SQLALCHEMY_DATABASE_URI = None  # 将在子类中设置
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 小程序配置
    WECHAT_APPID = os.environ.get('WECHAT_APPID')
    WECHAT_SECRET = os.environ.get('WECHAT_SECRET')
    
    # 日志配置
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # 管理员配置
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'password'
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@example.com'
    
    # 应用配置
    DEBUG = True
    
    # 文件上传设置
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # 邮件设置
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your-email@example.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your-password'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'admin@example.com'
    
    # 应用相关设置
    APP_NAME = '车辆管理系统'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{Config.SQLITE_DB_PATH}'


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard_to_guess_string'
    
    # 根据DB_TYPE设置数据库URI
    if Config.DB_TYPE == 'mysql':
        SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.MYSQL_DB}'
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{Config.SQLITE_DB_PATH}'


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# 默认配置
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app_config = config[config_name] 