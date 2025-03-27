from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.workflow import Workflow, WorkflowStep, WorkflowForm, FormField, WorkflowPermission
from models.user import User, Role
from models.application import Application, ApplicationForm, ApplicationStatus, ApplicationLog
from utils.decorators import admin_required, role_required
from datetime import datetime
import json

workflow_bp = Blueprint('workflow', __name__)

# 工作流列表
@workflow_bp.route('/workflows')
@login_required
@admin_required
def workflows():
    workflows = Workflow.query.all()
    return render_template('admin/workflows.html', workflows=workflows)

# 创建工作流
@workflow_bp.route('/workflow/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_workflow():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('名称不能为空', 'danger')
            return redirect(url_for('workflow.create_workflow'))
        
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
        return redirect(url_for('workflow.edit_workflow', workflow_id=workflow.id))
    
    return render_template('admin/workflow_create.html')

# 编辑工作流
@workflow_bp.route('/workflow/<int:workflow_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    if request.method == 'POST':
        workflow.name = request.form.get('name')
        workflow.description = request.form.get('description')
        workflow.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('工作流更新成功', 'success')
        return redirect(url_for('workflow.edit_workflow', workflow_id=workflow.id))
    
    return render_template('admin/workflow_edit.html', workflow=workflow)

# 工作流详情
@workflow_bp.route('/workflow/<int:workflow_id>')
@login_required
@admin_required
def workflow_detail(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).order_by(WorkflowStep.order).all()
    forms = WorkflowForm.query.filter_by(workflow_id=workflow_id).all()
    
    # 获取权限设置
    permissions = WorkflowPermission.query.filter_by(workflow_id=workflow_id).all()
    user_permissions = []
    role_permissions = []
    
    for perm in permissions:
        if perm.permission_type == 'user':
            user = User.query.get(perm.target_id)
            if user:
                user_permissions.append(user)
        elif perm.permission_type == 'role':
            role = Role.query.get(perm.target_id)
            if role:
                role_permissions.append(role)
    
    return render_template('admin/workflow_detail.html', 
                           workflow=workflow, 
                           steps=steps, 
                           forms=forms,
                           user_permissions=user_permissions,
                           role_permissions=role_permissions)

# 发布工作流
@workflow_bp.route('/workflow/<int:workflow_id>/publish', methods=['GET', 'POST'])
@login_required
@admin_required
def publish_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以发布（只能发布草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能发布草稿状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    # 检查是否已配置步骤
    steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).count()
    if steps == 0:
        flash('工作流必须至少有一个步骤才能发布', 'danger')
        return redirect(url_for('workflow.edit_workflow', workflow_id=workflow_id))
    
    # 获取所有用户和角色（用于选择权限）
    users = User.query.all()
    roles = Role.query.all()
    
    if request.method == 'POST':
        # 处理有效期
        start_date = None
        end_date = None
        
        if request.form.get('start_date'):
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        
        if request.form.get('end_date'):
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            end_date = datetime.combine(end_date, datetime.max.time())  # 设置为当天的23:59:59
        
        # 处理权限
        current_perms = WorkflowPermission.query.filter_by(workflow_id=workflow_id).all()
        for perm in current_perms:
            db.session.delete(perm)
        
        # 添加用户权限
        user_ids = request.form.getlist('user_ids')
        for user_id in user_ids:
            perm = WorkflowPermission(
                workflow_id=workflow_id,
                permission_type='user',
                target_id=int(user_id)
            )
            db.session.add(perm)
        
        # 添加角色权限
        role_ids = request.form.getlist('role_ids')
        for role_id in role_ids:
            perm = WorkflowPermission(
                workflow_id=workflow_id,
                permission_type='role',
                target_id=int(role_id)
            )
            db.session.add(perm)
        
        # 发布工作流
        workflow.publish(current_user.id, start_date, end_date)
        db.session.commit()
        
        flash('工作流发布成功', 'success')
        return redirect(url_for('workflow.workflow_detail', workflow_id=workflow_id))
    
    return render_template('admin/workflow_publish.html', workflow=workflow, users=users, roles=roles)

# 下线工作流
@workflow_bp.route('/workflow/<int:workflow_id>/unpublish', methods=['POST'])
@login_required
@admin_required
def unpublish_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以下线（只能下线已发布状态的工作流）
    if workflow.status != '已发布':
        flash('只能下线已发布状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    workflow.unpublish()
    db.session.commit()
    
    flash('工作流已下线', 'success')
    return redirect(url_for('workflow.workflow_detail', workflow_id=workflow_id))

# 创建工作流新版本
@workflow_bp.route('/workflow/<int:workflow_id>/new_version', methods=['POST'])
@login_required
@admin_required
def new_workflow_version(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以创建新版本（只能为已发布或已下线的工作流创建新版本）
    if workflow.status == '草稿':
        flash('草稿状态的工作流不需要创建新版本', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    new_workflow = workflow.new_version()
    db.session.commit()
    
    # 复制步骤和表单
    old_steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).all()
    new_form_map = {}  # 存储旧表单ID到新表单ID的映射
    
    # 首先复制表单
    old_forms = WorkflowForm.query.filter_by(workflow_id=workflow_id).all()
    for old_form in old_forms:
        new_form = WorkflowForm(
            workflow_id=new_workflow.id,
            name=old_form.name,
            description=old_form.description
        )
        db.session.add(new_form)
        db.session.flush()
        
        new_form_map[old_form.id] = new_form.id
        
        # 复制表单字段
        old_fields = FormField.query.filter_by(form_id=old_form.id).all()
        for old_field in old_fields:
            new_field = FormField(
                form_id=new_form.id,
                name=old_field.name,
                label=old_field.label,
                field_type=old_field.field_type,
                is_required=old_field.is_required,
                order=old_field.order,
                options=old_field.options,
                placeholder=old_field.placeholder,
                default_value=old_field.default_value,
                visible_steps=old_field.visible_steps,
                editable_steps=old_field.editable_steps,
                config=old_field.config
            )
            db.session.add(new_field)
    
    # 然后复制步骤
    for old_step in old_steps:
        # 处理表单ID
        new_form_id = None
        if old_step.form_id and old_step.form_id in new_form_map:
            new_form_id = new_form_map[old_step.form_id]
        
        new_step = WorkflowStep(
            workflow_id=new_workflow.id,
            name=old_step.name,
            description=old_step.description,
            order=old_step.order,
            role_id=old_step.role_id,
            form_id=new_form_id
        )
        db.session.add(new_step)
    
    db.session.commit()
    
    flash('已创建工作流新版本', 'success')
    return redirect(url_for('workflow.edit_workflow', workflow_id=new_workflow.id))

# 添加工作流步骤
@workflow_bp.route('/workflow/<int:workflow_id>/step/add', methods=['POST'])
@login_required
@admin_required
def add_workflow_step(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    role_id = request.form.get('role_id')
    form_id = request.form.get('form_id')
    
    # 确定步骤顺序
    max_order = db.session.query(db.func.max(WorkflowStep.order)).filter_by(workflow_id=workflow_id).scalar() or 0
    
    step = WorkflowStep(
        workflow_id=workflow_id,
        name=name,
        description=description,
        role_id=role_id,
        form_id=form_id,
        order=max_order + 1
    )
    
    db.session.add(step)
    db.session.commit()
    
    flash('工作流步骤添加成功', 'success')
    return redirect(url_for('workflow.edit_workflow', workflow_id=workflow_id))

# 删除工作流步骤
@workflow_bp.route('/workflow/step/<int:step_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_workflow_step(step_id):
    step = WorkflowStep.query.get_or_404(step_id)
    workflow_id = step.workflow_id
    workflow = Workflow.query.get(workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    db.session.delete(step)
    db.session.commit()
    
    # 重新排序步骤
    steps = WorkflowStep.query.filter_by(workflow_id=workflow_id).order_by(WorkflowStep.order).all()
    for i, step in enumerate(steps, 1):
        step.order = i
    
    db.session.commit()
    
    flash('工作流步骤删除成功', 'success')
    return redirect(url_for('workflow.edit_workflow', workflow_id=workflow_id))

# 表单设计
@workflow_bp.route('/workflow/<int:workflow_id>/form/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_form(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        form = WorkflowForm(
            workflow_id=workflow_id,
            name=name,
            description=description
        )
        
        db.session.add(form)
        db.session.commit()
        
        flash('表单创建成功', 'success')
        return redirect(url_for('workflow.edit_form', form_id=form.id))
    
    return render_template('admin/workflow_form_create.html', workflow=workflow)

# 编辑表单
@workflow_bp.route('/form/<int:form_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_form(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = form.workflow
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        flash('只能编辑草稿状态的工作流', 'danger')
        return redirect(url_for('workflow.workflows'))
    
    if request.method == 'POST':
        form.name = request.form.get('name')
        form.description = request.form.get('description')
        
        db.session.commit()
        flash('表单更新成功', 'success')
    
    # 获取表单字段
    fields = FormField.query.filter_by(form_id=form_id).order_by(FormField.order).all()
    # 获取工作流步骤
    steps = WorkflowStep.query.filter_by(workflow_id=workflow.id).order_by(WorkflowStep.order).all()
    
    return render_template('admin/workflow_form_edit.html', 
                           form=form, 
                           workflow=workflow, 
                           fields=fields,
                           steps=steps,
                           field_types=FormField.get_field_types())

# AJAX：添加表单字段
@workflow_bp.route('/form/<int:form_id>/field/add', methods=['POST'])
@login_required
@admin_required
def add_form_field(form_id):
    form = WorkflowForm.query.get_or_404(form_id)
    workflow = form.workflow
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        return jsonify({'success': False, 'message': '只能编辑草稿状态的工作流'}), 403
    
    data = request.json
    name = data.get('name')
    label = data.get('label')
    field_type = data.get('field_type')
    is_required = data.get('is_required', False)
    placeholder = data.get('placeholder', '')
    default_value = data.get('default_value', '')
    options = data.get('options')
    
    # 获取可见性和可编辑性设置
    visible_steps = data.get('visible_steps', [])
    editable_steps = data.get('editable_steps', [])
    
    # 处理配置
    config = {}
    # 位置字段配置
    if field_type == 'location' and data.get('location_settings'):
        config['use_wechat'] = data.get('location_settings', {}).get('use_wechat', False)
    
    # 确定字段顺序
    max_order = db.session.query(db.func.max(FormField.order)).filter_by(form_id=form_id).scalar() or 0
    
    # 创建字段
    field = FormField(
        form_id=form_id,
        name=name,
        label=label,
        field_type=field_type,
        is_required=is_required,
        order=max_order + 1,
        placeholder=placeholder,
        default_value=default_value,
        visible_steps=json.dumps(visible_steps) if visible_steps else None,
        editable_steps=json.dumps(editable_steps) if editable_steps else None,
        config=json.dumps(config) if config else None
    )
    
    # 处理选项
    if options and (field_type in ['select', 'radio', 'checkbox']):
        field.options = json.dumps(options)
    elif field_type == 'location' and data.get('location_settings'):
        field.options = json.dumps(data.get('location_settings'))
    
    db.session.add(field)
    db.session.commit()
    
    return jsonify({'success': True, 'field_id': field.id})

# AJAX：更新表单字段
@workflow_bp.route('/form/field/<int:field_id>/update', methods=['POST'])
@login_required
@admin_required
def update_form_field(field_id):
    field = FormField.query.get_or_404(field_id)
    workflow = field.form.workflow
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        return jsonify({'success': False, 'message': '只能编辑草稿状态的工作流'}), 403
    
    data = request.json
    field.name = data.get('name')
    field.label = data.get('label')
    field.field_type = data.get('field_type')
    field.is_required = data.get('is_required', False)
    field.placeholder = data.get('placeholder', '')
    field.default_value = data.get('default_value', '')
    
    # 更新可见性和可编辑性设置
    visible_steps = data.get('visible_steps', [])
    editable_steps = data.get('editable_steps', [])
    field.visible_steps = json.dumps(visible_steps) if visible_steps else None
    field.editable_steps = json.dumps(editable_steps) if editable_steps else None
    
    # 更新配置
    config = {}
    # 位置字段配置
    if field.field_type == 'location' and data.get('location_settings'):
        config['use_wechat'] = data.get('location_settings', {}).get('use_wechat', False)
    
    field.config = json.dumps(config) if config else None
    
    # 处理选项
    if data.get('options') and (field.field_type in ['select', 'radio', 'checkbox']):
        field.options = json.dumps(data.get('options'))
    elif field.field_type == 'location' and data.get('location_settings'):
        field.options = json.dumps(data.get('location_settings'))
    
    db.session.commit()
    
    return jsonify({'success': True})

# AJAX：删除表单字段
@workflow_bp.route('/form/field/<int:field_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_form_field(field_id):
    field = FormField.query.get_or_404(field_id)
    form_id = field.form_id
    workflow = field.form.workflow
    
    # 检查是否可以编辑（只能编辑草稿状态的工作流）
    if workflow.status != '草稿':
        return jsonify({'success': False, 'message': '只能编辑草稿状态的工作流'}), 403
    
    db.session.delete(field)
    db.session.commit()
    
    # 重新排序字段
    fields = FormField.query.filter_by(form_id=form_id).order_by(FormField.order).all()
    for i, field in enumerate(fields, 1):
        field.order = i
    
    db.session.commit()
    
    return jsonify({'success': True}) 