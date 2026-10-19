# MotuCalliLib - 书法字库应用

墨研书法字库与集字字典软件 V1.0 是面向个人临帖学习和集字创作的 Flask 应用。
正式功能包含：字形组合检索、出处与图版详情、收藏、逐字替换、四种排版方向、
作品持久化、PNG 导出、草稿恢复、备份合并恢复、纠错记录和全局阅读偏好。

新版入口仍为 `python app_new.py`，默认访问 `http://127.0.0.1:5000`。
界面所需 CSS / JavaScript 均保存在本地；字图默认为数据库中的远程来源。
新建作品、收藏和纠错保存在 `data/workspace.db`，主字库按只读方式访问。
同一服务实例共享一个个人工作区。本版本未实现账号隔离，不应直接作为多人公网平台。

项目评估、材料定位和变更说明见 `docs/PROJECT_REVIEW.md`。
本次登记材料为 AI 辅助的核验稿，位于 `output/softcopyright/`；请先阅读其中的材料清单，
核验当前登记系统的声明要求并补全真实权属信息，不能直接签署不符合事实的声明。

### 新版运行配置

- `MOTU_DB_PATH`：主字库绝对路径，默认项目内 `data/shufadb.db`。
- `MOTU_WORKSPACE_DB`：个人工作库路径，默认 `data/workspace.db`，首次启动自动创建。
- `USE_LOCAL_IMAGES`：是否优先读取本地图片，默认 `false`。
- `LOCAL_IMAGE_DIR`：本地字图目录，以图片编号命名，例如 `35233.png`。
- `HOST` / `PORT`：默认 `127.0.0.1` / `5000`。`DEBUG` 默认关闭。

运行核心测试：`python tests/test_product.py`；运行原有数据库和日志测试：`python tests/run_tests.py`。
独立浏览器验收脚本：`tools/preview_qa.cjs`，支持 `PLAYWRIGHT_MODULE` 和 `MOTU_PREVIEW_URL` 配置。
浏览器验收需在独立演示工作库运行，以免演示作品或核查记录写入日常工作区。

## 功能特点

- 搜索书法字体
- 生成集字作品
- 导出图片
- 查看所有图片

## 日志系统

应用集成了灵活的日志系统，可以通过环境变量或.env文件配置日志级别和输出方式。

### 日志级别

可以设置以下日志级别（从详细到简略）：

- `debug`: 显示所有日志，包括详细的调试信息
- `info`: 显示信息、警告和错误（默认）
- `warning`: 只显示警告和错误
- `error`: 只显示错误
- `critical`: 只显示严重错误
- `none`: 完全禁用日志

### 配置方法

#### 使用环境变量

```bash
# Windows
set MOTU_LOG_LEVEL=debug
set MOTU_LOG_TO_FILE=true
python app_new.py

# Linux/Mac
export MOTU_LOG_LEVEL=debug
export MOTU_LOG_TO_FILE=true
python app_new.py
```

#### 使用.env文件

创建或编辑项目根目录下的`.env`文件：

```
MOTU_LOG_LEVEL=debug
MOTU_LOG_TO_FILE=true
```

### 日志文件

当启用文件日志（`MOTU_LOG_TO_FILE=true`）时，日志将保存在项目根目录下的`logs/app.log`文件中。日志文件使用滚动机制，每个文件最大10MB，最多保留5个备份文件。

## 数据库结构

应用使用SQLite数据库存储书法字体、作者、书籍和图像信息。数据库文件位于`data/shufadb.db`。

### 主要表结构

- `fonts`: 字体信息
- `authors`: 作者信息
- `books`: 书籍信息
- `glyphs`: 汉字信息，关联字体、作者和书籍
- `images`: 图像信息，关联汉字

详细信息请查看`data/README.md`文件。

## 安装和运行

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 运行应用：`python app_new.py`
4. 在浏览器中访问：`http://localhost:5000`

## 开发者说明

### 使用日志模块

在代码中使用日志：

```python
from logger import get_logger

# 获取默认日志记录器
logger = get_logger()

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 开发工具

项目提供了多个开发和维护工具，位于 `tools/` 目录：

- **数据库检查工具** (`tools/check_db.py`): 检查数据库结构、统计信息和数据完整性
  ```bash
  python tools/check_db.py --stats  # 查看统计信息
  python tools/check_db.py --tables # 查看表结构
  ```

更多工具信息请参考 `tools/README.md`。

### 创建自定义日志记录器

```python
from logger import get_logger

# 创建自定义日志记录器
my_logger = get_logger(
    name="my_module",  # 日志记录器名称
    level="debug",     # 日志级别
    log_to_console=True,  # 是否输出到控制台
    log_to_file=True      # 是否输出到文件
)
```

## 测试

项目包含一套完整的测试，位于 `tests` 目录下。

### 运行测试

运行所有测试：

```bash
python tests/run_tests.py
```

运行单个测试：

```bash
python tests/test_db.py
```

运行日志示例：

```bash
# 设置环境变量（Windows PowerShell）
$env:MOTU_LOG_LEVEL="debug"
$env:MOTU_LOG_TO_FILE="true"
python tests/log_example.py
```

### 测试内容

- 数据库连接和查询测试
- 日志配置和功能测试
- 中文日志记录测试

详细信息请查看 `tests/README.md` 文件。

## 部署

### 群晖服务器部署

本项目提供了专门的群晖发布包，位于 `synology_release/` 目录中。

### 🚀 快速部署

1. 将 `synology_release/` 目录上传到群晖服务器
2. SSH 连接群晖服务器并进入目录
3. 执行部署脚本：
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
4. 访问应用：http://群晖IP:5000

详细的部署指南请参考 `synology_release/README.md` 和 `synology_release/deploy_synology.md`。

## Docker 部署

Docker 相关的配置文件位于 `synology_release/` 目录中，包括：
- `Dockerfile` - Docker 镜像构建文件
- `docker-compose.yml` - 容器编排配置
- `gunicorn.conf.py` - 生产环境配置

如需 Docker 部署，请使用 `synology_release/` 目录中的配置文件。

### 环境变量配置

- `MOTU_LOG_LEVEL`: 日志级别 (debug, info, warning, error)
- `MOTU_LOG_TO_FILE`: 是否输出日志到文件 (true/false)
- `PORT`: 应用端口 (默认: 5000)
- `HOST`: 绑定地址 (默认: 0.0.0.0)
- `DEBUG`: 调试模式 (默认: false)
