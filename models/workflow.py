from extensions import db
from datetime import datetime
import json

# 工作流模型
class Workflow(db.Model):
    __tablename__ = 'workflows'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='草稿')  # 草稿、已发布、已下线
    published_at = db.Column(db.DateTime)
    start_date = db.Column(db.DateTime)  # 有效期开始时间，为空表示立即生效
    end_date = db.Column(db.DateTime)  # 有效期结束时间，为空表示永久有效
    version = db.Column(db.Integer, default=1)  # 流程版本号
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 关系
    steps = db.relationship('WorkflowStep', back_populates='workflow', order_by='WorkflowStep.order')
    forms = db.relationship('WorkflowForm', back_populates='workflow')
    applications = db.relationship('Application', back_populates='workflow')
    permissions = db.relationship('WorkflowPermission', back_populates='workflow', cascade='all, delete-orphan')
    
    creator = db.relationship('User', foreign_keys=[created_by])
    publisher = db.relationship('User', foreign_keys=[published_by])
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Workflow {self.name}>'
    
    def is_published(self):
        """检查流程是否已发布"""
        return self.status == '已发布'
    
    def is_effective(self):
        """检查流程是否在有效期内"""
        if not self.is_published():
            return False
            
        now = datetime.now()
        
        # 检查有效期开始时间（如果有设置）
        if self.start_date and now < self.start_date:
            return False
            
        # 检查有效期结束时间（如果有设置）
        if self.end_date and now > self.end_date:
            return False
            
        return True
    
    def can_be_initiated_by(self, user):
        """检查用户是否有权限发起此流程"""
        if not self.is_effective():
            return False
            
        # 管理员可以发起任何流程
        if user.has_role('管理员'):
            return True
            
        # 检查用户权限
        for perm in self.permissions:
            if perm.permission_type == 'user' and perm.target_id == user.id:
                return True
            elif perm.permission_type == 'role' and user.has_role_id(perm.target_id):
                return True
                
        # 如果没有设置任何权限，则任何用户都可以发起
        return len(self.permissions) == 0
    
    def publish(self, publisher_id, start_date=None, end_date=None):
        """发布流程"""
        self.status = '已发布'
        self.published_at = datetime.now()
        self.published_by = publisher_id
        self.start_date = start_date
        self.end_date = end_date
        return True
    
    def unpublish(self):
        """下线流程"""
        self.status = '已下线'
        return True
    
    def new_version(self):
        """创建新版本"""
        new_workflow = Workflow(
            name=self.name,
            description=self.description,
            is_active=True,
            status='草稿',
            version=self.version + 1,
            created_by=self.created_by
        )
        db.session.add(new_workflow)
        return new_workflow

# 工作流步骤模型
class WorkflowStep(db.Model):
    __tablename__ = 'workflow_steps'
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    form_id = db.Column(db.Integer, db.ForeignKey('workflow_forms.id'))
    
    # 关系
    workflow = db.relationship('Workflow', back_populates='steps')
    role = db.relationship('Role', backref='workflow_steps')
    form = db.relationship('WorkflowForm', backref='workflow_steps')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<WorkflowStep {self.name}>'

# 表单模型
class WorkflowForm(db.Model):
    __tablename__ = 'workflow_forms'
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # 关系
    workflow = db.relationship('Workflow', back_populates='forms')
    fields = db.relationship('FormField', back_populates='form', order_by='FormField.order')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<WorkflowForm {self.name}>'

# 表单字段模型
class FormField(db.Model):
    __tablename__ = 'form_fields'
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('workflow_forms.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, date, select, file, location, etc.
    is_required = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, nullable=False)
    options = db.Column(db.Text)  # JSON字符串，用于select类型字段，对location类型存储地图配置
    placeholder = db.Column(db.String(255))
    default_value = db.Column(db.String(255))
    visible_steps = db.Column(db.Text)  # JSON字符串，存储可见的步骤ID列表
    editable_steps = db.Column(db.Text)  # JSON字符串，存储可编辑的步骤ID列表
    config = db.Column(db.Text)  # JSON字符串，存储其他配置项
    
    # 关系
    form = db.relationship('WorkflowForm', back_populates='fields')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<FormField {self.name}>'
    
    def get_options(self):
        if self.options:
            return json.loads(self.options)
        return []
    
    def get_visible_steps(self):
        """获取字段可见的步骤ID列表"""
        if self.visible_steps:
            return json.loads(self.visible_steps)
        return []  # 如果未设置，默认在所有步骤可见
    
    def get_editable_steps(self):
        """获取字段可编辑的步骤ID列表"""
        if self.editable_steps:
            return json.loads(self.editable_steps)
        return []  # 如果未设置，默认在所有步骤可编辑
    
    def get_config(self):
        """获取字段的其他配置项"""
        if self.config:
            return json.loads(self.config)
        return {}
    
    def is_visible_in_step(self, step_id):
        """判断字段在指定步骤是否可见"""
        visible_steps = self.get_visible_steps()
        return len(visible_steps) == 0 or step_id in visible_steps
    
    def is_editable_in_step(self, step_id):
        """判断字段在指定步骤是否可编辑"""
        editable_steps = self.get_editable_steps()
        return len(editable_steps) == 0 or step_id in editable_steps
        
    @staticmethod
    def get_field_types():
        """获取所有支持的字段类型"""
        return [
            {'value': 'text', 'label': '单行文本'},
            {'value': 'textarea', 'label': '多行文本'},
            {'value': 'number', 'label': '数字'},
            {'value': 'date', 'label': '日期'},
            {'value': 'datetime', 'label': '日期时间'},
            {'value': 'select', 'label': '下拉选择'},
            {'value': 'radio', 'label': '单选按钮'},
            {'value': 'checkbox', 'label': '复选框'},
            {'value': 'file', 'label': '文件上传'},
            {'value': 'location', 'label': '位置信息'}
        ]

# 工作流权限模型
class WorkflowPermission(db.Model):
    __tablename__ = 'workflow_permissions'
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    permission_type = db.Column(db.String(20), nullable=False)  # user或role
    target_id = db.Column(db.Integer, nullable=False)  # 用户ID或角色ID
    
    # 关系
    workflow = db.relationship('Workflow', back_populates='permissions')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<WorkflowPermission {self.permission_type}:{self.target_id}>' 