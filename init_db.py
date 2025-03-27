from app import create_app
from extensions import db
from models.user import User, Role
from models.application import ApplicationStatus
import sys

def init_db():
    app = create_app()
    with app.app_context():
        # 创建数据库表
        db.create_all()
        
        # 检查数据库是否已初始化
        if Role.query.first() is not None:
            print('数据库已初始化.')
            return
        
        # 创建角色
        roles = [
            {'name': '管理员', 'description': '系统管理员，拥有所有权限'},
            {'name': '部门员工', 'description': '普通员工，可以发起申请'},
            {'name': '部门审核员', 'description': '部门主管，可以审核部门员工的申请'},
            {'name': '车辆管理员', 'description': '负责车辆分配和管理'},
            {'name': '办公室审核员', 'description': '办公室主任，最终审核人'},
            {'name': '司机', 'description': '负责驾驶车辆'}
        ]
        
        for role_data in roles:
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)
        
        # 创建管理员账号
        admin = User(
            username='admin',
            email='admin@example.com',
            name='系统管理员',
            department='管理部',
            position='管理员',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # 为管理员分配角色
        admin_role = Role.query.filter_by(name='管理员').first()
        admin.roles.append(admin_role)
        
        # 创建申请状态
        statuses = [
            {'name': '待提交', 'description': '申请已创建但尚未提交'},
            {'name': '待审核', 'description': '申请已提交，等待审核'},
            {'name': '待出行', 'description': '申请已审核通过，等待出行'},
            {'name': '已完成', 'description': '申请已完成'},
            {'name': '已取消', 'description': '申请已取消'},
            {'name': '已拒绝', 'description': '申请被拒绝'}
        ]
        
        for status_data in statuses:
            status = ApplicationStatus(name=status_data['name'], description=status_data['description'])
            db.session.add(status)
        
        # 提交所有更改
        db.session.commit()
        print('数据库初始化完成.')

if __name__ == '__main__':
    app = create_app()
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        with app.app_context():
            db.drop_all()
            print('数据库已重置.')
    init_db() 