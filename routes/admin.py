from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.user import User, Role, UserRole
from models.vehicle import Vehicle
from models.workflow import Workflow, WorkflowStep, WorkflowForm, FormField
from models.application import Application, ApplicationStatus
import pandas as pd
from io import BytesIO
from functools import wraps
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# 管理员权限验证装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('管理员'):
            flash('您没有管理员权限', 'danger')
            return redirect(url_for('user.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# 用户管理
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    roles = Role.query.all()
    return render_template('admin/users.html', users=users, roles=roles)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    roles = Role.query.all()
    
    if request.method == 'POST':
        # 获取表单数据
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        department = request.form.get('department')
        position = request.form.get('position')
        phone = request.form.get('phone')
        is_active = 'is_active' in request.form
        role_ids = request.form.getlist('roles')
        
        # 验证数据
        if not username or not email or not password:
            flash('用户名、邮箱和密码为必填项', 'danger')
            return render_template('admin/user_create.html', roles=roles)
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('admin/user_create.html', roles=roles)
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash(f'用户名 {username} 已存在', 'danger')
            return render_template('admin/user_create.html', roles=roles)
        
        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            flash(f'邮箱 {email} 已存在', 'danger')
            return render_template('admin/user_create.html', roles=roles)
        
        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            name=name,
            department=department,
            position=position,
            phone=phone,
            is_active=is_active
        )
        new_user.set_password(password)
        
        # 添加用户角色
        for role_id in role_ids:
            role = Role.query.get(role_id)
            if role:
                new_user.roles.append(role)
        
        # 保存到数据库
        db.session.add(new_user)
        db.session.commit()
        
        flash('用户创建成功', 'success')
        return redirect(url_for('admin.users'))
    
    # GET请求，显示创建用户表单
    return render_template('admin/user_create.html', roles=roles)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        # 获取表单数据
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        department = request.form.get('department')
        position = request.form.get('position')
        phone = request.form.get('phone')
        is_active = 'is_active' in request.form
        role_ids = request.form.getlist('roles')
        
        # 验证数据
        if not username or not email:
            flash('用户名和邮箱为必填项', 'danger')
            return render_template('admin/user_edit.html', user=user, roles=roles)
        
        # 检查用户名是否已存在（排除当前用户）
        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            flash(f'用户名 {username} 已存在', 'danger')
            return render_template('admin/user_edit.html', user=user, roles=roles)
        
        # 检查邮箱是否已存在（排除当前用户）
        existing_user = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_user:
            flash(f'邮箱 {email} 已存在', 'danger')
            return render_template('admin/user_edit.html', user=user, roles=roles)
        
        # 如果填写了密码，则验证确认密码并更新
        if password:
            if password != confirm_password:
                flash('两次输入的密码不一致', 'danger')
                return render_template('admin/user_edit.html', user=user, roles=roles)
            user.set_password(password)
        
        # 更新用户信息
        user.username = username
        user.email = email
        user.name = name
        user.department = department
        user.position = position
        user.phone = phone
        user.is_active = is_active
        
        # 不允许管理员禁用自己的账号
        if user.id == current_user.id and not is_active:
            flash('不能禁用自己的账号', 'danger')
            return render_template('admin/user_edit.html', user=user, roles=roles)
        
        # 更新用户角色
        user.roles = []
        for role_id in role_ids:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)
        
        # 保存到数据库
        db.session.commit()
        
        flash('用户信息更新成功', 'success')
        return redirect(url_for('admin.users'))
    
    # GET请求，显示编辑用户表单
    return render_template('admin/user_edit.html', user=user, roles=roles)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # 不允许删除自己的账号
    if user.id == current_user.id:
        flash('不能删除自己的账号', 'danger')
        return redirect(url_for('admin.users'))
    
    # 检查用户是否有关联的申请
    if user.applications:
        flash('该用户有关联的申请记录，无法删除', 'danger')
        return redirect(url_for('admin.users'))
    
    # 删除用户
    db.session.delete(user)
    db.session.commit()
    
    flash('用户删除成功', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/roles', methods=['POST'])
@login_required
@admin_required
def user_roles(user_id):
    user = User.query.get_or_404(user_id)
    
    # 获取表单提交的角色ID列表
    role_ids = request.form.getlist('roles')
    
    # 清空用户当前的所有角色
    user.roles = []
    
    # 添加选定的角色
    for role_id in role_ids:
        role = Role.query.get(role_id)
        if role:
            user.roles.append(role)
    
    db.session.commit()
    flash(f'用户 {user.username} 的角色已更新', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    # 不允许禁用自己的账号
    if user.id == current_user.id:
        flash('不能修改自己的账号状态', 'danger')
        return redirect(url_for('admin.users'))
    
    # 切换用户状态
    user.is_active = not user.is_active
    db.session.commit()
    
    status_text = '激活' if user.is_active else '禁用'
    flash(f'用户 {user.username} 已{status_text}', 'success')
    return redirect(url_for('admin.users'))

# 角色管理
@admin_bp.route('/roles')
@login_required
@admin_required
def roles():
    roles = Role.query.all()
    return render_template('admin/roles.html', roles=roles)

@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_role():
    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        description = request.form.get('description')
        
        # 验证数据
        if not name:
            flash('角色名称为必填项', 'danger')
            return render_template('admin/role_create.html')
        
        # 检查角色名称是否已存在
        if Role.query.filter_by(name=name).first():
            flash(f'角色名称 {name} 已存在', 'danger')
            return render_template('admin/role_create.html')
        
        # 创建新角色
        new_role = Role(
            name=name,
            description=description
        )
        
        # 保存到数据库
        db.session.add(new_role)
        db.session.commit()
        
        flash('角色创建成功', 'success')
        return redirect(url_for('admin.roles'))
    
    # GET请求，显示创建角色表单
    return render_template('admin/role_create.html')

@admin_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        description = request.form.get('description')
        
        # 验证数据
        if not name:
            flash('角色名称为必填项', 'danger')
            return render_template('admin/role_edit.html', role=role)
        
        # 检查角色名称是否已存在（排除当前角色）
        existing_role = Role.query.filter(Role.name == name, Role.id != role_id).first()
        if existing_role:
            flash(f'角色名称 {name} 已存在', 'danger')
            return render_template('admin/role_edit.html', role=role)
        
        # 更新角色信息
        role.name = name
        role.description = description
        
        # 保存到数据库
        db.session.commit()
        
        flash('角色信息更新成功', 'success')
        return redirect(url_for('admin.roles'))
    
    # GET请求，显示编辑角色表单
    return render_template('admin/role_edit.html', role=role)

@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    # 检查是否为内置角色
    if role.name == '管理员':
        flash('不能删除系统内置角色', 'danger')
        return redirect(url_for('admin.roles'))
    
    # 解除所有用户与该角色的关联
    for user in role.users:
        user.roles.remove(role)
    
    # 删除角色
    db.session.delete(role)
    db.session.commit()
    
    flash('角色删除成功', 'success')
    return redirect(url_for('admin.roles'))

# 车辆管理
@admin_bp.route('/vehicles')
@login_required
def vehicles():
    vehicles = Vehicle.query.all()
    return render_template('admin/vehicles.html', vehicles=vehicles)

@admin_bp.route('/vehicles/create', methods=['GET', 'POST'])
@login_required
def create_vehicle():
    # 获取有司机角色的用户列表
    drivers = User.query.join(UserRole).join(Role).filter(Role.name == '司机').all()
    
    if request.method == 'POST':
        # 获取表单数据
        plate_number = request.form.get('plate_number')
        vehicle_type = request.form.get('vehicle_type')
        brand = request.form.get('brand')
        model = request.form.get('model')
        color = request.form.get('color')
        seats = request.form.get('seats')
        purchase_date = request.form.get('purchase_date')
        mileage = request.form.get('mileage')
        status = request.form.get('status')
        driver_id = request.form.get('driver_id')
        notes = request.form.get('notes')
        
        # 验证必填字段
        if not plate_number or not vehicle_type:
            flash('车牌号和车辆类型为必填项', 'danger')
            return render_template('admin/vehicle_create.html', drivers=drivers)
        
        # 检查车牌号是否已存在
        existing_vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
        if existing_vehicle:
            flash(f'车牌号 {plate_number} 已存在', 'danger')
            return render_template('admin/vehicle_create.html', drivers=drivers)
        
        # 创建车辆对象
        new_vehicle = Vehicle(
            plate_number=plate_number,
            vehicle_type=vehicle_type,
            brand=brand,
            model=model,
            color=color,
            status=status or '可用'
        )
        
        # 设置可选字段
        if seats:
            new_vehicle.seats = int(seats)
        if purchase_date:
            new_vehicle.purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date()
        if mileage:
            new_vehicle.mileage = float(mileage)
        if driver_id:
            new_vehicle.driver_id = int(driver_id)
        if notes:
            new_vehicle.notes = notes
        
        # 保存到数据库
        db.session.add(new_vehicle)
        db.session.commit()
        
        flash('车辆添加成功', 'success')
        return redirect(url_for('admin.vehicles'))
    
    # GET请求，显示表单
    return render_template('admin/vehicle_create.html', drivers=drivers)

@admin_bp.route('/vehicles/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    # 获取车辆信息
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # 获取有司机角色的用户列表
    drivers = User.query.join(UserRole).join(Role).filter(Role.name == '司机').all()
    
    if request.method == 'POST':
        # 获取表单数据
        plate_number = request.form.get('plate_number')
        vehicle_type = request.form.get('vehicle_type')
        brand = request.form.get('brand')
        model = request.form.get('model')
        color = request.form.get('color')
        seats = request.form.get('seats')
        purchase_date = request.form.get('purchase_date')
        mileage = request.form.get('mileage')
        status = request.form.get('status')
        driver_id = request.form.get('driver_id')
        notes = request.form.get('notes')
        
        # 验证必填字段
        if not plate_number or not vehicle_type:
            flash('车牌号和车辆类型为必填项', 'danger')
            return render_template('admin/vehicle_edit.html', vehicle=vehicle, drivers=drivers)
        
        # 检查车牌号是否已存在（排除当前车辆）
        existing_vehicle = Vehicle.query.filter(Vehicle.plate_number == plate_number, Vehicle.id != vehicle_id).first()
        if existing_vehicle:
            flash(f'车牌号 {plate_number} 已存在', 'danger')
            return render_template('admin/vehicle_edit.html', vehicle=vehicle, drivers=drivers)
        
        # 更新车辆信息
        vehicle.plate_number = plate_number
        vehicle.vehicle_type = vehicle_type
        vehicle.brand = brand
        vehicle.model = model
        vehicle.color = color
        vehicle.status = status
        
        # 更新可选字段
        vehicle.seats = int(seats) if seats else None
        vehicle.purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date() if purchase_date else None
        vehicle.mileage = float(mileage) if mileage else 0
        vehicle.driver_id = int(driver_id) if driver_id else None
        vehicle.notes = notes
        
        # 保存到数据库
        db.session.commit()
        
        flash('车辆信息更新成功', 'success')
        return redirect(url_for('admin.vehicles'))
    
    # GET请求，显示表单
    return render_template('admin/vehicle_edit.html', vehicle=vehicle, drivers=drivers)

@admin_bp.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # 检查车辆是否正在使用中
    if vehicle.applications:
        flash('该车辆有关联的申请记录，无法删除', 'danger')
        return redirect(url_for('admin.vehicles'))
    
    # 删除车辆
    db.session.delete(vehicle)
    db.session.commit()
    
    flash('车辆删除成功', 'success')
    return redirect(url_for('admin.vehicles'))

# 工作流管理
@admin_bp.route('/workflows')
@login_required
@admin_required
def workflows():
    workflows = Workflow.query.all()
    return render_template('admin/workflows.html', workflows=workflows)

@admin_bp.route('/workflows/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_workflow():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('工作流名称不能为空', 'danger')
            return render_template('admin/workflow_create.html')
        
        # 创建工作流
        workflow = Workflow(
            name=name,
            description=description,
            status='草稿',
            version=1,
            created_by=current_user.id
        )
        
        db.session.add(workflow)
        db.session.commit()
        
        flash('工作流创建成功', 'success')
        return redirect(url_for('admin.edit_workflow', workflow_id=workflow.id))
    
    return render_template('admin/workflow_create.html')

@admin_bp.route('/workflows/<int:workflow_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流', 'danger')
        return redirect(url_for('admin.workflows'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('工作流名称不能为空', 'danger')
            return render_template('admin/workflow_edit.html', workflow=workflow)
        
        # 更新工作流
        workflow.name = name
        workflow.description = description
        
        db.session.commit()
        
        flash('工作流更新成功', 'success')
        return redirect(url_for('admin.workflows'))
    
    return render_template('admin/workflow_edit.html', workflow=workflow)

@admin_bp.route('/workflows/<int:workflow_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否有关联的申请
    if workflow.applications.count() > 0:
        flash('该工作流已有关联的申请记录，无法删除', 'danger')
        return redirect(url_for('admin.workflows'))
    
    # 删除关联的表单字段
    forms = WorkflowForm.query.filter_by(workflow_id=workflow_id).all()
    for form in forms:
        fields = FormField.query.filter_by(form_id=form.id).all()
        for field in fields:
            db.session.delete(field)
        db.session.delete(form)
    
    # 删除关联的步骤
    steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).all()
    for step in steps:
        db.session.delete(step)
    
    # 删除工作流
    db.session.delete(workflow)
    db.session.commit()
    
    flash('工作流删除成功', 'success')
    return redirect(url_for('admin.workflows'))

@admin_bp.route('/workflows/<int:workflow_id>/steps', methods=['GET', 'POST'])
@login_required
@admin_required
def workflow_steps(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).order_by(WorkflowStep.order).all()
    roles = Role.query.all()
    forms = WorkflowForm.query.filter_by(workflow_id=workflow_id).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        role_id = request.form.get('role_id')
        form_id = request.form.get('form_id')
        
        if not name:
            flash('步骤名称不能为空', 'danger')
            return redirect(url_for('admin.workflow_steps', workflow_id=workflow_id))
        
        # 获取当前最大的排序值
        max_order = db.session.query(db.func.max(WorkflowStep.order)).filter(
            WorkflowStep.workflow_id == workflow_id).scalar() or 0
        
        # 创建新步骤
        step = WorkflowStep(
            workflow_id=workflow_id,
            name=name,
            description=description,
            role_id=role_id if role_id else None,
            form_id=form_id if form_id else None,
            order=max_order + 1
        )
        
        db.session.add(step)
        db.session.commit()
        
        flash('步骤添加成功', 'success')
        return redirect(url_for('admin.workflow_steps', workflow_id=workflow_id))
    
    return render_template('admin/workflow_steps.html', 
                          workflow=workflow, 
                          steps=steps, 
                          roles=roles, 
                          forms=forms)

@admin_bp.route('/workflows/<int:workflow_id>/forms', methods=['GET'])
@login_required
@admin_required
def workflow_forms(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    forms = WorkflowForm.query.filter_by(workflow_id=workflow_id).all()
    
    return render_template('admin/workflow_forms.html', workflow=workflow, forms=forms)

@admin_bp.route('/workflows/<int:workflow_id>/forms/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_workflow_form(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('表单名称不能为空', 'danger')
            return render_template('admin/workflow_form_create.html', workflow=workflow)
        
        # 创建新表单
        form = WorkflowForm(
            workflow_id=workflow_id,
            name=name,
            description=description
        )
        
        db.session.add(form)
        db.session.commit()
        
        flash('表单创建成功', 'success')
        return redirect(url_for('admin.workflow_forms', workflow_id=workflow_id))
    
    return render_template('admin/workflow_form_create.html', workflow=workflow)

@admin_bp.route('/workflow/form/<int:form_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_workflow_form(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流的表单）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态工作流的表单', 'danger')
        return redirect(url_for('admin.workflow_forms', workflow_id=workflow.id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('表单名称不能为空', 'danger')
            return render_template('admin/workflow_form_edit.html', form=form, workflow=workflow)
        
        # 更新表单
        form.name = name
        form.description = description
        
        db.session.commit()
        
        flash('表单更新成功', 'success')
        return redirect(url_for('admin.workflow_forms', workflow_id=workflow.id))
    
    return render_template('admin/workflow_form_edit.html', form=form, workflow=workflow)

@admin_bp.route('/workflow/form/<int:form_id>/fields', methods=['GET'])
@login_required
@admin_required
def workflow_form_fields(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    fields = FormField.query.filter_by(form_id=form_id).order_by(FormField.order).all()
    
    return render_template('admin/workflow_form_fields.html', 
                          form=form, 
                          workflow=workflow, 
                          fields=fields,
                          field_types=FormField.get_field_types())

@admin_bp.route('/workflow/form/<int:form_id>/field/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_form_field(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流的表单）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态工作流的表单', 'danger')
        return redirect(url_for('admin.workflow_form_fields', form_id=form_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        label = request.form.get('label')
        field_type = request.form.get('field_type')
        is_required = 'is_required' in request.form
        placeholder = request.form.get('placeholder')
        default_value = request.form.get('default_value')
        options = request.form.get('options')
        
        if not name or not label or not field_type:
            flash('字段名称、标签和类型为必填项', 'danger')
            return render_template('admin/workflow_form_field_create.html', 
                                 form=form, 
                                 workflow=workflow,
                                 field_types=FormField.get_field_types())
        
        # 获取当前最大的排序值
        max_order = db.session.query(db.func.max(FormField.order)).filter(
            FormField.form_id == form_id).scalar() or 0
        
        # 创建新字段
        field = FormField(
            form_id=form_id,
            name=name,
            label=label,
            field_type=field_type,
            is_required=is_required,
            placeholder=placeholder,
            default_value=default_value,
            options=options,
            order=max_order + 1
        )
        
        db.session.add(field)
        db.session.commit()
        
        flash('字段创建成功', 'success')
        return redirect(url_for('admin.workflow_form_fields', form_id=form_id))
    
    return render_template('admin/workflow_form_field_create.html', 
                         form=form, 
                         workflow=workflow,
                         field_types=FormField.get_field_types())

@admin_bp.route('/workflow/form/field/<int:field_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_form_field(field_id):
    field = FormField.query.get_or_404(field_id)
    form = WorkflowForm.query.get_or_404(field.form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流的表单字段）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态工作流的表单字段', 'danger')
        return redirect(url_for('admin.workflow_form_fields', form_id=form.id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        label = request.form.get('label')
        field_type = request.form.get('field_type')
        is_required = 'is_required' in request.form
        placeholder = request.form.get('placeholder')
        default_value = request.form.get('default_value')
        options = request.form.get('options')
        
        if not name or not label or not field_type:
            flash('字段名称、标签和类型为必填项', 'danger')
            return render_template('admin/workflow_form_field_edit.html', 
                                  field=field,
                                  form=form, 
                                  workflow=workflow,
                                  field_types=FormField.get_field_types())
        
        # 更新字段
        field.name = name
        field.label = label
        field.field_type = field_type
        field.is_required = is_required
        field.placeholder = placeholder
        field.default_value = default_value
        field.options = options
        
        db.session.commit()
        
        flash('字段更新成功', 'success')
        return redirect(url_for('admin.workflow_form_fields', form_id=form.id))
    
    return render_template('admin/workflow_form_field_edit.html', 
                         field=field,
                         form=form, 
                         workflow=workflow,
                         field_types=FormField.get_field_types())

@admin_bp.route('/workflow/form/field/<int:field_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_form_field(field_id):
    field = FormField.query.get_or_404(field_id)
    form_id = field.form_id
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    
    # 检查是否可以删除（只能删除草稿状态的工作流的表单字段）
    if workflow.status != '草稿':
        flash('只能删除草稿状态工作流的表单字段', 'danger')
        return redirect(url_for('admin.workflow_form_fields', form_id=form_id))
    
    # 获取该字段之后的所有字段
    later_fields = FormField.query.filter(
        FormField.form_id == form_id,
        FormField.order > field.order
    ).all()
    
    # 删除字段
    db.session.delete(field)
    
    # 更新后续字段的顺序
    for later_field in later_fields:
        later_field.order -= 1
    
    db.session.commit()
    
    flash('字段删除成功', 'success')
    return redirect(url_for('admin.workflow_form_fields', form_id=form_id))

# 申请管理
@admin_bp.route('/applications')
@login_required
def applications():
    applications = Application.query.all()
    return render_template('admin/applications.html', applications=applications)

@admin_bp.route('/applications/<int:application_id>')
@login_required
def application_detail(application_id):
    # 获取申请详情
    application = Application.query.get_or_404(application_id)
    
    # 检查权限（仅管理员或申请人本人可查看）
    if not current_user.has_role('管理员') and current_user.id != application.user_id:
        flash('您没有权限查看此申请', 'danger')
        return redirect(url_for('admin.applications'))
    
    return render_template('admin/application_detail.html', application=application)

@admin_bp.route('/applications/<int:application_id>/approve', methods=['POST'])
@login_required
def approve_application(application_id):
    # 获取申请详情
    application = Application.query.get_or_404(application_id)
    
    # 检查权限（仅管理员可审批）
    if not current_user.has_role('管理员'):
        flash('您没有权限审批申请', 'danger')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    # 检查申请状态
    if application.status.name != '审批中':
        flash('只能审批状态为"审批中"的申请', 'warning')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    # 获取并保存备注信息
    comment = request.form.get('comment', '')
    
    # 更新申请状态为"已通过"
    approved_status = ApplicationStatus.query.filter_by(name='已通过').first()
    if not approved_status:
        flash('系统错误：找不到状态"已通过"', 'danger')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    application.status_id = approved_status.id
    
    # 创建审批日志
    log = ApplicationLog(
        application_id=application.id,
        user_id=current_user.id,
        action='approve',
        description=f'已通过申请。备注：{comment}' if comment else '已通过申请',
        step=application.current_step
    )
    
    # 如果申请涉及车辆，则更新车辆状态
    if application.vehicle:
        application.vehicle.status = '预约中'
    
    # 保存变更
    db.session.add(log)
    db.session.commit()
    
    # 发送通知邮件
    try:
        from utils.mail import send_email
        subject = f'您的申请 {application.title} 已通过'
        body = f'''尊敬的 {application.user.name}：
        
您的申请 #{application.id} {application.title} 已被管理员通过。

申请详情：
- 工作流：{application.workflow.name}
- 提交时间：{application.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- 审批时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{f"管理员备注：{comment}" if comment else ""}

请登录系统查看更多详情。
        '''
        send_email(application.user.email, subject, body)
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
    
    flash('申请已通过', 'success')
    return redirect(url_for('admin.applications'))

@admin_bp.route('/applications/<int:application_id>/reject', methods=['POST'])
@login_required
def reject_application(application_id):
    # 获取申请详情
    application = Application.query.get_or_404(application_id)
    
    # 检查权限（仅管理员可审批）
    if not current_user.has_role('管理员'):
        flash('您没有权限审批申请', 'danger')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    # 检查申请状态
    if application.status.name != '审批中':
        flash('只能审批状态为"审批中"的申请', 'warning')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    # 获取拒绝原因
    reason = request.form.get('reason')
    if not reason:
        flash('拒绝原因不能为空', 'danger')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    # 更新申请状态为"已拒绝"
    rejected_status = ApplicationStatus.query.filter_by(name='已拒绝').first()
    if not rejected_status:
        flash('系统错误：找不到状态"已拒绝"', 'danger')
        return redirect(url_for('admin.application_detail', application_id=application_id))
    
    application.status_id = rejected_status.id
    
    # 创建审批日志
    log = ApplicationLog(
        application_id=application.id,
        user_id=current_user.id,
        action='reject',
        description=f'已拒绝申请。原因：{reason}',
        step=application.current_step
    )
    
    # 如果申请涉及车辆，恢复车辆状态为可用
    if application.vehicle and application.vehicle.status == '预约中':
        application.vehicle.status = '可用'
    
    # 保存变更
    db.session.add(log)
    db.session.commit()
    
    # 发送通知邮件
    try:
        from utils.mail import send_email
        subject = f'您的申请 {application.title} 已被拒绝'
        body = f'''尊敬的 {application.user.name}：
        
很遗憾，您的申请 #{application.id} {application.title} 被管理员拒绝。

申请详情：
- 工作流：{application.workflow.name}
- 提交时间：{application.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- 拒绝时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 拒绝原因：{reason}

请登录系统查看更多详情。
        '''
        send_email(application.user.email, subject, body)
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
    
    flash('申请已拒绝', 'warning')
    return redirect(url_for('admin.applications'))

# 数据导出
@admin_bp.route('/export/applications')
@login_required
@admin_required
def export_applications():
    # 导出申请数据为Excel
    applications = Application.query.all()
    
    # 准备数据
    data = []
    for app in applications:
        data.append({
            'ID': app.id,
            '标题': app.title,
            '申请人': app.user.name,
            '工作流': app.workflow.name,
            '状态': app.status.name,
            '车辆': app.vehicle.plate_number if app.vehicle else '',
            '创建时间': app.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '更新时间': app.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='申请列表')
        # 自动调整列宽
        worksheet = writer.sheets['申请列表']
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
            worksheet.column_dimensions[chr(65 + i)].width = column_width
    
    output.seek(0)
    
    # 设置响应头，使浏览器下载文件
    from flask import send_file
    filename = f'申请列表_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@admin_bp.route('/export/vehicles')
@login_required
@admin_required
def export_vehicles():
    # 导出车辆数据为Excel
    vehicles = Vehicle.query.all()
    
    # 准备数据
    data = []
    for vehicle in vehicles:
        data.append({
            'ID': vehicle.id,
            '车牌号': vehicle.plate_number,
            '类型': vehicle.vehicle_type,
            '品牌': vehicle.brand or '',
            '型号': vehicle.model or '',
            '颜色': vehicle.color or '',
            '座位数': vehicle.seats or '',
            '状态': vehicle.status,
            '驾驶员': vehicle.driver.name if vehicle.driver else '',
            '购买日期': vehicle.purchase_date.strftime('%Y-%m-%d') if vehicle.purchase_date else '',
            '里程数': vehicle.mileage or 0,
            '备注': vehicle.notes or ''
        })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='车辆列表')
        # 自动调整列宽
        worksheet = writer.sheets['车辆列表']
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
            worksheet.column_dimensions[chr(65 + i)].width = column_width
    
    output.seek(0)
    
    # 设置响应头，使浏览器下载文件
    from flask import send_file
    filename = f'车辆列表_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@admin_bp.route('/workflow/step/<int:step_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_workflow_step(step_id):
    step = WorkflowStep.query.get_or_404(step_id)
    workflow = Workflow.query.get_or_404(step.workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流步骤', 'danger')
        return redirect(url_for('admin.workflow_steps', workflow_id=workflow.id))
    
    name = request.form.get('name')
    description = request.form.get('description')
    role_id = request.form.get('role_id')
    form_id = request.form.get('form_id')
    
    if not name:
        flash('步骤名称不能为空', 'danger')
        return redirect(url_for('admin.workflow_steps', workflow_id=workflow.id))
    
    # 更新步骤
    step.name = name
    step.description = description
    step.role_id = role_id if role_id else None
    step.form_id = form_id if form_id else None
    
    db.session.commit()
    
    flash('步骤更新成功', 'success')
    return redirect(url_for('admin.workflow_steps', workflow_id=workflow.id))

@admin_bp.route('/workflow/step/<int:step_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_workflow_step(step_id):
    step = WorkflowStep.query.get_or_404(step_id)
    workflow_id = step.workflow_id
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以删除（只能删除草稿状态的工作流的步骤）
    if workflow.status != '草稿':
        flash('只能删除草稿状态的工作流步骤', 'danger')
        return redirect(url_for('admin.workflow_steps', workflow_id=workflow_id))
    
    # 获取该步骤之后的所有步骤
    later_steps = WorkflowStep.query.filter(
        WorkflowStep.workflow_id == workflow_id,
        WorkflowStep.order > step.order
    ).all()
    
    # 删除步骤
    db.session.delete(step)
    
    # 更新后续步骤的顺序
    for later_step in later_steps:
        later_step.order -= 1
    
    db.session.commit()
    
    flash('步骤删除成功', 'success')
    return redirect(url_for('admin.workflow_steps', workflow_id=workflow_id))

@admin_bp.route('/workflow/form/<int:form_id>/preview', methods=['GET'])
@login_required
@admin_required
def preview_form(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    fields = FormField.query.filter_by(form_id=form_id).order_by(FormField.order).all()
    
    return render_template('admin/workflow_form_preview.html', 
                          form=form, 
                          workflow=workflow, 
                          fields=fields)

@admin_bp.route('/workflows/<int:workflow_id>/visual-design', methods=['GET', 'POST'])
@login_required
@admin_required
def workflow_visual_design(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).order_by(WorkflowStep.order).all()
    roles = Role.query.all()
    forms = WorkflowForm.query.filter_by(workflow_id=workflow_id).all()
    
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        
        # 删除所有现有步骤
        for step in steps:
            db.session.delete(step)
        
        # 创建新步骤
        for i, step_data in enumerate(data.get('steps', [])):
            role_id = step_data.get('role_id')
            form_id = step_data.get('form_id')
            
            step = WorkflowStep(
                workflow_id=workflow_id,
                name=step_data.get('name'),
                description=step_data.get('description', ''),
                role_id=int(role_id) if role_id else None,
                form_id=int(form_id) if form_id else None,
                order=i + 1
            )
            db.session.add(step)
        
        db.session.commit()
        return jsonify({"success": True, "message": "工作流设计已保存"})
    
    return render_template('admin/workflow_visual_design.html', 
                          workflow=workflow, 
                          steps=steps, 
                          roles=roles, 
                          forms=forms)

@admin_bp.route('/workflow/form/<int:form_id>/visual-design', methods=['GET', 'POST'])
@login_required
@admin_required
def form_visual_design(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = Workflow.query.get_or_404(form.workflow_id)
    fields = FormField.query.filter_by(form_id=form_id).order_by(FormField.order).all()
    field_types = FormField.get_field_types()
    
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        
        # 删除所有现有字段
        for field in fields:
            db.session.delete(field)
        
        # 创建新字段
        for i, field_data in enumerate(data.get('fields', [])):
            field = FormField(
                form_id=form_id,
                name=field_data.get('name'),
                label=field_data.get('label'),
                field_type=field_data.get('field_type'),
                is_required=field_data.get('is_required', False),
                placeholder=field_data.get('placeholder', ''),
                default_value=field_data.get('default_value', ''),
                options=field_data.get('options', ''),
                order=i + 1
            )
            db.session.add(field)
        
        db.session.commit()
        return jsonify({"success": True, "message": "表单设计已保存"})
    
    return render_template('admin/form_visual_design.html', 
                          form=form, 
                          workflow=workflow, 
                          fields=fields,
                          field_types=field_types) 