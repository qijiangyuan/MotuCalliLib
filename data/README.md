# 数据目录

此目录包含项目的所有数据文件，主要是数据库和SQL查询文件。

## 目录结构

- `shufadb.db` - 主数据库文件，包含书法字体、作者、书籍和图像信息
- `sql/` - SQL查询文件目录
  - `check_images_count.sql` - 检查图像数量的SQL查询
  - `check_table_structure.sql` - 检查表结构的SQL查询
  - `fix_split2.sql` - 修复数据的SQL查询
  - `view_image_details.sql` - 查看图像详情的SQL查询

## 数据库结构

数据库包含以下表：

1. `fonts` - 字体信息
2. `authors` - 作者信息
3. `books` - 书籍信息
4. `glyphs` - 汉字信息，关联字体、作者和书籍
5. `images` - 图像信息，关联汉字

## 使用说明

在应用程序中，通过以下方式访问数据库：

```python
import os

DB_PATH = os.path.join("data", "shufadb.db")
```

可以使用`tools/check_db.py`脚本查看数据库的结构和示例数据：

```bash
# 查看所有信息
python tools/check_db.py

# 只查看统计信息
python tools/check_db.py --stats

# 只查看表结构
python tools/check_db.py --tables
```