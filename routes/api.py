from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models.user import User
from models.vehicle import Vehicle
from models.workflow import Workflow, FormField
from models.application import Application, ApplicationForm, ApplicationStatus, ApplicationLog
from functools import wraps
import json
import hashlib
import time
import random
import string
import requests

api_bp = Blueprint('api', __name__)

# 微信配置
WECHAT_APPID = '你的微信APPID'  # 需要替换为实际的AppID
WECHAT_SECRET = '你的微信Secret'  # 需要替换为实际的Secret
WECHAT_ACCESS_TOKEN = None
WECHAT_ACCESS_TOKEN_EXPIRES = 0

# 辅助函数 - API认证检查
def api_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-API-Token')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        # TODO: 实现token验证逻辑
        
        return f(*args, **kwargs)
    return decorated_function

# 用户API
@api_bp.route('/user/info', methods=['GET'])
@api_auth_required
def get_user_info():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'name': current_user.name,
        'department': current_user.department,
        'position': current_user.position,
        'roles': current_user.get_roles()
    })

# 工作流API
@api_bp.route('/workflows', methods=['GET'])
@api_auth_required
def get_workflows():
    workflows = Workflow.query.filter_by(is_active=True).all()
    result = []
    
    for workflow in workflows:
        result.append({
            'id': workflow.id,
            'name': workflow.name,
            'description': workflow.description
        })
    
    return jsonify(result)

@api_bp.route('/workflow/<int:workflow_id>', methods=['GET'])
@api_auth_required
def get_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    result = {
        'id': workflow.id,
        'name': workflow.name,
        'description': workflow.description,
        'steps': [],
        'forms': []
    }
    
    # 获取步骤
    for step in workflow.steps:
        result['steps'].append({
            'id': step.id,
            'name': step.name,
            'description': step.description,
            'order': step.order,
            'role': step.role.name if step.role else None
        })
    
    # 获取表单
    for form in workflow.forms:
        form_data = {
            'id': form.id,
            'name': form.name,
            'description': form.description,
            'fields': []
        }
        
        for field in form.fields:
            form_data['fields'].append({
                'id': field.id,
                'name': field.name,
                'label': field.label,
                'type': field.field_type,
                'required': field.is_required,
                'order': field.order,
                'options': field.get_options(),
                'placeholder': field.placeholder,
                'default': field.default_value
            })
        
        result['forms'].append(form_data)
    
    return jsonify(result)

# 申请API
@api_bp.route('/applications', methods=['GET'])
@api_auth_required
def get_user_applications():
    applications = Application.query.filter_by(user_id=current_user.id).all()
    result = []
    
    for app in applications:
        result.append({
            'id': app.id,
            'title': app.title,
            'workflow': app.workflow.name,
            'status': app.status.name,
            'created_at': app.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify(result)

@api_bp.route('/application/<int:application_id>', methods=['GET'])
@api_auth_required
def get_application(application_id):
    app = Application.query.get_or_404(application_id)
    
    # 检查权限
    if app.user_id != current_user.id and not (current_user.has_role('管理员') or current_user.has_role('部门审核员') or current_user.has_role('车辆管理员') or current_user.has_role('办公室审核员')):
        return jsonify({'message': '无权访问此申请'}), 403
    
    result = {
        'id': app.id,
        'title': app.title,
        'workflow': app.workflow.name,
        'status': app.status.name,
        'current_step': app.current_step,
        'user': {
            'id': app.user.id,
            'name': app.user.name,
            'department': app.user.department
        },
        'vehicle': app.vehicle.to_dict() if app.vehicle else None,
        'forms': [],
        'logs': []
    }
    
    # 获取表单数据
    for form_data in app.forms:
        result['forms'].append({
            'id': form_data.id,
            'form_id': form_data.form_id,
            'form_name': form_data.form.name,
            'data': form_data.get_data()
        })
    
    # 获取日志
    for log in app.logs:
        result['logs'].append(log.to_dict())
    
    return jsonify(result)

@api_bp.route('/application/create', methods=['POST'])
@api_auth_required
def create_application():
    data = request.json
    
    if not data or not data.get('workflow_id') or not data.get('title'):
        return jsonify({'message': '缺少必要参数'}), 400
    
    workflow = Workflow.query.get_or_404(data.get('workflow_id'))
    
    # 查找待提交状态
    status = ApplicationStatus.query.filter_by(name='待提交').first()
    if not status:
        status = ApplicationStatus(name='待提交', description='申请已创建但尚未提交')
        db.session.add(status)
        db.session.commit()
    
    # 创建申请
    application = Application(
        workflow_id=workflow.id,
        user_id=current_user.id,
        status_id=status.id,
        title=data.get('title'),
        current_step=0
    )
    
    db.session.add(application)
    
    # 添加日志
    log = ApplicationLog(
        application_id=application.id,
        user_id=current_user.id,
        action='创建',
        description='创建了申请',
        step=0
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': '申请创建成功',
        'application_id': application.id
    })

@api_bp.route('/application/<int:application_id>/submit_form', methods=['POST'])
@api_auth_required
def submit_application_form(application_id):
    app = Application.query.get_or_404(application_id)
    
    # 检查权限
    if app.user_id != current_user.id:
        return jsonify({'message': '无权提交此申请表单'}), 403
    
    data = request.json
    
    if not data or not data.get('form_id') or not data.get('form_data'):
        return jsonify({'message': '缺少必要参数'}), 400
    
    # 检查表单是否存在
    form_id = data.get('form_id')
    form = None
    for wf_form in app.workflow.forms:
        if wf_form.id == form_id:
            form = wf_form
            break
    
    if not form:
        return jsonify({'message': '表单不存在'}), 400
    
    # 查找或创建表单数据
    form_data = ApplicationForm.query.filter_by(
        application_id=app.id,
        form_id=form_id
    ).first()
    
    if not form_data:
        form_data = ApplicationForm(
            application_id=app.id,
            form_id=form_id
        )
        db.session.add(form_data)
    
    # 更新表单数据
    form_data.set_data(data.get('form_data'))
    
    # 添加日志
    log = ApplicationLog(
        application_id=app.id,
        user_id=current_user.id,
        action='提交表单',
        description=f'提交了表单 {form.name}',
        step=app.current_step
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': '表单提交成功'})

@api_bp.route('/application/<int:application_id>/submit', methods=['POST'])
@api_auth_required
def submit_application(application_id):
    app = Application.query.get_or_404(application_id)
    
    # 检查权限
    if app.user_id != current_user.id:
        return jsonify({'message': '无权提交此申请'}), 403
    
    # 检查状态是否为待提交
    if app.status.name != '待提交':
        return jsonify({'message': '当前状态无法提交申请'}), 400
    
    # 更新状态为待审核
    status = ApplicationStatus.query.filter_by(name='待审核').first()
    if not status:
        status = ApplicationStatus(name='待审核', description='申请已提交，等待审核')
        db.session.add(status)
        db.session.commit()
    
    app.status_id = status.id
    app.current_step = 1  # 设置为第一个审核步骤
    
    # 添加日志
    log = ApplicationLog(
        application_id=app.id,
        user_id=current_user.id,
        action='提交申请',
        description='提交了申请，等待审核',
        step=app.current_step
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': '申请提交成功'})

# 车辆API
@api_bp.route('/vehicles', methods=['GET'])
@api_auth_required
def get_vehicles():
    vehicles = Vehicle.query.filter_by(status='可用').all()
    result = [vehicle.to_dict() for vehicle in vehicles]
    return jsonify(result)

@api_bp.route('/wechat/jsconfig', methods=['GET'])
def get_wechat_js_config():
    """
    获取微信JS SDK配置
    """
    # 获取当前页面URL
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL参数不能为空'}), 400
    
    # 获取access_token
    access_token = get_wechat_access_token()
    if not access_token:
        return jsonify({'error': '获取微信access_token失败'}), 500
    
    # 获取jsapi_ticket
    jsapi_ticket = get_wechat_jsapi_ticket(access_token)
    if not jsapi_ticket:
        return jsonify({'error': '获取微信jsapi_ticket失败'}), 500
    
    # 生成签名
    noncestr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    timestamp = int(time.time())
    
    # 按照字典序排序
    sign_dict = {
        'noncestr': noncestr,
        'jsapi_ticket': jsapi_ticket,
        'timestamp': timestamp,
        'url': url
    }
    sign_str = '&'.join(['%s=%s' % (key, sign_dict[key]) for key in sorted(sign_dict.keys())])
    signature = hashlib.sha1(sign_str.encode('utf-8')).hexdigest()
    
    # 返回配置
    config = {
        'appId': WECHAT_APPID,
        'timestamp': timestamp,
        'nonceStr': noncestr,
        'signature': signature
    }
    
    return jsonify(config)

def get_wechat_access_token():
    """
    获取微信access_token，有效期两小时
    """
    global WECHAT_ACCESS_TOKEN, WECHAT_ACCESS_TOKEN_EXPIRES
    current_time = time.time()
    
    # 如果token还有效，直接返回
    if WECHAT_ACCESS_TOKEN and current_time < WECHAT_ACCESS_TOKEN_EXPIRES - 300:  # 提前5分钟刷新
        return WECHAT_ACCESS_TOKEN
    
    # 重新获取token
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'access_token' in data:
            WECHAT_ACCESS_TOKEN = data['access_token']
            WECHAT_ACCESS_TOKEN_EXPIRES = current_time + data['expires_in']
            return WECHAT_ACCESS_TOKEN
    except Exception as e:
        current_app.logger.error(f"获取微信access_token失败：{str(e)}")
    
    return None

def get_wechat_jsapi_ticket(access_token):
    """
    获取微信jsapi_ticket
    """
    url = f"https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi"
    try:
        response = requests.get(url)
        data = response.json()
        if data['errcode'] == 0:
            return data['ticket']
    except Exception as e:
        current_app.logger.error(f"获取微信jsapi_ticket失败：{str(e)}")
    
    return None 