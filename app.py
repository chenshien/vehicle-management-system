from flask import Flask
from extensions import db, login_manager, mail
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.application import application_bp
from routes.workflow import workflow_bp
from routes.api import api_bp
from models.user import User
from config import app_config
import os
from datetime import datetime

def create_app(config_class=app_config):
    # 确保上传文件夹存在
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'), exist_ok=True)
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # 配置登录管理器
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 添加模板上下文处理器
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(application_bp, url_prefix='/application')
    app.register_blueprint(workflow_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 注册首页路由
    @app.route('/')
    def index():
        return '<script>window.location.href="/user/dashboard";</script>'
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 