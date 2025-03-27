from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

# 数据库实例
db = SQLAlchemy()

# 登录管理器
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录才能访问此页面'
login_manager.login_message_category = 'info'

# 邮件实例
mail = Mail() 