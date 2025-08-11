# SSH 远程更新指南

## 📋 概述

本指南提供了通过SSH远程更新Ubuntu服务器上MotuCalliLib应用的方法。支持Windows和Linux两种环境。

## 🛠️ 准备工作

### 1. SSH密钥配置（推荐）

为了避免每次输入密码，建议配置SSH密钥：

```bash
# 在本地生成SSH密钥（如果还没有）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 将公钥复制到服务器
ssh-copy-id -p 22 username@server_ip

# 或者手动复制
cat ~/.ssh/id_rsa.pub | ssh username@server_ip "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 2. Windows环境准备

确保已安装SSH客户端：
- Windows 10/11 内置OpenSSH
- Git for Windows
- 或者安装WSL

### 3. 服务器环境确认

确保服务器上已经部署了应用：
- 应用目录：`~/MotuCalliLib`
- 系统服务：`motucallilib.service`
- 虚拟环境：`~/MotuCalliLib/.venv`

## 🚀 使用方法

### Windows PowerShell 版本

#### 首次配置
```powershell
# 配置服务器信息
.\remote_update.ps1 -Action config
```

#### 完整更新
```powershell
# 上传代码并更新应用
.\remote_update.ps1 -Action update

# 或者指定服务器信息
.\remote_update.ps1 -Action update -ServerHost 192.168.1.100 -ServerUser ubuntu
```

#### 其他操作
```powershell
# 查看服务状态
.\remote_update.ps1 -Action status

# 查看实时日志
.\remote_update.ps1 -Action logs

# 重启服务
.\remote_update.ps1 -Action restart

# 显示帮助
.\remote_update.ps1 -Action help
```

### Linux/macOS Bash 版本

#### 首次配置
```bash
# 给脚本执行权限
chmod +x remote_update.sh

# 配置服务器信息
./remote_update.sh --config
```

#### 完整更新
```bash
# 上传代码并更新应用
./remote_update.sh

# 或者使用参数
./remote_update.sh --upload
```

#### 其他操作
```bash
# 查看服务状态
./remote_update.sh --status

# 查看实时日志
./remote_update.sh --logs

# 重启服务
./remote_update.sh --restart

# 显示帮助
./remote_update.sh --help
```

## 📁 文件传输说明

### 包含的文件
- `app_new.py` - 主应用文件
- `requirements.txt` - Python依赖
- `logger.py` - 日志配置
- `static/` - 静态文件目录
- `templates/` - 模板文件目录
- `.env.production` - 生产环境配置

### 排除的文件
- `.git/` - Git仓库文件
- `__pycache__/` - Python缓存
- `*.pyc` - 编译的Python文件
- `.env` - 本地环境配置
- `logs/` - 日志文件
- `image_cache/` - 图片缓存
- `calligraphy.db` - 数据库文件

## 🔧 更新流程

1. **备份配置** - 自动备份服务器上的`.env`文件
2. **停止服务** - 停止`motucallilib`服务
3. **上传代码** - 同步本地代码到服务器
4. **更新依赖** - 安装/更新Python包
5. **恢复配置** - 确保配置文件存在
6. **重启服务** - 启动更新后的应用
7. **状态检查** - 验证服务是否正常运行

## 🔍 故障排除

### 常见问题

1. **SSH连接失败**
   ```bash
   # 测试SSH连接
   ssh -p 22 username@server_ip "echo 'test'"
   
   # 检查SSH配置
   ssh -v username@server_ip
   ```

2. **权限问题**
   ```bash
   # 确保用户有sudo权限
   sudo systemctl status motucallilib
   
   # 检查文件权限
   ls -la ~/MotuCalliLib/
   ```

3. **服务启动失败**
   ```bash
   # 查看详细错误日志
   sudo journalctl -u motucallilib -n 50
   
   # 检查配置文件
   cat ~/MotuCalliLib/.env
   ```

4. **依赖安装失败**
   ```bash
   # 手动激活虚拟环境
   cd ~/MotuCalliLib
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### 手动回滚

如果更新失败，可以手动回滚：

```bash
# 恢复配置文件
cd ~/MotuCalliLib
cp .env.backup.YYYYMMDD_HHMMSS .env

# 重启服务
sudo systemctl restart motucallilib
```

## 📊 监控和维护

### 定期检查
```bash
# 检查服务状态
sudo systemctl status motucallilib

# 检查磁盘空间
df -h ~/MotuCalliLib

# 查看最近日志
sudo journalctl -u motucallilib -n 20
```

### 性能监控
```bash
# 查看系统负载
top
htop

# 查看内存使用
free -h

# 查看网络连接
netstat -tulpn | grep :5000
```

## 🔐 安全建议

1. **使用SSH密钥** - 避免密码认证
2. **限制SSH访问** - 配置防火墙规则
3. **定期更新系统** - 保持服务器安全
4. **备份重要数据** - 定期备份数据库和配置
5. **监控日志** - 关注异常访问和错误

## 📞 支持

如果遇到问题：

1. 检查本文档的故障排除部分
2. 查看服务器日志：`sudo journalctl -u motucallilib -f`
3. 检查应用日志：`tail -f ~/MotuCalliLib/logs/app.log`
4. 验证网络连接和SSH配置

---

**注意**: 在生产环境中进行更新前，建议先在测试环境中验证更改。