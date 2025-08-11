# SSH密钥配置指南

为了让远程更新脚本能够无密码运行，建议配置SSH密钥认证。

## 1. 生成SSH密钥对

在Windows PowerShell中运行：

```powershell
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

- 按回车使用默认文件位置 (`~/.ssh/id_rsa`)
- 可以设置密码短语，也可以留空（留空更方便自动化）

## 2. 复制公钥到服务器

### 方法1：使用ssh-copy-id（推荐）
```powershell
ssh-copy-id archy@192.168.100.227
```

### 方法2：手动复制
```powershell
# 查看公钥内容
Get-Content ~/.ssh/id_rsa.pub

# 然后SSH到服务器，将公钥内容添加到 ~/.ssh/authorized_keys
ssh archy@192.168.100.227
mkdir -p ~/.ssh
echo "你的公钥内容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## 3. 测试无密码登录

```powershell
ssh archy@192.168.100.227
```

如果配置成功，应该可以直接登录而不需要输入密码。

## 4. 配置sudo无密码（可选）

如果你想让sudo命令也不需要密码，可以在服务器上配置：

```bash
# 在服务器上运行
sudo visudo

# 添加以下行（将archy替换为你的用户名）
archy ALL=(ALL) NOPASSWD: ALL
```

**注意：这会降低安全性，仅在测试环境中使用。**

## 5. 验证配置

配置完成后，运行更新脚本应该不再需要输入密码：

```powershell
.\remote_update.ps1 -Action update
```

## 故障排除

- 如果仍然要求密码，检查服务器上的 `~/.ssh/authorized_keys` 文件权限
- 确保SSH服务允许密钥认证（`PubkeyAuthentication yes`）
- 检查防火墙设置是否阻止SSH连接