from app import create_app
from extensions import db
import os

def init_database():
    """初始化数据库结构"""
    app = create_app()
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("创建数据库表完成")

if __name__ == '__main__':
    print("开始初始化数据库...")
    init_database()
    print("数据库初始化完成") 