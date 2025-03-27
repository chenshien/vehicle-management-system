from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(role_name):
    """
    检查用户是否具有指定角色的装饰器
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            if not current_user.has_role(role_name):
                flash(f'您需要 {role_name} 角色权限才能访问', 'danger')
                return redirect(url_for('user.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    检查用户是否是管理员的装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.has_role('管理员'):
            flash('此页面仅管理员可访问', 'danger')
            return redirect(url_for('user.dashboard'))
        return f(*args, **kwargs)
    return decorated_function 