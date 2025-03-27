from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.workflow import Workflow, WorkflowStep, WorkflowForm
from models.application import Application, ApplicationForm, ApplicationStatus, ApplicationLog
from utils.decorators import role_required
import json
from datetime import datetime

application_bp = Blueprint('application', __name__)

# 我的申请列表
@application_bp.route('/applications')
@login_required
def my_applications():
    applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('application/list.html', applications=applications)

# 创建申请
@application_bp.route('/application/create/<int:workflow_id>', methods=['GET', 'POST'])
@login_required
def create_application(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('申请标题不能为空', 'danger')
            return redirect(url_for('application.create_application', workflow_id=workflow_id))
        
        # 获取工作流的第一个状态
        first_step = WorkflowStep.query.filter_by(workflow_id=workflow_id).order_by(WorkflowStep.order).first()
        if not first_step:
            flash('工作流未配置步骤', 'danger')
            return redirect(url_for('application.my_applications'))
        
        # 创建申请记录
        status = ApplicationStatus(name='草稿', description='正在填写申请表')
        db.session.add(status)
        db.session.flush()  # 获取生成的ID
        
        application = Application(
            workflow_id=workflow_id,
            user_id=current_user.id,
            title=title,
            status_id=status.id,
            current_step_id=first_step.id
        )
        
        db.session.add(application)
        db.session.commit()
        
        # 创建日志
        log = ApplicationLog(
            application_id=application.id,
            user_id=current_user.id,
            action='创建',
            description='创建了申请',
            created_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        
        flash('申请创建成功，请填写表单', 'success')
        return redirect(url_for('application.edit_application', application_id=application.id))
    
    return render_template('application/create.html', workflow=workflow)

# 编辑申请
@application_bp.route('/application/<int:application_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_application(application_id):
    application = Application.query.get_or_404(application_id)
    
    # 检查权限
    if application.user_id != current_user.id:
        flash('无权编辑此申请', 'danger')
        return redirect(url_for('application.my_applications'))
    
    # 检查申请状态
    if application.status.name != '草稿':
        flash('此申请已提交，无法编辑', 'danger')
        return redirect(url_for('application.view_application', application_id=application_id))
    
    workflow = application.workflow
    current_step = application.current_step
    
    if request.method == 'POST':
        # 保存表单数据
        form_data = {}
        for key, value in request.form.items():
            if key not in ['csrf_token', 'title', 'submit']:
                form_data[key] = value
        
        # 处理文件上传
        for key, file in request.files.items():
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                form_data[key] = filename
        
        # 检查当前步骤是否有表单
        if current_step and current_step.form:
            # 获取或创建表单记录
            application_form = ApplicationForm.query.filter_by(
                application_id=application.id,
                form_id=current_step.form.id
            ).first()
            
            if not application_form:
                application_form = ApplicationForm(
                    application_id=application.id,
                    form_id=current_step.form.id,
                    data=json.dumps(form_data)
                )
                db.session.add(application_form)
            else:
                application_form.data = json.dumps(form_data)
            
            db.session.commit()
            
            flash('表单已保存', 'success')
            
            if 'submit' in request.form:
                # 提交申请
                return redirect(url_for('application.submit_application', application_id=application.id))
        
        return redirect(url_for('application.edit_application', application_id=application.id))
    
    # 获取表单数据
    form_data = {}
    if current_step and current_step.form:
        application_form = ApplicationForm.query.filter_by(
            application_id=application.id,
            form_id=current_step.form.id
        ).first()
        
        if application_form and application_form.data:
            form_data = json.loads(application_form.data)
    
    return render_template('application/edit.html', 
                           application=application, 
                           workflow=workflow, 
                           current_step=current_step,
                           form_data=form_data)

# 查看申请
@application_bp.route('/application/<int:application_id>')
@login_required
def view_application(application_id):
    application = Application.query.get_or_404(application_id)
    
    # 检查权限
    if application.user_id != current_user.id and not current_user.has_role('管理员'):
        # 检查当前用户是否是当前步骤的处理人
        if not application.current_step or not application.current_step.role or not current_user.has_role(application.current_step.role.name):
            flash('无权查看此申请', 'danger')
            return redirect(url_for('application.my_applications'))
    
    # 获取所有表单数据
    forms_data = {}
    for app_form in application.forms:
        if app_form.data:
            forms_data[app_form.form_id] = json.loads(app_form.data)
    
    # 获取审批日志
    logs = ApplicationLog.query.filter_by(application_id=application_id).order_by(ApplicationLog.created_at).all()
    
    return render_template('application/view.html', 
                           application=application, 
                           forms_data=forms_data,
                           logs=logs)

# 处理申请（审批）
@application_bp.route('/application/<int:application_id>/process', methods=['GET', 'POST'])
@login_required
def process_application(application_id):
    application = Application.query.get_or_404(application_id)
    
    # 检查权限
    if not application.current_step or not application.current_step.role or not current_user.has_role(application.current_step.role.name):
        flash('无权处理此申请', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        comment = request.form.get('comment', '')
        
        # 保存表单数据（如果当前步骤有表单）
        if application.current_step.form:
            form_data = {}
            for key, value in request.form.items():
                if key not in ['csrf_token', 'action', 'comment']:
                    form_data[key] = value
            
            # 处理文件上传
            for key, file in request.files.items():
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    form_data[key] = filename
            
            # 获取或创建表单记录
            application_form = ApplicationForm.query.filter_by(
                application_id=application.id,
                form_id=application.current_step.form.id
            ).first()
            
            if not application_form:
                application_form = ApplicationForm(
                    application_id=application.id,
                    form_id=application.current_step.form.id,
                    data=json.dumps(form_data)
                )
                db.session.add(application_form)
            else:
                application_form.data = json.dumps(form_data)
            
            db.session.commit()
        
        # 处理审批
        if action == 'approve':
            # 找下一个步骤
            next_steps = WorkflowStep.query.filter(
                WorkflowStep.workflow_id == application.workflow_id,
                WorkflowStep.order > application.current_step.order
            ).order_by(WorkflowStep.order).all()
            
            if next_steps:
                # 进入下一步
                next_step = next_steps[0]
                application.current_step_id = next_step.id
                
                # 更新状态
                status = ApplicationStatus(name='处理中', description=f'等待{next_step.role.name if next_step.role else "系统"}处理')
                db.session.add(status)
                db.session.flush()
                application.status_id = status.id
                
                # 记录日志
                log = ApplicationLog(
                    application_id=application.id,
                    user_id=current_user.id,
                    action='通过',
                    description=f'同意申请，进入下一步：{next_step.name}' + (f'，备注：{comment}' if comment else ''),
                    created_at=datetime.now()
                )
                db.session.add(log)
            else:
                # 没有下一步，流程结束
                status = ApplicationStatus(name='已完成', description='申请已通过')
                db.session.add(status)
                db.session.flush()
                application.status_id = status.id
                application.completed_at = datetime.now()
                
                # 记录日志
                log = ApplicationLog(
                    application_id=application.id,
                    user_id=current_user.id,
                    action='通过',
                    description='同意申请，流程已完成' + (f'，备注：{comment}' if comment else ''),
                    created_at=datetime.now()
                )
                db.session.add(log)
        
        elif action == 'reject':
            # 拒绝申请
            status = ApplicationStatus(name='已拒绝', description='申请未通过')
            db.session.add(status)
            db.session.flush()
            application.status_id = status.id
            application.completed_at = datetime.now()
            
            # 记录日志
            log = ApplicationLog(
                application_id=application.id,
                user_id=current_user.id,
                action='拒绝',
                description='拒绝申请' + (f'，原因：{comment}' if comment else ''),
                created_at=datetime.now()
            )
            db.session.add(log)
        
        elif action == 'return':
            # 退回申请（找到开始步骤）
            first_step = WorkflowStep.query.filter_by(workflow_id=application.workflow_id).order_by(WorkflowStep.order).first()
            if first_step:
                application.current_step_id = first_step.id
                
                # 更新状态
                status = ApplicationStatus(name='已退回', description='需要修改重新提交')
                db.session.add(status)
                db.session.flush()
                application.status_id = status.id
                
                # 记录日志
                log = ApplicationLog(
                    application_id=application.id,
                    user_id=current_user.id,
                    action='退回',
                    description='申请被退回修改' + (f'，原因：{comment}' if comment else ''),
                    created_at=datetime.now()
                )
                db.session.add(log)
        
        db.session.commit()
        flash('处理成功', 'success')
        return redirect(url_for('application.view_application', application_id=application.id))
    
    # 获取表单数据
    form_data = {}
    if application.current_step and application.current_step.form:
        application_form = ApplicationForm.query.filter_by(
            application_id=application.id,
            form_id=application.current_step.form.id
        ).first()
        
        if application_form and application_form.data:
            form_data = json.loads(application_form.data)
    
    return render_template('application/process.html', 
                           application=application, 
                           form_data=form_data,
                           current_step_id=application.current_step_id)

# 提交申请（从草稿到正式流程）
@application_bp.route('/application/<int:application_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_application(application_id):
    application = Application.query.get_or_404(application_id)
    
    # 检查权限
    if application.user_id != current_user.id:
        flash('无权提交此申请', 'danger')
        return redirect(url_for('application.my_applications'))
    
    # 检查状态
    if application.status.name != '草稿':
        flash('此申请已提交，无法再次提交', 'danger')
        return redirect(url_for('application.view_application', application_id=application_id))
    
    if request.method == 'POST':
        # 更新状态为已提交
        status = ApplicationStatus(name='已提交', description='等待审核')
        db.session.add(status)
        db.session.flush()
        application.status_id = status.id
        application.submitted_at = datetime.now()
        
        # 记录日志
        log = ApplicationLog(
            application_id=application.id,
            user_id=current_user.id,
            action='提交',
            description='提交了申请，等待审核',
            created_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        
        flash('申请已成功提交', 'success')
        return redirect(url_for('application.view_application', application_id=application_id))
    
    # 检查是否已填写所有必要表单
    missing_forms = []
    if application.current_step and application.current_step.form:
        application_form = ApplicationForm.query.filter_by(
            application_id=application.id,
            form_id=application.current_step.form.id
        ).first()
        
        if not application_form:
            missing_forms.append(application.current_step.form.name)
    
    if missing_forms:
        flash(f'请先填写以下表单: {", ".join(missing_forms)}', 'danger')
        return redirect(url_for('application.edit_application', application_id=application_id))
    
    return render_template('application/submit.html', application=application) 