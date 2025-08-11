#!/bin/bash

# MotuCalliLib 快速部署脚本
# 适合有经验的用户，最小化交互

set -e

echo "🚀 MotuCalliLib 快速部署开始..."

# 更新系统并安装依赖
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev build-essential nginx

# 进入项目目录
cd ~/MotuCalliLib

# 设置Python环境
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境
cp .env.production .env
mkdir -p logs image_cache

# 配置nginx
sudo cp nginx_motucallilib.conf /etc/nginx/sites-available/motucallilib
sudo ln -sf /etc/nginx/sites-available/motucallilib /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable nginx

# 配置systemd服务
sudo tee /etc/systemd/system/motucallilib.service << EOF
[Unit]
Description=MotuCalliLib Flask Application
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin
ExecStart=$(pwd)/.venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 app_new:app
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable motucallilib
sudo systemctl start motucallilib

# 检查状态
sleep 3
if sudo systemctl is-active --quiet motucallilib; then
    echo "✅ 部署成功！"
    echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}')"
    echo "📊 服务状态: sudo systemctl status motucallilib"
else
    echo "❌ 部署失败，请检查日志: sudo journalctl -u motucallilib -n 20"
    exit 1
fi