# MotuCalliLib 远程更新工具

这是一个简单的Windows PowerShell脚本，用于远程更新Ubuntu服务器上的MotuCalliLib应用。

## 服务器信息

- **服务器IP**: 192.168.100.227
- **用户名**: archy
- **SSH端口**: 22
- **远程路径**: ~/MotuCalliLib

## 使用方法

### 1. 查看帮助
```powershell
.\remote_update.ps1 -Action help
```

### 2. 完整更新（推荐）
```powershell
.\remote_update.ps1 -Action update
```
这个命令会：
- 上传本地文件到服务器
- 停止服务
- 安装依赖
- 重启服务
- 显示服务状态

### 3. 查看服务状态
```powershell
.\remote_update.ps1 -Action status
```

### 4. 查看实时日志
```powershell
.\remote_update.ps1 -Action logs
```
按 Ctrl+C 退出日志查看

## 上传的文件

脚本会自动上传以下文件和目录：
- `app_new.py` - 主应用文件
- `requirements.txt` - Python依赖
- `logger.py` - 日志模块
- `static/` - 静态文件目录
- `templates/` - 模板文件目录

## 前提条件

1. **SSH客户端**: 确保Windows系统已安装SSH客户端（Windows 10/11默认包含）
2. **SSH密钥**: 建议配置SSH密钥认证，避免每次输入密码
3. **网络连接**: 确保能够访问服务器IP地址

## SSH密钥配置（可选但推荐）

1. 生成SSH密钥：
```powershell
ssh-keygen -t rsa -b 4096
```

2. 复制公钥到服务器：
```powershell
scp ~/.ssh/id_rsa.pub archy@192.168.100.227:~/.ssh/authorized_keys
```

配置完成后，脚本运行时就不需要输入密码了。

## 故障排除

- 如果连接失败，请检查服务器IP和网络连接
- 如果权限错误，请确保用户有sudo权限
- 如果服务启动失败，请检查应用日志

## 注意事项

- 脚本会自动停止和启动服务，可能会短暂中断服务
- 建议在维护时间窗口内执行更新
- 更新完成后会显示服务访问地址