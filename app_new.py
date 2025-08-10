from flask import Flask, request, jsonify, send_file, render_template
import sqlite3
import os
from PIL import Image
import io
import requests
from dotenv import load_dotenv
from logger import get_logger, configure_from_env

# 加载环境变量
load_dotenv()

# 配置日志
logger = configure_from_env()

app = Flask(__name__)
DB_PATH = os.path.join("data", "shufadb.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 首页
@app.route("/")
def index():
    return render_template("index_new.html")

# 查看所有图片页面
@app.route("/view_all_images.html")
def view_all_images():
    return render_template("view_all_images.html")

# 集字页面
@app.route("/calligraphy_set")
def calligraphy_set():
    return render_template("calligraphy_set.html")

# 布局测试页面
@app.route("/test_layout")
def test_layout():
    return render_template("test_layout.html")

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

# 搜索接口
@app.route("/api/search")
def search():
    han = request.args.get("han", "").strip()
    font = request.args.get("font", "").strip()
    author = request.args.get("calligrapher", "").strip()
    book = request.args.get("book", "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    # 添加调试日志
    logger.info(f"收到/api/search请求")
    logger.debug(f"- han: {han}")
    logger.debug(f"- font: {font}")
    logger.debug(f"- calligrapher: {author}")
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
            # 获取该字符的图片URLs
            image_rows = conn.execute("SELECT url FROM images WHERE glyph_id = ?", (row["id"],)).fetchall()
            image_urls = [img_row["url"] for img_row in image_rows]

            result.append({
                "han": row["han"],
                "font": row["font"],
                "author": row["author"],
                "image_urls": image_urls
            })
        else:
            # 没有找到该字符的图片
            result.append({
                "han": char,
                "font": None,
                "author": None,
                "image_urls": []
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



# 导出图片API
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

        # 设置统一的图片尺寸
        target_size = (100, 100)  # 可以根据需要调整这个尺寸
        pil_images = []
        for url in images:
            try:
                # 去除可能的引号和空格
                clean_url = url.strip().strip('"').strip('\'')
                logger.debug(f"尝试加载图片: {clean_url}")
                resp = requests.get(clean_url, stream=True, timeout=10)
                resp.raise_for_status()  # 抛出HTTP错误
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                # 调整图片大小到统一尺寸
                img = img.resize(target_size, Image.LANCZOS)
                pil_images.append(img)
            except Exception as e:
                logger.warning(f"加载图片失败: {url}, 错误: {e}")
                # 使用占位图替代
                placeholder_path = os.path.join(app.static_folder, "placeholder.png")
                if os.path.exists(placeholder_path):
                    img = Image.open(placeholder_path).convert("RGBA")
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
            output_img = Image.new("RGBA", (h * cols_used, w * rows_per_col), (255, 255, 255, 255))
        else:
            # 水平排列时，cols表示每行的字符数
            rows_used = (len(pil_images) + cols - 1) // cols
            output_img = Image.new("RGBA", (w * cols, h * rows_used), (255, 255, 255, 255))

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
            logger.debug("使用垂直左排列逻辑")
            logger.debug(f"垂直排列参数: cols_used={cols_used}, rows_per_col={rows_per_col}, 图片尺寸={w}x{h}")
            # 从左上角开始，向下填充，达到字数限制换列
            for idx, img in enumerate(pil_images):
                col = idx // rows_per_col
                row = idx % rows_per_col
                x = col * h
                y = row * w
                logger.debug(f"图片 {idx}: 列={col}, 行={row}, X={x}, Y={y}")
                output_img.paste(img, (x, y))
        elif direction == "vertical-right":
            logger.debug("使用垂直右排列逻辑")
            # 从右上角开始，向下填充，达到字数限制换列
            for idx, img in enumerate(pil_images):
                col = (cols_used - 1) - (idx // rows_per_col)
                row = idx % rows_per_col
                x = col * h
                y = row * w
                logger.debug(f"图片 {idx}: 列={col}, 行={row}, X={x}, Y={y}")
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
