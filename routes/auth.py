from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from models.user import User
from werkzeug.urls import url_parse
from forms.auth import LoginForm, RegisterForm

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码错误', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('user.dashboard')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            name=form.name.data,
            department=form.department.data,
            position=form.position.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        
        # 添加默认角色 - 部门员工
        from models.user import Role
        role = Role.query.filter_by(name='部门员工').first()
        if role:
            user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    # 获取表单数据
    email = request.form.get('email')
    name = request.form.get('name')
    department = request.form.get('department')
    position = request.form.get('position')
    phone = request.form.get('phone')
    
    # 验证邮箱唯一性（排除当前用户）
    if email != current_user.email:
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash(f'邮箱 {email} 已被其他用户使用', 'danger')
            return redirect(url_for('auth.profile'))
    
    # 更新用户信息
    current_user.email = email
    current_user.name = name
    current_user.department = department
    current_user.position = position
    current_user.phone = phone
    
    # 保存到数据库
    db.session.commit()
    
    flash('个人资料更新成功', 'success')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    # 获取表单数据
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 验证当前密码
    if not current_user.check_password(current_password):
        flash('当前密码不正确', 'danger')
        return redirect(url_for('auth.profile'))
    
    # 验证新密码与确认密码是否一致
    if new_password != confirm_password:
        flash('新密码与确认密码不一致', 'danger')
        return redirect(url_for('auth.profile'))
    
    # 更新密码
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('密码修改成功', 'success')
    return redirect(url_for('auth.profile'))

# 微信小程序端的认证API
@auth_bp.route('/wechat/login', methods=['POST'])
def wechat_login():
    # 处理微信小程序的登录逻辑
    pass 