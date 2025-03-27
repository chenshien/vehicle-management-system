from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.workflow import Workflow, WorkflowPermission, WorkflowStep
from models.application import Application, ApplicationStatus
from datetime import datetime
from sqlalchemy.orm import joinedload

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # 获取用户可发起的工作流
    available_workflows = []
    
    # 获取所有已发布的工作流
    published_workflows = Workflow.query.filter_by(status='已发布').all()
    
    for workflow in published_workflows:
        # 检查有效期
        now = datetime.now()
        if workflow.start_date and workflow.start_date > now:
            continue
        if workflow.end_date and workflow.end_date < now:
            continue
        
        # 检查权限
        user_permissions = WorkflowPermission.query.filter_by(
            workflow_id=workflow.id,
            permission_type='user',
            target_id=current_user.id
        ).first()
        
        # 检查角色权限
        role_ids = [role.id for role in current_user.roles]
        role_permissions = WorkflowPermission.query.filter(
            WorkflowPermission.workflow_id == workflow.id,
            WorkflowPermission.permission_type == 'role',
            WorkflowPermission.target_id.in_(role_ids)
        ).first()
        
        # 检查是否有任何权限配置
        has_any_permissions = WorkflowPermission.query.filter_by(workflow_id=workflow.id).first()
        
        # 如果没有任何权限配置或者用户有权限，则添加到可用工作流列表
        if not has_any_permissions or user_permissions or role_permissions:
            available_workflows.append(workflow)
    
    # 获取用户的申请
    my_applications = Application.query.filter_by(user_id=current_user.id).order_by(Application.updated_at.desc()).limit(5).all()
    
    # 获取待我处理的申请
    role_ids = [role.id for role in current_user.roles]
    pending_applications = []
    
    if role_ids:
        # 首先获取"处理中"状态的ID
        processing_status = ApplicationStatus.query.filter_by(name='待审核').first()
        if processing_status:
            # 使用JOIN查询找到当前用户角色可以处理的申请
            # 通过步骤表中的role_id字段进行关联
            pending_applications = Application.query\
                .join(WorkflowStep, Application.current_step == WorkflowStep.order)\
                .filter(WorkflowStep.workflow_id == Application.workflow_id)\
                .filter(WorkflowStep.role_id.in_(role_ids))\
                .filter(Application.status_id == processing_status.id)\
                .order_by(Application.updated_at.desc())\
                .limit(5)\
                .all()
    
    return render_template('user/dashboard.html', 
                           available_workflows=available_workflows, 
                           my_applications=my_applications, 
                           pending_applications=pending_applications)

@user_bp.route('/applications')
@login_required
def my_applications():
    # 获取用户的所有申请
    applications = Application.query.filter_by(user_id=current_user.id).order_by(Application.updated_at.desc()).all()
    return render_template('user/applications.html', applications=applications)

@user_bp.route('/pending-applications')
@login_required
def pending_applications():
    # 获取待当前用户处理的申请
    role_ids = [role.id for role in current_user.roles]
    applications = []
    
    if role_ids:
        # 首先获取"处理中"状态的ID
        processing_status = ApplicationStatus.query.filter_by(name='待审核').first()
        if processing_status:
            # 使用JOIN查询找到当前用户角色可以处理的申请
            # 通过步骤表中的role_id字段进行关联
            applications = Application.query\
                .join(WorkflowStep, Application.current_step == WorkflowStep.order)\
                .filter(WorkflowStep.workflow_id == Application.workflow_id)\
                .filter(WorkflowStep.role_id.in_(role_ids))\
                .filter(Application.status_id == processing_status.id)\
                .order_by(Application.updated_at.desc())\
                .all()
    
    return render_template('user/pending_applications.html', applications=applications)

@user_bp.route('/start-process/<int:workflow_id>')
@login_required
def start_process(workflow_id):
    # 获取指定的工作流
    workflow = Workflow.query.filter_by(id=workflow_id, status='已发布').first_or_404()
    
    # 检查有效期
    now = datetime.now()
    if workflow.start_date and workflow.start_date > now:
        flash('该工作流尚未开始生效', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if workflow.end_date and workflow.end_date < now:
        flash('该工作流已过期', 'danger')
        return redirect(url_for('user.dashboard'))
    
    # 检查权限
    user_permission = WorkflowPermission.query.filter_by(
        workflow_id=workflow_id,
        permission_type='user',
        target_id=current_user.id
    ).first()
    
    # 检查角色权限
    role_ids = [role.id for role in current_user.roles]
    role_permission = WorkflowPermission.query.filter(
        WorkflowPermission.workflow_id == workflow_id,
        WorkflowPermission.permission_type == 'role',
        WorkflowPermission.target_id.in_(role_ids)
    ).first()
    
    # 检查是否有任何权限配置
    has_any_permissions = WorkflowPermission.query.filter_by(workflow_id=workflow_id).first()
    
    # 如果有权限配置但当前用户没有权限，则拒绝访问
    if has_any_permissions and not (user_permission or role_permission):
        flash('您没有权限发起此工作流', 'danger')
        return redirect(url_for('user.dashboard'))
    
    # 重定向到申请创建页面
    return redirect(url_for('application.create_application', workflow_id=workflow_id)) 