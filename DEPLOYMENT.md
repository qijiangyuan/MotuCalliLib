# 🚀 免费部署指南

本文档介绍如何将书法字库应用部署到免费的云平台。

## 📋 部署前准备

### 1. 代码准备
- ✅ 应用已支持生产环境配置
- ✅ 环境变量配置完整
- ✅ 依赖文件 `requirements.txt` 已更新

### 2. 必需文件
- `app_new.py` - 主应用文件
- `requirements.txt` - Python依赖
- `render.yaml` - Render平台配置
- `data/` - 数据库文件夹
- `static/` - 静态资源
- `templates/` - HTML模板

## 🌟 推荐平台：Render

### 优势
- ✅ **完全免费** - 无需信用卡
- ✅ **自动部署** - 连接GitHub自动更新
- ✅ **HTTPS支持** - 自动SSL证书
- ✅ **零配置** - 使用 `render.yaml` 配置

### 部署步骤

#### 1. 准备GitHub仓库
```bash
# 初始化Git仓库（如果还没有）
git init
git add .
git commit -m "Initial commit"

# 推送到GitHub
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

#### 2. 连接Render
1. 访问 [render.com](https://render.com)
2. 使用GitHub账号注册/登录
3. 点击 "New +" → "Web Service"
4. 选择您的GitHub仓库
5. 配置如下：
   - **Name**: `motu-callilib`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app_new.py`

#### 3. 环境变量设置
在Render控制台设置以下环境变量：
```
FLASK_ENV=production
LOG_LEVEL=info
LOG_TO_FILE=false
PORT=10000
HOST=0.0.0.0
DEBUG=false
```

#### 4. 部署完成
- Render会自动构建和部署
- 获得类似 `https://motu-callilib.onrender.com` 的URL

## 🔄 其他免费平台选项

### Railway
1. 访问 [railway.app](https://railway.app)
2. 连接GitHub仓库
3. 自动检测Python项目
4. 每月$5免费额度

### Fly.io
1. 安装 Fly CLI
2. 运行 `fly launch`
3. 自动生成配置文件
4. 部署命令：`fly deploy`

### PythonAnywhere
1. 注册 [pythonanywhere.com](https://pythonanywhere.com)
2. 上传代码文件
3. 在Web控制台配置WSGI
4. 免费版支持一个应用

## ⚠️ 注意事项

### 数据库文件
- SQLite文件会包含在部署中
- 免费平台可能有存储限制
- 考虑使用云数据库（如果数据重要）

### 图片缓存
- `image_cache/` 目录在重启后可能清空
- 免费平台通常有临时文件系统

### 性能限制
- 免费版通常有CPU/内存限制
- 可能有请求数量限制
- 无访问时可能进入睡眠状态

## 🔧 优化建议

### 1. 添加健康检查
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

### 2. 静态文件优化
- 考虑使用CDN托管静态资源
- 压缩CSS/JS文件

### 3. 数据库优化
- 定期备份SQLite文件
- 考虑迁移到PostgreSQL（免费版）

## 📞 技术支持

如果部署过程中遇到问题：
1. 检查平台的构建日志
2. 确认环境变量设置正确
3. 验证 `requirements.txt` 包含所有依赖
4. 查看应用日志排查错误

## 🎯 部署成功后

部署成功后，您将获得：
- 🌐 公网可访问的URL
- 🔒 HTTPS安全连接
- 📱 移动端友好界面
- 🔄 自动更新部署

现在您的书法字库应用就可以让全世界的用户访问了！