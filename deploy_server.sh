#!/bin/bash

# MotuCalliLib 服务器部署脚本
echo "开始部署 MotuCalliLib 应用..."

# 1. 更新系统包
echo "更新系统包..."
sudo apt update

# 2. 安装必要的系统依赖
echo "安装Python和相关工具..."
sudo apt install -y python3-pip python3-venv python3-dev build-essential

# 3. 进入项目目录
cd ~/MotuCalliLib

# 4. 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv .venv
fi

# 5. 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 6. 升级pip
echo "升级pip..."
pip install --upgrade pip

# 7. 安装项目依赖
echo "安装项目依赖..."
pip install -r requirements.txt

# 8. 检查环境配置文件
if [ ! -f ".env" ]; then
    echo "复制环境配置文件..."
    cp .env.example .env
    echo "请编辑 .env 文件以配置数据库连接"
fi

# 9. 创建必要的目录
mkdir -p logs
mkdir -p image_cache

# 10. 设置文件权限
chmod +x app_new.py

# 11. 安装并配置nginx（可选）
echo "是否安装nginx作为反向代理？(y/n)"
read -r install_nginx
if [ "$install_nginx" = "y" ]; then
    sudo apt install -y nginx
    
    # 创建nginx配置
    sudo tee /etc/nginx/sites-available/motucallilib << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $(pwd)/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # 启用站点
    sudo ln -sf /etc/nginx/sites-available/motucallilib /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    sudo systemctl enable nginx
fi

# 12. 创建systemd服务文件
echo "创建systemd服务..."
sudo tee /etc/systemd/system/motucallilib.service << EOF
[Unit]
Description=MotuCalliLib Flask Application
After=network.target

[Service]
Type=simple
User=archy
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin
ExecStart=$(pwd)/.venv/bin/python app_new.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 13. 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable motucallilib
sudo systemctl start motucallilib

echo "部署完成！"
echo "服务状态："
sudo systemctl status motucallilib --no-pager

echo ""
echo "有用的命令："
echo "查看服务状态: sudo systemctl status motucallilib"
echo "查看日志: sudo journalctl -u motucallilib -f"
echo "重启服务: sudo systemctl restart motucallilib"
echo "停止服务: sudo systemctl stop motucallilib"

if [ "$install_nginx" = "y" ]; then
    echo "nginx状态: sudo systemctl status nginx"
    echo "应用访问地址: http://$(hostname -I | awk '{print $1}')"
else
    echo "应用访问地址: http://$(hostname -I | awk '{print $1}'):5000"
fi