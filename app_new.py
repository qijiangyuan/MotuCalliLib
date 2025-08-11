from flask import Flask, request, jsonify, send_file, render_template
import sqlite3
import os
from PIL import Image
import io
import requests
from dotenv import load_dotenv
from logger import get_logger, configure_from_env
import time
from collections import OrderedDict
import concurrent.futures
import threading
from functools import lru_cache

# 加载环境变量
load_dotenv()

# 配置日志
logger = configure_from_env()
# 使用默认日志级别

app = Flask(__name__)
# 禁用模板缓存，确保开发时能加载最新模板
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
DB_PATH = os.path.join("data", "shufadb.db")

# 图片缓存类
class ImageCache:
    def __init__(self, max_size=1000, expire_time=3600):  # 缓存1000个条目，1小时过期
        self.cache = OrderedDict()
        self.max_size = max_size
        self.expire_time = expire_time
    
    def _is_expired(self, timestamp):
        return time.time() - timestamp > self.expire_time
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if not self._is_expired(timestamp):
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                return data
            else:
                # 过期，删除
                del self.cache[key]
        return None
    
    def set(self, key, value):
        # 如果已存在，更新并移动到末尾
        if key in self.cache:
            self.cache[key] = (value, time.time())
            self.cache.move_to_end(key)
        else:
            # 新增条目
            self.cache[key] = (value, time.time())
            # 如果超过最大大小，删除最旧的条目
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()
    
    def size(self):
        return len(self.cache)

# 创建全局图片缓存实例
image_cache = ImageCache()

# 图片内容缓存（内存缓存，用于缓存已下载的图片内容）
_image_content_cache = {}
_image_content_cache_lock = threading.Lock()

def download_and_process_image(img_id, url, target_size=(120, 120)):
    """下载并处理单张图片，支持缓存"""
    try:
        # 检查内存缓存
        cache_key = f"img_content_{img_id}"
        with _image_content_cache_lock:
            if cache_key in _image_content_cache:
                logger.debug(f"从内存缓存获取图片内容: {img_id}")
                cached_img = _image_content_cache[cache_key]
                return cached_img.copy()  # 返回副本避免修改原图
        
        # 下载图片
        logger.debug(f"下载图片ID {img_id}: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 处理图片
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        img = img.resize(target_size, Image.LANCZOS)
        
        # 缓存到内存（限制缓存大小）
        with _image_content_cache_lock:
            if len(_image_content_cache) < 200:  # 限制缓存大小
                _image_content_cache[cache_key] = img.copy()
                logger.debug(f"图片内容已缓存: {img_id}")
        
        return img
    except Exception as e:
        logger.warning(f"下载图片ID {img_id} 失败: {e}")
        return None

def get_placeholder_image(target_size=(120, 120)):
    """获取占位图"""
    placeholder_path = os.path.join(app.static_folder, "placeholder.png")
    if os.path.exists(placeholder_path):
        img = Image.open(placeholder_path).convert("RGBA")
        return img.resize(target_size, Image.LANCZOS)
    else:
        # 创建一个简单的占位图
        img = Image.new("RGBA", target_size, (200, 200, 200, 255))
        return img

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 首页
@app.route("/")
def index():
    logger.info("首页路由被调用")
    print("首页路由被调用 - 控制台输出")
    return render_template("index.html")

# 字库页面
@app.route("/library")
def library():
    logger.info("字库页面路由被调用")
    print("字库页面路由被调用 - 控制台输出")
    return render_template("library.html")

# 查看所有图片页面
@app.route("/view_all_images.html")
def view_all_images():
    return render_template("view_all_images.html")

# 集字页面
@app.route("/calligraphy_set")
def calligraphy_set():
    logger.info("集字页面路由被调用")
    print("集字页面路由被调用 - 控制台输出")
    return render_template("calligraphy_set.html")

# 布局测试页面
@app.route("/test_layout")
def test_layout():
    return render_template("test_layout.html")

# 调试测试页面
@app.route("/debug_test")
def debug_test():
    from datetime import datetime
    logger.info("调试测试页面路由被调用")
    return render_template("debug_test.html", current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# 设置页面
@app.route("/settings")
def settings():
    logger.info("设置页面路由被调用")
    print("设置页面路由被调用 - 控制台输出")
    return render_template("settings.html")



# 获取下拉选项
@app.route("/api/options")
def api_options():
    logger.debug("api_options函数被调用，使用的是修改后的代码")
    conn = get_db()
    fonts = [row["name"] for row in conn.execute("SELECT name FROM fonts ORDER BY name").fetchall()]
    authors = [row["name"] for row in conn.execute("SELECT name FROM authors ORDER BY name").fetchall()]
    books = [row["title"] for row in conn.execute("SELECT title FROM books ORDER BY title").fetchall()]
    conn.close()
    return jsonify({"fonts": fonts, "authors": authors, "books": books})

# 获取特定字符的书法家和典籍选项
@app.route("/api/char_options")
def char_options():
    han = request.args.get("han", "").strip()
    
    if not han:
        return jsonify({"authors": [], "books": []})
    
    conn = get_db()
    
    # 获取该字符的所有书法家
    authors_query = """
        SELECT DISTINCT a.name 
        FROM glyphs g 
        LEFT JOIN authors a ON g.author_id = a.id 
        WHERE g.han = ? AND a.name IS NOT NULL 
        ORDER BY a.name
    """
    authors = [row["name"] for row in conn.execute(authors_query, (han,)).fetchall()]
    
    # 获取该字符的所有典籍
    books_query = """
        SELECT DISTINCT b.title 
        FROM glyphs g 
        LEFT JOIN books b ON g.book_id = b.id 
        WHERE g.han = ? AND b.title IS NOT NULL 
        ORDER BY b.title
    """
    books = [row["title"] for row in conn.execute(books_query, (han,)).fetchall()]
    
    conn.close()
    
    logger.debug(f"字符 '{han}' 的书法家数量: {len(authors)}, 典籍数量: {len(books)}")
    
    return jsonify({"authors": authors, "books": books})

# 搜索接口
@app.route("/api/search")
def search():
    han = request.args.get("han", "").strip()
    font = request.args.get("font", "").strip()
    author = request.args.get("author", "").strip()
    book = request.args.get("book", "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    # 添加调试日志
    logger.info(f"收到/api/search请求")
    logger.debug(f"- han: {han}")
    logger.debug(f"- font: {font}")
    logger.debug(f"- author: {author}")
    logger.debug(f"- book: {book}")
    # 添加获取所有结果的参数
    get_all = request.args.get("all", "false").lower() == "true"

    where_clauses = []
    params = []

    if han:
        # 支持多字搜索，自动拆分每个汉字
        han_chars = list(han)
        if len(han_chars) == 1:
            where_clauses.append("g.han = ?")
            params.append(han_chars[0])
        else:
            # 使用IN操作符匹配多个汉字
            placeholders = ", ".join(["?"] * len(han_chars))
            where_clauses.append(f"g.han IN ({placeholders})")
            params.extend(han_chars)
    if font:
        where_clauses.append("f.name = ?")
        params.append(font)
    if author:
        where_clauses.append("a.name = ?")
        params.append(author)
    if book:
        where_clauses.append("b.title = ?")
        params.append(book)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    conn = get_db()
    cur = conn.cursor()

    # 统计总数
    cur.execute(f"SELECT COUNT(*) FROM glyphs g LEFT JOIN fonts f ON g.font_id = f.id LEFT JOIN authors a ON g.author_id = a.id LEFT JOIN books b ON g.book_id = b.id {where_sql}", params)
    total = cur.fetchone()[0]

    # 查询数据
    query_sql = f"""
        SELECT g.id, g.han, f.name AS font, a.name AS author, b.title AS book_title
        FROM glyphs g
        LEFT JOIN fonts f ON g.font_id = f.id
        LEFT JOIN authors a ON g.author_id = a.id
        LEFT JOIN books b ON g.book_id = b.id
        {where_sql}
        ORDER BY g.id
    """

    if get_all:
        # 获取所有结果
        cur.execute(query_sql, params)
        results = [dict(row) for row in cur.fetchall()]
        per_page = total  # 设置每页数量为总数
    else:
        # 分页查询
        offset = (page - 1) * per_page
        cur.execute(query_sql + " LIMIT ? OFFSET ?", params + [per_page, offset])
        results = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify({
        "total": total,
        "per_page": per_page,
        "results": results
    })


# 图片接口 - 返回单个图片
@app.route("/image/<int:glyph_id>")
def image(glyph_id):
    conn = get_db()
    row = conn.execute("SELECT url FROM images WHERE glyph_id = ? LIMIT 1", (glyph_id,)).fetchone()
    conn.close()

    if row:
        # 直接返回图片URL，让客户端自行下载
        return jsonify({"image_url": row["url"]})
    return "Image not found", 404

# 新接口 - 返回某个glyph的所有图片
@app.route("/images/<int:glyph_id>")
def images(glyph_id):
    conn = get_db()
    rows = conn.execute("SELECT url FROM images WHERE glyph_id = ?", (glyph_id,)).fetchall()
    conn.close()

    if rows:
        # 返回所有图片URL
        return jsonify({"image_urls": [row["url"] for row in rows]})
    return jsonify({"image_urls": []}), 404

# 生成集字API
@app.route("/api/generate_calligraphy")
def generate_calligraphy():
    text = request.args.get("text", "").strip()
    font = request.args.get("font", "").strip()
    direction = request.args.get("direction", "horizontal").strip()
    chars_per_line = request.args.get("chars_per_line", "5").strip()
    calligrapher = request.args.get("calligrapher", "").strip()
    book = request.args.get("book", "").strip()

    if not text:
        return jsonify({"success": False, "message": "请输入文字内容"})

    # 拆分文字为单个字符
    characters = list(text)
    result = []

    conn = get_db()

    for char in characters:
        # 查询该字符的图片
        query = """
            SELECT g.id, g.han, f.name AS font, a.name AS author, b.title AS book
            FROM glyphs g
            LEFT JOIN fonts f ON g.font_id = f.id
            LEFT JOIN authors a ON g.author_id = a.id
            LEFT JOIN books b ON g.book_id = b.id
            WHERE g.han = ?
        """
        params = [char]

        if font:
            query += " AND f.name = ?"
            params.append(font)

        if calligrapher:
            query += " AND a.name = ?"
            params.append(calligrapher)

        if book:
            query += " AND b.title = ?"
            params.append(book)

        query += " ORDER BY g.id LIMIT 1"

        row = conn.execute(query, params).fetchone()

        if row:
            # 获取该字符的图片URLs和IDs
            image_rows = conn.execute("SELECT id, url FROM images WHERE glyph_id = ?", (row["id"],)).fetchall()
            image_urls = [img_row["url"] for img_row in image_rows]
            image_ids = [img_row["id"] for img_row in image_rows]

            # 将图片ID到URL的映射缓存起来，避免导出时重复查询
            for img_row in image_rows:
                cache_key = f"image_url_{img_row['id']}"
                image_cache.set(cache_key, img_row["url"])
                logger.debug(f"缓存图片ID {img_row['id']} -> URL: {img_row['url']}")

            result.append({
                "han": row["han"],
                "font": row["font"],
                "author": row["author"],
                "glyph_id": row["id"],
                "image_urls": image_urls,
                "image_ids": image_ids
            })
        else:
            # 没有找到该字符的图片
            result.append({
                "han": char,
                "font": None,
                "author": None,
                "glyph_id": None,
                "image_urls": [],
                "image_ids": []
            })

    conn.close()

    return jsonify({
        "success": True,
        "characters": result,
        "direction": direction,
        "chars_per_line": chars_per_line
    })

# 保存集字API
@app.route("/api/save_calligraphy", methods=["POST"])
def save_calligraphy():
    data = request.json
    text = data.get("text", "").strip()
    font = data.get("font", "").strip()

    if not text:
        return jsonify({"success": False, "message": "请输入文字内容"})

    # 这里只是一个示例实现，实际应用中可能需要将集字结果保存到数据库
    # 或者生成一个图片并保存到服务器

    return jsonify({
        "success": True,
        "message": "集字已保存"
    })



# 优化版导出图片API - 使用图片ID
@app.route("/export_image_by_ids", methods=["POST"])
def export_image_by_ids():
    try:
        data = request.json
        logger.info("收到导出请求数据（使用图片ID）")
        logger.debug(f"请求数据: {data}")

        # 验证数据格式
        if not data or "image_ids" not in data:
            logger.error("请求数据格式错误，缺少image_ids字段")
            return "Invalid request data, 'image_ids' field is required", 400

        image_ids = data["image_ids"]
        cols = data.get("cols", 10)  # 每行多少个字
        direction = data.get("direction", "horizontal")  # 排列方向
        logger.debug(f"接收到的排列方向: {direction}")

        # 验证image_ids是列表且不为空
        if not isinstance(image_ids, list) or len(image_ids) == 0:
            logger.error("image_ids必须是非空列表")
            return "'image_ids' must be a non-empty list", 400

        # 优先从缓存获取图片URL，减少数据库查询
        id_to_url = {}
        cache_miss_ids = []  # 缓存中没有的ID
        
        # 过滤掉None值和占位符，并转换为整数类型
        valid_image_ids = []
        for img_id in image_ids:
            if img_id is not None and img_id != 'placeholder':
                try:
                    img_id_int = int(img_id)
                    valid_image_ids.append(img_id_int)
                    
                    # 先尝试从缓存获取
                    cache_key = f"image_url_{img_id_int}"
                    cached_url = image_cache.get(cache_key)
                    if cached_url:
                        id_to_url[img_id_int] = cached_url
                        logger.debug(f"从缓存获取图片ID {img_id_int} -> URL: {cached_url}")
                    else:
                        cache_miss_ids.append(img_id_int)
                        logger.debug(f"缓存中未找到图片ID {img_id_int}，需要查询数据库")
                except (ValueError, TypeError):
                    logger.warning(f"无法转换图片ID为整数: {img_id}")
        
        # 只查询缓存中没有的图片ID
        if cache_miss_ids:
            logger.info(f"需要从数据库查询 {len(cache_miss_ids)} 个图片ID: {cache_miss_ids}")
            conn = get_db()
            placeholders = ','.join(['?' for _ in cache_miss_ids])
            query = f"SELECT id, url FROM images WHERE id IN ({placeholders})"
            image_rows = conn.execute(query, cache_miss_ids).fetchall()
            
            # 将查询结果添加到映射中，并缓存起来
            for row in image_rows:
                id_to_url[row["id"]] = row["url"]
                cache_key = f"image_url_{row['id']}"
                image_cache.set(cache_key, row["url"])
                logger.debug(f"从数据库查询并缓存图片ID {row['id']} -> URL: {row['url']}")
            
            conn.close()
        else:
            logger.info("所有图片URL都从缓存中获取，无需查询数据库")
        
        logger.info(f"缓存命中率: {(len(valid_image_ids) - len(cache_miss_ids)) / len(valid_image_ids) * 100:.1f}%" if valid_image_ids else "N/A")
        logger.info(f"当前缓存大小: {image_cache.size()} 个条目")

        # 设置统一的图片尺寸 - 增大尺寸以获得更好的效果
        target_size = (120, 120)  # 增大图片尺寸
        
        # 准备下载任务
        download_tasks = []
        for img_id in image_ids:
            if img_id is None or img_id == 'placeholder':
                download_tasks.append(('placeholder', None))
            else:
                try:
                    img_id_int = int(img_id)
                    if img_id_int in id_to_url:
                        url = id_to_url[img_id_int]
                        download_tasks.append((img_id_int, url))
                    else:
                        logger.warning(f"图片ID {img_id} 在数据库中不存在，使用占位图")
                        download_tasks.append(('placeholder', None))
                except (ValueError, TypeError):
                    logger.warning(f"无效的图片ID: {img_id}")
                    download_tasks.append(('placeholder', None))
        
        # 并发下载和处理图片
        logger.info(f"开始并发下载 {len(download_tasks)} 张图片")
        start_time = time.time()
        
        pil_images = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有下载任务
            future_to_index = {}
            for index, (img_id, url) in enumerate(download_tasks):
                if img_id == 'placeholder':
                    # 直接处理占位图，不需要下载
                    future = executor.submit(get_placeholder_image, target_size)
                else:
                    future = executor.submit(download_and_process_image, img_id, url, target_size)
                future_to_index[future] = index
            
            # 收集结果，保持顺序
            results = [None] * len(download_tasks)
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    img = future.result()
                    if img is not None:
                        results[index] = img
                    else:
                        # 下载失败，使用占位图
                        results[index] = get_placeholder_image(target_size)
                except Exception as e:
                    logger.warning(f"处理图片任务失败: {e}")
                    results[index] = get_placeholder_image(target_size)
            
            # 按顺序添加到pil_images
            for img in results:
                if img is not None:
                    pil_images.append(img)
        
        download_time = time.time() - start_time
        logger.info(f"并发下载完成，耗时: {download_time:.2f}秒，成功处理 {len(pil_images)} 张图片")

        if not pil_images:
            logger.error("没有成功加载任何图片")
            return "No images could be loaded", 400

        w, h = target_size
        
        # 根据排列方向调整行列计算和输出图像尺寸
        if direction in ['vertical-left', 'vertical-right']:
            rows_per_col = cols
            cols_used = (len(pil_images) + rows_per_col - 1) // rows_per_col
            rows_used = min(rows_per_col, len(pil_images))
            output_img = Image.new("RGBA", (w * cols_used, h * rows_per_col), (255, 255, 255, 0))
        else:
            rows_used = (len(pil_images) + cols - 1) // cols
            output_img = Image.new("RGBA", (w * cols, h * rows_used), (255, 255, 255, 0))

        # 根据排列方向调整图片位置
        logger.info(f"开始处理 {len(pil_images)} 张图片，排列方向: {direction}")
        if direction == "horizontal":
            for idx, img in enumerate(pil_images):
                x = (idx % cols) * w
                y = (idx // cols) * h
                output_img.paste(img, (x, y))
        elif direction == "horizontal-reverse":
            for idx, img in enumerate(pil_images):
                row = idx // cols
                col = cols - 1 - (idx % cols)
                x = col * w
                y = row * h
                output_img.paste(img, (x, y))
        elif direction == "vertical-left":
            for idx, img in enumerate(pil_images):
                col = idx // rows_per_col
                row = idx % rows_per_col
                x = col * w
                y = row * h
                output_img.paste(img, (x, y))
        elif direction == "vertical-right":
            for idx, img in enumerate(pil_images):
                col = (cols_used - 1) - (idx // rows_per_col)
                row = idx % rows_per_col
                x = col * w
                y = row * h
                output_img.paste(img, (x, y))
        else:
            for idx, img in enumerate(pil_images):
                x = (idx % cols) * w
                y = (idx // cols) * h
                output_img.paste(img, (x, y))

        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        buf.seek(0)
        logger.info("图片导出成功（使用图片ID）")
        return send_file(buf, mimetype="image/png", as_attachment=True, download_name="calligraphy_set.png")
    except Exception as e:
        logger.error(f"导出图片时发生错误: {e}")
        return f"Error exporting image: {str(e)}", 500

# 原有导出图片API（保持兼容性）
@app.route("/export_image", methods=["POST"])
def export_image():
    try:
        data = request.json
        logger.info("收到导出请求数据")
        logger.debug(f"请求数据: {data}")

        # 验证数据格式
        if not data or "images" not in data:
            logger.error("请求数据格式错误，缺少images字段")
            return "Invalid request data, 'images' field is required", 400

        images = data["images"]
        cols = data.get("cols", 10)  # 每行多少个字
        direction = data.get("direction", "horizontal")  # 排列方向
        logger.debug(f"接收到的排列方向: {direction}")

        # 验证images是列表且不为空
        if not isinstance(images, list) or len(images) == 0:
            logger.error("images必须是非空列表")
            return "'images' must be a non-empty list", 400

        # 设置统一的图片尺寸 - 增大尺寸以获得更好的效果
        target_size = (120, 120)  # 增大图片尺寸
        pil_images = []
        original_sizes = []  # 记录原始图片尺寸用于调试
        for url in images:
            try:
                # 去除可能的引号和空格
                clean_url = url.strip().strip('"').strip('\'')
                logger.debug(f"尝试加载图片: {clean_url}")
                resp = requests.get(clean_url, stream=True, timeout=10)
                resp.raise_for_status()  # 抛出HTTP错误
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                original_sizes.append(img.size)  # 记录原始尺寸
                # 调整图片大小到统一尺寸
                img = img.resize(target_size, Image.LANCZOS)
                pil_images.append(img)
            except Exception as e:
                logger.warning(f"加载图片失败: {url}, 错误: {e}")
                # 使用占位图替代
                placeholder_path = os.path.join(app.static_folder, "placeholder.png")
                if os.path.exists(placeholder_path):
                    img = Image.open(placeholder_path).convert("RGBA")
                    original_sizes.append(img.size)  # 记录占位图原始尺寸
                    # 调整占位图大小到统一尺寸
                    img = img.resize(target_size, Image.LANCZOS)
                    pil_images.append(img)
                else:
                    logger.warning("占位图不存在，跳过该图片")

        if not pil_images:
            logger.error("没有成功加载任何图片")
            return "No images could be loaded", 400

        w, h = target_size  # 使用统一的尺寸
        
        # 根据排列方向调整行列计算和输出图像尺寸
        if direction in ['vertical-left', 'vertical-right']:
            # 垂直排列时，cols表示每列的字符数
            rows_per_col = cols  # 每列显示的行数
            cols_used = (len(pil_images) + rows_per_col - 1) // rows_per_col  # 计算需要多少列
            rows_used = min(rows_per_col, len(pil_images))
            # 垂直排列时，宽度和高度需要交换
            output_img = Image.new("RGBA", (w * cols_used, h * rows_per_col), (255, 255, 255, 0))
        else:
            # 水平排列时，cols表示每行的字符数
            rows_used = (len(pil_images) + cols - 1) // cols
            output_img = Image.new("RGBA", (w * cols, h * rows_used), (255, 255, 255, 0))

        # 根据排列方向调整图片位置
        logger.info(f"开始处理 {len(pil_images)} 张图片，排列方向: {direction}")
        if direction == "horizontal":
            # 从左到右，从上到下（默认）
            for idx, img in enumerate(pil_images):
                x = (idx % cols) * w
                y = (idx // cols) * h
                output_img.paste(img, (x, y))
        elif direction == "horizontal-reverse":
            # 从右到左，从上到下
            for idx, img in enumerate(pil_images):
                row = idx // cols
                col = cols - 1 - (idx % cols)
                x = col * w
                y = row * h
                output_img.paste(img, (x, y))
        elif direction == "vertical-left":
            # 从左上角开始，向下填充，达到字数限制换列
            for idx, img in enumerate(pil_images):
                col = idx // rows_per_col
                row = idx % rows_per_col
                x = col * w
                y = row * h
                output_img.paste(img, (x, y))
        elif direction == "vertical-right":
            # 从右上角开始，向下填充，达到字数限制换列
            for idx, img in enumerate(pil_images):
                col = (cols_used - 1) - (idx // rows_per_col)
                row = idx % rows_per_col
                x = col * w
                y = row * h
                output_img.paste(img, (x, y))
        else:
            # 默认使用水平排列
            for idx, img in enumerate(pil_images):
                x = (idx % cols) * w
                y = (idx // cols) * h
                output_img.paste(img, (x, y))

        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        buf.seek(0)
        logger.info("图片导出成功")
        return send_file(buf, mimetype="image/png", as_attachment=True, download_name="calligraphy_set.png")
    except Exception as e:
        logger.error(f"导出图片时发生错误: {e}")
        return f"Error exporting image: {str(e)}", 500

# 缓存管理API
@app.route("/api/cache/status")
def cache_status():
    """获取缓存状态"""
    return jsonify({
        "cache_size": image_cache.size(),
        "max_size": image_cache.max_size,
        "expire_time": image_cache.expire_time
    })

@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """清理缓存"""
    old_size = image_cache.size()
    image_cache.clear()
    logger.info(f"缓存已清理，清理前大小: {old_size}")
    return jsonify({
        "success": True,
        "message": f"缓存已清理，清理了 {old_size} 个条目"
    })

# 确保有占位图可用
if not os.path.exists(os.path.join(app.static_folder, "placeholder.png")):
    logger.warning("占位图不存在，将创建一个简单的占位图")
    placeholder = Image.new('RGBA', (100, 100), color=(200, 200, 200, 255))
    placeholder.save(os.path.join(app.static_folder, "placeholder.png"), format="PNG")

if __name__ == "__main__":
    # 显示日志配置信息
    log_level = os.environ.get('MOTU_LOG_LEVEL', 'info')
    log_to_file = os.environ.get('MOTU_LOG_TO_FILE', 'false').lower() == 'true'
    logger.info(f"启动应用，日志级别: {log_level}, 日志输出到文件: {log_to_file}")
    
    # 生产环境配置
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
