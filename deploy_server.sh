#!/bin/bash

# MotuCalliLib 服务器部署脚本
# 支持Ubuntu 18.04+

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    log_error "请不要使用root用户运行此脚本"
    exit 1
fi

log_info "开始部署 MotuCalliLib 应用..."
log_info "当前用户: $(whoami)"
log_info "当前目录: $(pwd)"

# 检查Ubuntu版本
if ! grep -q "Ubuntu" /etc/os-release; then
    log_warning "此脚本专为Ubuntu设计，其他发行版可能需要调整"
fi

# 1. 更新系统包
log_info "更新系统包..."
sudo apt update

# 2. 安装必要的系统依赖
log_info "安装Python和相关工具..."
sudo apt install -y python3-pip python3-venv python3-dev build-essential

# 检查Python版本
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
log_info "Python版本: $PYTHON_VERSION"

# 3. 检查并进入项目目录
if [ ! -d "~/MotuCalliLib" ]; then
    log_error "项目目录 ~/MotuCalliLib 不存在"
    log_info "请先将项目代码上传到服务器"
    exit 1
fi

cd ~/MotuCalliLib
log_info "进入项目目录: $(pwd)"

# 4. 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    log_info "创建Python虚拟环境..."
    python3 -m venv .venv
    log_success "虚拟环境创建完成"
else
    log_info "虚拟环境已存在"
fi

# 5. 激活虚拟环境
log_info "激活虚拟环境..."
source .venv/bin/activate

# 6. 升级pip
log_info "升级pip..."
pip install --upgrade pip

# 7. 安装项目依赖
log_info "安装项目依赖..."
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt 文件不存在"
    exit 1
fi
pip install -r requirements.txt
log_success "项目依赖安装完成"

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
log_info "创建systemd服务..."
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
log_success "systemd服务文件创建完成"

# 13. 启用并启动服务
log_info "启用并启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable motucallilib

# 启动服务并检查状态
if sudo systemctl start motucallilib; then
    log_success "服务启动成功"
else
    log_error "服务启动失败"
    log_info "查看错误日志: sudo journalctl -u motucallilib -n 20"
    exit 1
fi

# 等待服务启动
sleep 3

# 检查服务状态
if sudo systemctl is-active --quiet motucallilib; then
    log_success "服务运行正常"
else
    log_error "服务未正常运行"
    sudo systemctl status motucallilib --no-pager
    exit 1
fi

log_success "🎉 部署完成！"

echo ""
log_info "=== 服务状态 ==="
sudo systemctl status motucallilib --no-pager -l

echo ""
log_info "=== 访问地址 ==="
SERVER_IP=$(hostname -I | awk '{print $1}')
if [ "$install_nginx" = "y" ]; then
    echo "🌐 应用访问地址: http://$SERVER_IP"
    echo "📱 移动端优化: 已启用"
else
    echo "🌐 应用访问地址: http://$SERVER_IP:5000"
    echo "⚠️  建议配置nginx反向代理以获得更好性能"
fi

echo ""
log_info "=== 常用管理命令 ==="
echo "📊 查看服务状态: sudo systemctl status motucallilib"
echo "📋 查看实时日志: sudo journalctl -u motucallilib -f"
echo "🔄 重启服务: sudo systemctl restart motucallilib"
echo "⏹️  停止服务: sudo systemctl stop motucallilib"
echo "🔧 编辑配置: nano ~/MotuCalliLib/.env"

if [ "$install_nginx" = "y" ]; then
    echo "🌐 nginx状态: sudo systemctl status nginx"
    echo "📝 nginx配置: sudo nano /etc/nginx/sites-available/motucallilib"
fi

echo ""
log_info "=== 应用功能 ==="
echo "🏠 首页: 墨研书法主页和搜索"
echo "📚 字库: 汉字搜索和筛选"
echo "✍️  集字: 书法集字功能"
echo "⚙️  设置: 应用配置管理"

echo ""
log_success "部署完成！请访问上述地址开始使用墨研书法应用。"