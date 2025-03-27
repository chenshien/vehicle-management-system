from extensions import db
from datetime import datetime
import json

# 申请状态模型
class ApplicationStatus(db.Model):
    __tablename__ = 'application_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255))
    
    # 关系
    applications = db.relationship('Application', back_populates='status')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<ApplicationStatus {self.name}>'

# 申请模型
class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('application_statuses.id'), nullable=False)
    current_step = db.Column(db.Integer, default=0)
    title = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    # 关系
    workflow = db.relationship('Workflow', back_populates='applications')
    user = db.relationship('User', back_populates='applications')
    vehicle = db.relationship('Vehicle', back_populates='applications')
    status = db.relationship('ApplicationStatus', back_populates='applications')
    forms = db.relationship('ApplicationForm', back_populates='application')
    logs = db.relationship('ApplicationLog', back_populates='application', order_by='ApplicationLog.created_at')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Application {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'workflow': self.workflow.name,
            'user': self.user.name,
            'status': self.status.name,
            'vehicle': self.vehicle.plate_number if self.vehicle else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

# 申请表单数据模型
class ApplicationForm(db.Model):
    __tablename__ = 'application_forms'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    form_id = db.Column(db.Integer, db.ForeignKey('workflow_forms.id'), nullable=False)
    form_data = db.Column(db.Text)  # JSON字符串
    
    # 关系
    application = db.relationship('Application', back_populates='forms')
    form = db.relationship('WorkflowForm', backref='application_forms')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<ApplicationForm {self.id}>'
    
    def get_data(self):
        if self.form_data:
            return json.loads(self.form_data)
        return {}
    
    def set_data(self, data):
        self.form_data = json.dumps(data)

# 申请日志模型
class ApplicationLog(db.Model):
    __tablename__ = 'application_logs'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    step = db.Column(db.Integer)
    
    # 关系
    application = db.relationship('Application', back_populates='logs')
    user = db.relationship('User', backref='application_logs')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<ApplicationLog {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.name,
            'action': self.action,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } 