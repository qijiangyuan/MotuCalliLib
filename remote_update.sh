#!/bin/bash

# MotuCalliLib 远程更新脚本
# 通过SSH连接到Ubuntu服务器并更新应用

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置变量（请根据你的服务器信息修改）
SERVER_USER="your_username"
SERVER_HOST="your_server_ip"
SERVER_PORT="22"
REMOTE_PROJECT_PATH="~/MotuCalliLib"
LOCAL_PROJECT_PATH="."

# 检查配置
check_config() {
    if [ "$SERVER_USER" = "your_username" ] || [ "$SERVER_HOST" = "your_server_ip" ]; then
        log_error "请先配置服务器信息！"
        echo "编辑此脚本，修改以下变量："
        echo "SERVER_USER=\"你的用户名\""
        echo "SERVER_HOST=\"你的服务器IP\""
        echo "SERVER_PORT=\"SSH端口（默认22）\""
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "MotuCalliLib 远程更新脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -c, --config   配置服务器信息"
    echo "  -u, --upload   上传代码并更新"
    echo "  -s, --status   检查服务器状态"
    echo "  -l, --logs     查看服务器日志"
    echo "  -r, --restart  重启服务"
    echo ""
    echo "示例:"
    echo "  $0 --config   # 配置服务器信息"
    echo "  $0 --upload   # 上传代码并更新应用"
    echo "  $0 --status   # 检查应用状态"
}

# 配置服务器信息
configure_server() {
    echo "请输入服务器信息："
    read -p "服务器IP地址: " input_host
    read -p "用户名: " input_user
    read -p "SSH端口 (默认22): " input_port
    
    input_port=${input_port:-22}
    
    # 更新脚本中的配置
    sed -i "s/SERVER_USER=\"your_username\"/SERVER_USER=\"$input_user\"/" "$0"
    sed -i "s/SERVER_HOST=\"your_server_ip\"/SERVER_HOST=\"$input_host\"/" "$0"
    sed -i "s/SERVER_PORT=\"22\"/SERVER_PORT=\"$input_port\"/" "$0"
    
    log_success "服务器配置已更新"
    log_info "服务器: $input_user@$input_host:$input_port"
}

# 测试SSH连接
test_connection() {
    log_info "测试SSH连接..."
    if ssh -p "$SERVER_PORT" -o ConnectTimeout=10 "$SERVER_USER@$SERVER_HOST" "echo 'SSH连接成功'" 2>/dev/null; then
        log_success "SSH连接正常"
        return 0
    else
        log_error "SSH连接失败"
        log_info "请检查："
        echo "1. 服务器IP地址和端口是否正确"
        echo "2. 用户名是否正确"
        echo "3. SSH密钥是否已配置"
        echo "4. 服务器是否可访问"
        return 1
    fi
}

# 上传代码到服务器
upload_code() {
    log_info "开始上传代码到服务器..."
    
    # 排除不需要上传的文件和目录
    rsync -avz --progress \
        --exclude='.git/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='logs/' \
        --exclude='image_cache/' \
        --exclude='calligraphy.db' \
        -e "ssh -p $SERVER_PORT" \
        "$LOCAL_PROJECT_PATH/" \
        "$SERVER_USER@$SERVER_HOST:$REMOTE_PROJECT_PATH/"
    
    if [ $? -eq 0 ]; then
        log_success "代码上传完成"
    else
        log_error "代码上传失败"
        exit 1
    fi
}

# 远程更新应用
remote_update() {
    log_info "在服务器上更新应用..."
    
    ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" << 'EOF'
        set -e
        
        # 颜色定义
        GREEN='\033[0;32m'
        BLUE='\033[0;34m'
        NC='\033[0m'
        
        log_info() {
            echo -e "${BLUE}[INFO]${NC} $1"
        }
        
        log_success() {
            echo -e "${GREEN}[SUCCESS]${NC} $1"
        }
        
        cd ~/MotuCalliLib
        
        log_info "备份当前配置..."
        if [ -f ".env" ]; then
            cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        fi
        
        log_info "停止应用服务..."
        sudo systemctl stop motucallilib
        
        log_info "激活虚拟环境并更新依赖..."
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        
        log_info "确保配置文件存在..."
        if [ ! -f ".env" ]; then
            if [ -f ".env.production" ]; then
                cp .env.production .env
                log_info "已复制生产环境配置"
            fi
        fi
        
        log_info "创建必要目录..."
        mkdir -p logs image_cache
        
        log_info "重启应用服务..."
        sudo systemctl start motucallilib
        
        # 等待服务启动
        sleep 3
        
        if sudo systemctl is-active --quiet motucallilib; then
            log_success "应用更新成功！"
            echo "服务状态: $(sudo systemctl is-active motucallilib)"
        else
            echo "❌ 服务启动失败，请检查日志:"
            sudo journalctl -u motucallilib -n 10 --no-pager
            exit 1
        fi
EOF
    
    if [ $? -eq 0 ]; then
        log_success "远程更新完成"
    else
        log_error "远程更新失败"
        exit 1
    fi
}

# 检查服务器状态
check_status() {
    log_info "检查服务器应用状态..."
    
    ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" << 'EOF'
        echo "=== 系统信息 ==="
        echo "服务器时间: $(date)"
        echo "系统负载: $(uptime)"
        echo ""
        
        echo "=== 应用服务状态 ==="
        sudo systemctl status motucallilib --no-pager -l
        echo ""
        
        echo "=== Nginx状态 ==="
        if systemctl is-active --quiet nginx; then
            echo "Nginx: 运行中"
        else
            echo "Nginx: 未运行"
        fi
        echo ""
        
        echo "=== 磁盘使用情况 ==="
        df -h ~/MotuCalliLib
        echo ""
        
        echo "=== 最近的应用日志 ==="
        sudo journalctl -u motucallilib -n 5 --no-pager
EOF
}

# 查看服务器日志
view_logs() {
    log_info "查看服务器实时日志..."
    log_warning "按 Ctrl+C 退出日志查看"
    
    ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "sudo journalctl -u motucallilib -f"
}

# 重启服务
restart_service() {
    log_info "重启服务器上的应用..."
    
    ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" << 'EOF'
        echo "重启应用服务..."
        sudo systemctl restart motucallilib
        
        sleep 3
        
        if sudo systemctl is-active --quiet motucallilib; then
            echo "✅ 服务重启成功"
            sudo systemctl status motucallilib --no-pager -l
        else
            echo "❌ 服务重启失败"
            sudo journalctl -u motucallilib -n 10 --no-pager
        fi
EOF
}

# 完整更新流程
full_update() {
    log_info "🚀 开始完整更新流程..."
    
    # 1. 检查配置
    check_config
    
    # 2. 测试连接
    if ! test_connection; then
        exit 1
    fi
    
    # 3. 上传代码
    upload_code
    
    # 4. 远程更新
    remote_update
    
    # 5. 检查状态
    check_status
    
    log_success "🎉 更新完成！"
    
    # 获取服务器IP显示访问地址
    SERVER_IP=$(ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "hostname -I | awk '{print \$1}'" 2>/dev/null || echo "$SERVER_HOST")
    echo ""
    echo "🌐 应用访问地址: http://$SERVER_IP"
    echo "📊 查看状态: $0 --status"
    echo "📋 查看日志: $0 --logs"
}

# 主程序
main() {
    case "${1:-}" in
        -h|--help)
            show_help
            ;;
        -c|--config)
            configure_server
            ;;
        -u|--upload)
            check_config
            test_connection && upload_code && remote_update
            ;;
        -s|--status)
            check_config
            test_connection && check_status
            ;;
        -l|--logs)
            check_config
            test_connection && view_logs
            ;;
        -r|--restart)
            check_config
            test_connection && restart_service
            ;;
        "")
            full_update
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@"