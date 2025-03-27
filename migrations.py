from app import app, db
from models.workflow import Workflow, WorkflowPermission
from sqlalchemy import text
import os

def upgrade_database():
    """执行数据库升级操作"""
    with app.app_context():
        # 添加Workflow新字段
        columns = [
            ('status', 'VARCHAR(20)'),
            ('published_at', 'DATETIME'),
            ('start_date', 'DATETIME'),
            ('end_date', 'DATETIME'),
            ('version', 'INTEGER'),
            ('created_by', 'INTEGER'),
            ('published_by', 'INTEGER')
        ]
        
        for column_name, column_type in columns:
            try:
                db.session.execute(text(f'ALTER TABLE workflows ADD COLUMN {column_name} {column_type}'))
                print(f"添加字段 workflows.{column_name} 成功")
            except Exception as e:
                print(f"添加字段 workflows.{column_name} 失败: {e}")
        
        # 创建工作流权限表
        try:
            sql = '''
            CREATE TABLE IF NOT EXISTS workflow_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                permission_type VARCHAR(20) NOT NULL,
                target_id INTEGER NOT NULL,
                created_at DATETIME,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
            '''
            db.session.execute(text(sql))
            print("创建表 workflow_permissions 成功")
        except Exception as e:
            print(f"创建表 workflow_permissions 失败: {e}")
        
        # 为所有现有的工作流设置默认状态
        try:
            db.session.execute(text("UPDATE workflows SET status = '草稿', version = 1 WHERE status IS NULL"))
            print("更新工作流状态成功")
        except Exception as e:
            print(f"更新工作流状态失败: {e}")
            
        db.session.commit()

if __name__ == '__main__':
    print("开始执行数据库迁移...")
    upgrade_database()
    print("数据库迁移完成") 