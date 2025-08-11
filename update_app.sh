#!/bin/bash

# MotuCalliLib 应用更新脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "🔄 开始更新 MotuCalliLib 应用..."

# 进入项目目录
cd ~/MotuCalliLib

# 备份当前配置
log_info "备份当前配置..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 停止服务
log_info "停止应用服务..."
sudo systemctl stop motucallilib

# 更新代码（如果使用git）
if [ -d ".git" ]; then
    log_info "从git拉取最新代码..."
    git stash push -m "Auto stash before update $(date)"
    git pull origin main
    log_success "代码更新完成"
else
    log_warning "未检测到git仓库，请手动上传新代码"
    echo "按Enter键继续，或Ctrl+C取消..."
    read
fi

# 激活虚拟环境
log_info "激活虚拟环境..."
source .venv/bin/activate

# 更新依赖
log_info "更新Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 恢复配置文件
if [ -f ".env.backup.$(date +%Y%m%d)_"* ]; then
    log_info "检查配置文件..."
    if [ ! -f ".env" ]; then
        log_warning "配置文件不存在，恢复备份..."
        cp .env.backup.* .env
    fi
fi

# 创建必要目录
mkdir -p logs image_cache

# 重启服务
log_info "重启应用服务..."
sudo systemctl start motucallilib

# 等待服务启动
sleep 3

# 检查服务状态
if sudo systemctl is-active --quiet motucallilib; then
    log_success "✅ 应用更新成功！"
    echo ""
    echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}')"
    echo "📊 服务状态: sudo systemctl status motucallilib"
    echo "📋 查看日志: sudo journalctl -u motucallilib -f"
else
    echo "❌ 服务启动失败，请检查日志:"
    sudo journalctl -u motucallilib -n 20
    exit 1
fi

echo ""
log_info "更新完成！如有问题，可以查看备份的配置文件："
ls -la .env.backup.*