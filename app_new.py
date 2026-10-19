from flask import Flask, request, jsonify, send_file, render_template
import sqlite3
import os
import sys
import shutil
import json
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
import tempfile
from pathlib import Path
import product

# 加载环境变量
load_dotenv()

# 配置日志
logger = configure_from_env()
# 使用默认日志级别

# 本地图片目录配置
LOCAL_IMAGE_DIR = os.getenv("LOCAL_IMAGE_DIR", r"E:\书法字库\test")
USE_LOCAL_IMAGES = os.getenv("USE_LOCAL_IMAGES", "false").lower() == "true"

app = Flask(__name__)
# 禁用模板缓存，确保开发时能加载最新模板
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
DB_PATH = os.getenv(
    "MOTU_DB_PATH", str(Path(__file__).resolve().parent / "data" / "shufadb.db")
)
FEEDBACK_DB_PATH = str(Path(__file__).resolve().parent / "data" / "feedback.db")
CALLIREADER_BASE_DIR = os.path.join("data", "models", "CalliReader")
_callireader_model = None
_callireader_lock = threading.Lock()


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

        # Determine if URL is local or remote
        if url.startswith("/local_image/"):
            logger.debug(f"读取本地图片ID {img_id}: {url}")
            # Try to find the local file again since we only have the route URL here
            file_path = None
            for ext in [".jpg", ".png", ".jpeg", ".webp", ".bmp"]:
                temp_path = os.path.join(LOCAL_IMAGE_DIR, f"{img_id}{ext}")
                if os.path.exists(temp_path):
                    file_path = temp_path
                    break

            if file_path:
                img = Image.open(file_path).convert("RGBA")
            else:
                logger.warning(f"本地图片不存在: {img_id}")
                return None
        else:
            # 下载图片
            logger.debug(f"下载图片ID {img_id}: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content)).convert("RGBA")

        # 处理图片
        img = img.resize(target_size, Image.LANCZOS)

        # 缓存到内存（限制缓存大小）
        with _image_content_cache_lock:
            if len(_image_content_cache) < 200:  # 限制缓存大小
                _image_content_cache[cache_key] = img.copy()
                logger.debug(f"图片内容已缓存: {img_id}")

        return img
    except Exception as e:
        logger.warning(f"获取图片ID {img_id} 失败: {e}")
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
    conn = sqlite3.connect(
        Path(DB_PATH).resolve().as_uri() + "?mode=ro", uri=True, timeout=60
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_feedback_db():
    conn = sqlite3.connect(FEEDBACK_DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _patch_callireader_config_file(base_dir):
    config_path = os.path.join(base_dir, "InternVL", "configuration_internvl_chat.py")
    if not os.path.exists(config_path):
        return
    with open(config_path, "r", encoding="utf-8") as f:
        text = f.read()
    old_cond = "if llm_config['architectures'][0] == 'LlamaForCausalLM':"
    if old_cond not in text:
        return
    text = text.replace(
        "self.vision_config = InternVisionConfig(**vision_config)\n        if llm_config['architectures'][0] == 'LlamaForCausalLM':",
        "self.vision_config = InternVisionConfig(**vision_config)\n        arch = llm_config.get('architectures', ['LlamaForCausalLM'])[0]\n        if arch == 'LlamaForCausalLM':",
    )
    text = text.replace(
        "elif llm_config['architectures'][0] == 'InternLM2ForCausalLM':",
        "elif arch == 'InternLM2ForCausalLM':",
    )
    text = text.replace("llm_config['architectures'][0]", "arch")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(text)


def _patch_callireader_json_config(base_dir):
    config_path = os.path.join(base_dir, "InternVL", "config.json")
    if not os.path.exists(config_path):
        return
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    changed = False
    vision_cfg = config.get("vision_config", {})
    if (
        isinstance(vision_cfg, dict)
        and vision_cfg.get("use_flash_attn", None) is not False
    ):
        vision_cfg["use_flash_attn"] = False
        config["vision_config"] = vision_cfg
        changed = True
    llm_cfg = config.get("llm_config", {})
    if isinstance(llm_cfg, dict):
        if llm_cfg.get("attn_implementation", None) != "eager":
            llm_cfg["attn_implementation"] = "eager"
            changed = True
        config["llm_config"] = llm_cfg
    if changed:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


def _prepare_callireader_runtime(base_dir):
    required_paths = [
        os.path.join(base_dir, "InternVL", "config.json"),
        os.path.join(base_dir, "InternVL", "preprocessor_config.json"),
        os.path.join(base_dir, "InternVL", "modeling_internvl_chat.py"),
        os.path.join(base_dir, "InternVL", "configuration_internvl_chat.py"),
        os.path.join(base_dir, "InternVL", "model-00001-of-00004.safetensors"),
        os.path.join(base_dir, "InternVL", "model-00002-of-00004.safetensors"),
        os.path.join(base_dir, "InternVL", "model-00003-of-00004.safetensors"),
        os.path.join(base_dir, "InternVL", "model-00004-of-00004.safetensors"),
        os.path.join(base_dir, "models", "model.py"),
        os.path.join(base_dir, "models", "similarity.py"),
        os.path.join(base_dir, "utils", "utils.py"),
        os.path.join(base_dir, "config", "configu.py"),
        os.path.join(base_dir, "params", "best.pt"),
        os.path.join(base_dir, "params", "gauss_norm.pth"),
        os.path.join(base_dir, "params", "gauss_norm_mu_sigma.pth"),
        os.path.join(base_dir, "params", "mlp1.pth"),
        os.path.join(base_dir, "params", "token_embedding.pth"),
        os.path.join(base_dir, "params", "vit_model.pt"),
        os.path.join(base_dir, "params", "callialign.pth"),
        os.path.join(base_dir, "params", "orderformer.pth"),
        os.path.join(base_dir, "params", "new1000_token_embedding.pth"),
    ]
    missing = [p for p in required_paths if not os.path.exists(p)]
    if missing:
        missing_rel = [os.path.relpath(p, base_dir) for p in missing]
        return False, f"缺少文件: {', '.join(missing_rel)}"
    abs_base = os.path.abspath(base_dir)
    if abs_base not in sys.path:
        sys.path.insert(0, abs_base)
    hf_cache_mod = os.path.join(
        os.path.expanduser("~"),
        ".cache",
        "huggingface",
        "modules",
        "transformers_modules",
        "InternVL",
    )
    if os.path.exists(hf_cache_mod):
        shutil.rmtree(hf_cache_mod, ignore_errors=True)
    _patch_callireader_config_file(abs_base)
    _patch_callireader_json_config(abs_base)
    return True, ""


def _get_callireader_model():
    global _callireader_model
    with _callireader_lock:
        if _callireader_model is not None:
            return _callireader_model, ""
        try:
            import torch

            if not torch.cuda.is_available():
                return (
                    None,
                    "当前环境未检测到 CUDA，CalliReader 暂不支持在本机 CPU 模式稳定加载",
                )
        except Exception:
            return None, "当前环境缺少可用的 torch CUDA 运行条件"
        base_dir = os.path.abspath(CALLIREADER_BASE_DIR)
        ok, msg = _prepare_callireader_runtime(base_dir)
        if not ok:
            return None, msg
        os.environ["CHECKER_OCR_BACKEND"] = "callireader"
        os.environ["CHECKER_CALLIREADER_DIR"] = base_dir
        try:
            from tools.checker_app import ChineseCalligraphyRecognitionV1

            model = ChineseCalligraphyRecognitionV1()
            if model.backend_active != "callireader":
                return (
                    None,
                    model.load_error or f"模型未激活，当前后端: {model.backend_active}",
                )
            _callireader_model = model
            return _callireader_model, ""
        except Exception as e:
            return None, str(e)


def _recognize_callireader_image_file(local_image_path):
    model, err = _get_callireader_model()
    if model is None:
        return None, "", err
    try:
        result, _ = model.callireader_model.chat_ocr(
            model.callireader_tokenizer,
            model.callireader_detector,
            local_image_path,
            model.callireader_prompt,
            model.callireader_generation_config,
            use_p=True,
            hard_vq=False,
            drop_zero=True,
            repetition_penalty=1.2,
            return_history=True,
            verbose=False,
        )
        predicted_text = (result or "").strip().replace(" ", "")
        return predicted_text, model.backend_active, ""
    except Exception as e:
        return None, model.backend_active, str(e)


# 首页
@app.route("/")
def index():
    logger.info("首页路由被调用")
    print("首页路由被调用 - 控制台输出")
    return render_template("index.html", page="home")


# 字库页面
@app.route("/library")
def library():
    logger.info("字库页面路由被调用")
    print("字库页面路由被调用 - 控制台输出")
    return render_template("library.html", page="library")


# 查看所有图片页面
@app.route("/view_all_images.html")
def view_all_images():
    return render_template("view_all_images.html", page="library")


# 集字页面
@app.route("/calligraphy_set")
def calligraphy_set():
    logger.info("集字页面路由被调用")
    print("集字页面路由被调用 - 控制台输出")
    return render_template("calligraphy_set.html", page="compose")


# 布局测试页面
@app.route("/test_layout")
def test_layout():
    return render_template("test_layout.html")


# 调试测试页面
@app.route("/debug_test")
def debug_test():
    from datetime import datetime

    logger.info("调试测试页面路由被调用")
    return render_template(
        "debug_test.html", current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


# 设置页面
@app.route("/settings")
def settings():
    logger.info("设置页面路由被调用")
    print("设置页面路由被调用 - 控制台输出")
    return render_template("settings.html", page="settings")


# 反馈接口
@app.route("/api/report", methods=["POST"])
def report_error():
    """兼容既有入口，使用统一的业务校验与存储服务。"""
    return product.feedback()


# 获取下拉选项
@app.route("/api/options")
def api_options():
    logger.debug("api_options函数被调用，使用的是修改后的代码")
    conn = get_db()
    fonts = [
        row["name"]
        for row in conn.execute("SELECT name FROM fonts ORDER BY name").fetchall()
    ]
    authors = [
        row["name"]
        for row in conn.execute("SELECT name FROM authors ORDER BY name").fetchall()
    ]
    books = [
        row["title"]
        for row in conn.execute("SELECT title FROM books ORDER BY title").fetchall()
    ]
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
    """兼容既有入口，使用统一的业务校验与存储服务。"""
    return product.search_catalogue()


@app.route("/local_image/<int:image_id>")
def local_image(image_id):
    """Serve images from the local test directory based on image_id."""
    # We assume image names are like "123.jpg", "123.png", etc.
    # Try common extensions
    for ext in [".jpg", ".png", ".jpeg", ".webp", ".bmp"]:
        file_path = os.path.join(LOCAL_IMAGE_DIR, f"{image_id}{ext}")
        if os.path.exists(file_path):
            return send_file(file_path)

    # If not found, maybe return placeholder or 404
    return "Image not found locally", 404


# 图片接口 - 返回单个图片
@app.route("/image/<int:glyph_id>")
def image(glyph_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, url FROM images WHERE glyph_id = ? LIMIT 1", (glyph_id,)
    ).fetchone()
    conn.close()

    if row:
        if USE_LOCAL_IMAGES:
            # Check if local image exists before returning local URL
            image_id = row["id"]
            for ext in [".jpg", ".png", ".jpeg", ".webp", ".bmp"]:
                file_path = os.path.join(LOCAL_IMAGE_DIR, f"{image_id}{ext}")
                if os.path.exists(file_path):
                    return jsonify({"image_url": f"/local_image/{image_id}"})
            # Fallback to original URL if local not found

        return jsonify({"image_url": row["url"]})
    return "Image not found", 404


# 新接口 - 返回某个glyph的所有图片
@app.route("/images/<int:glyph_id>")
def images(glyph_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, url FROM images WHERE glyph_id = ?", (glyph_id,)
    ).fetchall()
    conn.close()

    if rows:
        image_urls = []
        image_ids = []
        for row in rows:
            img_id = row["id"]
            img_url = row["url"]
            image_ids.append(img_id)

            if USE_LOCAL_IMAGES:
                local_found = False
                for ext in [".jpg", ".png", ".jpeg", ".webp", ".bmp"]:
                    file_path = os.path.join(LOCAL_IMAGE_DIR, f"{img_id}{ext}")
                    if os.path.exists(file_path):
                        image_urls.append(f"/local_image/{img_id}")
                        local_found = True
                        break
                if not local_found:
                    image_urls.append(img_url)
            else:
                image_urls.append(img_url)

        return jsonify({"image_urls": image_urls, "image_ids": image_ids})
    return jsonify({"image_urls": [], "image_ids": []}), 404


# 生成集字API
@app.route("/api/generate_calligraphy")
def generate_calligraphy():
    """兼容既有入口，使用统一的业务校验与存储服务。"""
    return product.compose()


# 保存集字API
@app.route("/api/save_calligraphy", methods=["POST"])
def save_calligraphy():
    """兼容既有入口，使用统一的业务校验与存储服务。"""
    return product.create_work()


# 优化版导出图片API - 使用图片ID
@app.route("/export_image_by_ids", methods=["POST"])
def export_image_by_ids():
    """兼容既有入口，使用统一的业务校验与存储服务。"""
    return product.export_work()


# 原有导出图片API（保持兼容性）
@app.route("/export_image", methods=["POST"])
def export_image():
    """兼容既有入口，使用统一的业务校验与存储服务。"""
    return product.export_work()


# 缓存管理API
@app.route("/api/cache/status")
def cache_status():
    """获取缓存状态"""
    return jsonify(
        {
            "cache_size": image_cache.size(),
            "max_size": image_cache.max_size,
            "expire_time": image_cache.expire_time,
        }
    )


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """清理缓存"""
    old_size = image_cache.size()
    image_cache.clear()
    logger.info(f"缓存已清理，清理前大小: {old_size}")
    return jsonify(
        {"success": True, "message": f"缓存已清理，清理了 {old_size} 个条目"}
    )


# 确保有占位图可用
if not os.path.exists(os.path.join(app.static_folder, "placeholder.png")):
    logger.warning("占位图不存在，将创建一个简单的占位图")
    placeholder = Image.new("RGBA", (100, 100), color=(200, 200, 200, 255))
    placeholder.save(os.path.join(app.static_folder, "placeholder.png"), format="PNG")

product.init_product(app)

if __name__ == "__main__":
    # 显示日志配置信息
    log_level = os.environ.get("MOTU_LOG_LEVEL", "info")
    log_to_file = os.environ.get("MOTU_LOG_TO_FILE", "false").lower() == "true"
    logger.info(f"启动应用，日志级别: {log_level}, 日志输出到文件: {log_to_file}")

    # 生产环境配置
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    app.run(host=host, port=port, debug=debug)
