# 车辆管理系统

一个完整的车辆管理系统，具有用户管理、工作流设计、表单设计和权限控制功能。

## 功能特性

1. **用户和角色管理**
   - 多角色支持，灵活的权限配置
   - 细粒度的功能权限控制

2. **工作流管理**
   - 可视化的工作流设计
   - 工作流版本控制
   - 工作流生效时间设置
   - 发起权限控制

3. **表单设计**
   - 自定义表单字段
   - 丰富的字段类型，包括文本、数字、下拉选择、日期、位置等
   - 字段级别的可见性和编辑权限控制

4. **位置服务**
   - 集成高德地图API
   - 支持地址搜索
   - 支持获取当前位置

5. **完整的应用审批流程**
   - 申请创建、提交、审批
   - 流程跟踪和历史记录

6. **API支持**
   - 完整的RESTful API
   - 支持微信小程序集成

## 安装说明

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

系统支持SQLite和MySQL两种数据库：

#### 使用SQLite（默认）

无需额外配置，系统会在`data`文件夹中创建`app.db`文件。

#### 使用MySQL

1. 创建MySQL数据库：

```sql
CREATE DATABASE vehicle_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 设置环境变量：

```bash
# Windows
set DB_TYPE=mysql
set MYSQL_HOST=localhost
set MYSQL_PORT=3306
set MYSQL_USER=root
set MYSQL_PASSWORD=your_password
set MYSQL_DB=vehicle_management

# Linux/Mac
export DB_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DB=vehicle_management
```

或者在`config.py`中直接修改配置。

### 3. 初始化数据库

```bash
python create_db.py
```

### 4. 初始化默认用户和角色

```bash
python init_db.py
```

### 5. 启动应用

```bash
# Windows
run.bat

# Linux/Mac
sh run.sh

# 或者直接运行
python app.py
```

## 默认账户

- 管理员账户: admin / admin123
- 普通用户: user / user123

## 配置位置服务

如果需要使用位置服务功能，需要获取高德地图API的Key，并在`static/js/location-picker.js`文件中替换。

## 开发指南

### 项目结构

```
├── app.py                 # 应用入口
├── config.py              # 配置文件
├── create_db.py           # 数据库创建脚本
├── init_db.py             # 初始化数据脚本
├── requirements.txt       # 依赖列表
├── extensions.py          # 扩展初始化
├── models/                # 数据模型
├── routes/                # 路由控制器
├── static/                # 静态资源
│   ├── css/               # CSS样式
│   ├── js/                # JavaScript脚本
│   └── uploads/           # 上传文件存储
├── templates/             # 模板文件
│   ├── admin/             # 管理界面模板
│   ├── components/        # 组件模板
│   └── user/              # 用户界面模板
└── utils/                 # 工具函数
```

### 数据库迁移

当模型发生变化时，可以使用以下方法迁移数据库：

```bash
python migrations.py
```

### 添加新的字段类型

如需添加新的表单字段类型，请参考以下步骤：

1. 在`models/workflow.py`中的`FormField`类中添加新的字段类型
2. 在`static/js/`中创建相应的JavaScript处理代码
3. 在`templates/components/`中创建字段渲染模板
4. 在`templates/components/form_renderer.html`中添加字段渲染逻辑

## 许可证

[MIT License](LICENSE) 