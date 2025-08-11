# Ubuntu 服务器部署指南

## 📋 部署前准备

### 1. 服务器要求
- Ubuntu 18.04+ (推荐 20.04 或 22.04)
- 至少 1GB RAM
- 至少 10GB 磁盘空间
- Python 3.8+

### 2. 本地准备
确保你的代码已经提交到git仓库，并且可以通过以下方式获取：
```bash
git clone <你的仓库地址>
# 或者
scp -r /path/to/MotuCalliLib user@server:/home/user/
```

## 🚀 快速部署

### 方法一：使用自动部署脚本（推荐）

1. **上传项目到服务器**
```bash
# 方式1: 使用git克隆
git clone <你的仓库地址> ~/MotuCalliLib
cd ~/MotuCalliLib

# 方式2: 使用scp上传
scp -r ./MotuCalliLib user@your-server:~/
```

2. **运行部署脚本**
```bash
cd ~/MotuCalliLib
chmod +x deploy_server.sh
./deploy_server.sh
```

3. **配置环境变量**
```bash
cp .env.production .env
# 根据需要编辑 .env 文件
nano .env
```

### 方法二：手动部署

#### 步骤1: 更新系统
```bash
sudo apt update && sudo apt upgrade -y
```

#### 步骤2: 安装依赖
```bash
sudo apt install -y python3-pip python3-venv python3-dev build-essential nginx
```

#### 步骤3: 设置项目
```bash
cd ~/MotuCalliLib
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 步骤4: 配置环境
```bash
cp .env.production .env
mkdir -p logs image_cache
```

#### 步骤5: 配置Nginx
```bash
sudo cp nginx_motucallilib.conf /etc/nginx/sites-available/motucallilib
sudo ln -sf /etc/nginx/sites-available/motucallilib /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable nginx
```

#### 步骤6: 配置系统服务
```bash
sudo tee /etc/systemd/system/motucallilib.service << EOF
[Unit]
Description=MotuCalliLib Flask Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/MotuCalliLib
Environment=PATH=$HOME/MotuCalliLib/.venv/bin
ExecStart=$HOME/MotuCalliLib/.venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 app_new:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable motucallilib
sudo systemctl start motucallilib
```

## 🔧 服务管理

### 常用命令
```bash
# 查看服务状态
sudo systemctl status motucallilib

# 重启服务
sudo systemctl restart motucallilib

# 停止服务
sudo systemctl stop motucallilib

# 查看日志
sudo journalctl -u motucallilib -f

# 查看nginx状态
sudo systemctl status nginx

# 重启nginx
sudo systemctl restart nginx
```

### 日志位置
- 应用日志: `~/MotuCalliLib/logs/`
- 系统服务日志: `sudo journalctl -u motucallilib`
- Nginx日志: `/var/log/nginx/`

## 🌐 访问应用

部署完成后，你可以通过以下地址访问应用：
- **HTTP**: `http://你的服务器IP地址`
- **如果没有配置nginx**: `http://你的服务器IP地址:5000`

## 🔒 安全配置（可选）

### 1. 配置防火墙
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 2. 配置SSL证书（使用Let's Encrypt）
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名.com
```

### 3. 配置自动更新SSL证书
```bash
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔄 更新应用

### 方法1: Git更新
```bash
cd ~/MotuCalliLib
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart motucallilib
```

### 方法2: 手动更新
```bash
# 上传新文件后
cd ~/MotuCalliLib
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart motucallilib
```

## 🐛 故障排除

### 常见问题

1. **服务无法启动**
```bash
sudo journalctl -u motucallilib -n 50
```

2. **端口被占用**
```bash
sudo lsof -i :5000
sudo kill -9 <PID>
```

3. **权限问题**
```bash
sudo chown -R $USER:$USER ~/MotuCalliLib
chmod +x ~/MotuCalliLib/app_new.py
```

4. **数据库问题**
```bash
cd ~/MotuCalliLib
source .venv/bin/activate
python3 -c "import sqlite3; print('SQLite可用')"
```

### 性能优化

1. **增加Gunicorn工作进程**
编辑 `/etc/systemd/system/motucallilib.service`，修改：
```
ExecStart=$HOME/MotuCalliLib/.venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 app_new:app
```

2. **配置Nginx缓存**
在nginx配置中添加：
```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 📞 支持

如果遇到问题，请检查：
1. 系统日志: `sudo journalctl -u motucallilib`
2. Nginx日志: `sudo tail -f /var/log/nginx/error.log`
3. 应用日志: `tail -f ~/MotuCalliLib/logs/app.log`