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
FEEDBACK_DB_PATH = os.path.join("data", "feedback.db")
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
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
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
        "self.vision_config = InternVisionConfig(**vision_config)\n        arch = llm_config.get('architectures', ['LlamaForCausalLM'])[0]\n        if arch == 'LlamaForCausalLM':"
    )
    text = text.replace("elif llm_config['architectures'][0] == 'InternLM2ForCausalLM':", "elif arch == 'InternLM2ForCausalLM':")
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
    if isinstance(vision_cfg, dict) and vision_cfg.get("use_flash_attn", None) is not False:
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
        os.path.join(base_dir, "params", "new1000_token_embedding.pth")
    ]
    missing = [p for p in required_paths if not os.path.exists(p)]
    if missing:
        missing_rel = [os.path.relpath(p, base_dir) for p in missing]
        return False, f"缺少文件: {', '.join(missing_rel)}"
    abs_base = os.path.abspath(base_dir)
    if abs_base not in sys.path:
        sys.path.insert(0, abs_base)
    hf_cache_mod = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "modules", "transformers_modules", "InternVL")
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
                return None, "当前环境未检测到 CUDA，CalliReader 暂不支持在本机 CPU 模式稳定加载"
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
                return None, model.load_error or f"模型未激活，当前后端: {model.backend_active}"
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
            verbose=False
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

# 管理员页面
@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/ocr_test")
def ocr_test():
    return render_template("ocr_test.html")

@app.route("/api/ocr_test/recognize", methods=["POST"])
def ocr_test_recognize():
    image_file = request.files.get("image")
    if image_file is None:
        return jsonify({"success": False, "message": "请上传图片文件"}), 400
    filename = (image_file.filename or "").lower()
    if not filename:
        return jsonify({"success": False, "message": "文件名无效"}), 400
    ext = os.path.splitext(filename)[1]
    if ext not in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
        return jsonify({"success": False, "message": "仅支持 png/jpg/jpeg/bmp/webp"}), 400
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
            image_file.save(f)
            temp_path = f.name
        text, backend_active, err = _recognize_callireader_image_file(temp_path)
        if err:
            return jsonify({"success": False, "message": f"识别失败: {err}"}), 500
        return jsonify({
            "success": True,
            "backend_active": backend_active,
            "text": text or ""
        })
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

# 反馈接口
@app.route("/api/report", methods=["POST"])
def report_error():
    data = request.json
    glyph_id = data.get("glyph_id")
    image_id = data.get("image_id")
    han = data.get("han")
    font = data.get("font")
    author = data.get("author")
    book = data.get("book_title") # 注意：前端传的是book_title
    image_url = data.get("image_url")
    reason = data.get("reason", "图片与文字不符")

    if not glyph_id:
        return jsonify({"success": False, "message": "缺少必要参数"}), 400

    try:
        conn = get_feedback_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reports (glyph_id, image_id, han, font, author, book_title, image_url, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (glyph_id, image_id, han, font, author, book, image_url, reason))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "反馈已提交"})
    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# 获取反馈列表（管理员）
@app.route("/api/admin/reports")
def get_reports():
    status = request.args.get("status", "pending")
    reason_filter = request.args.get("reason", "").strip()
    max_conf = request.args.get("max_conf", "").strip()
    han_filter = request.args.get("han", "").strip()  # 新增汉字检索参数
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 40)) # 默认每页显示40条
    
    conn = get_feedback_db()
    cur = conn.cursor()
    
    query_base = "FROM reports WHERE status = ?"
    params = [status]
    
    if reason_filter:
        query_base += " AND reason LIKE ?"
        params.append(f"%{reason_filter}%")
    
    if han_filter:  # 新增汉字检索逻辑
        query_base += " AND han = ?"
        params.append(han_filter)
    
    # 获取总数
    count_query = f"SELECT COUNT(*) {query_base}"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]
    
    # 获取分页数据
    query = f"SELECT * {query_base} ORDER BY created_at DESC"
    
    # 注意：如果启用了 max_conf，我们需要在内存中过滤，这意味着分页也会受影响
    # 简单的做法是：如果指定了 max_conf，先不分页获取所有数据，在内存中过滤后再分页
    # 复杂的做法是：如果数据量非常大，这种内存过滤不可行。
    # 考虑到当前需求，我们先实现内存过滤的分页逻辑
    
    if max_conf:
        cur.execute(query, params)
        all_reports = [dict(row) for row in cur.fetchall()]
        
        try:
            max_conf_val = float(max_conf)
            filtered_reports = []
            import re
            for r in all_reports:
                match = re.search(r"conf:\s*(\d+\.\d+)", r["reason"])
                if match:
                    conf_val = float(match.group(1))
                    if conf_val <= max_conf_val:
                        filtered_reports.append(r)
                else:
                    # 如果没有conf，这里假设不显示
                    pass
            
            # 更新总数和切片
            total = len(filtered_reports)
            start = (page - 1) * per_page
            end = start + per_page
            reports = filtered_reports[start:end]
            
        except ValueError:
            # 如果max_conf无效，忽略它，走正常数据库分页
            query += " LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])
            cur.execute(query, params)
            reports = [dict(row) for row in cur.fetchall()]
    else:
        # 正常数据库分页
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        cur.execute(query, params)
        reports = [dict(row) for row in cur.fetchall()]

    conn.close()
    
    return jsonify({
        "success": True, 
        "reports": reports,
        "total": total,
        "page": page,
        "per_page": per_page
    })

@app.route("/api/admin/verify_texts", methods=["POST"])
def verify_texts():
    data = request.json or {}
    report_ids = data.get("report_ids", [])
    if not isinstance(report_ids, list) or len(report_ids) == 0:
        return jsonify({"success": False, "message": "缺少 report_ids"}), 400
    conn = get_feedback_db()
    cur = conn.cursor()
    placeholders = ",".join(["?" for _ in report_ids])
    cur.execute(f"SELECT id, han, image_url FROM reports WHERE id IN ({placeholders})", report_ids)
    rows = cur.fetchall()
    conn.close()
    row_map = {int(r["id"]): dict(r) for r in rows}
    model, err = _get_callireader_model()
    if model is None:
        return jsonify({"success": False, "message": f"CalliReader未就绪: {err}"}), 500
    results = []
    for rid in report_ids:
        if rid not in row_map:
            results.append({
                "report_id": rid,
                "success": False,
                "message": "记录不存在"
            })
            continue
        row = row_map[rid]
        expected = (row.get("han") or "").strip()
        image_url = (row.get("image_url") or "").strip()
        if not expected or not image_url:
            results.append({
                "report_id": rid,
                "success": False,
                "message": "缺少 han 或 image_url"
            })
            continue
        predicted, confidence, is_match = model.predict(image_url, expected)
        results.append({
            "report_id": rid,
            "success": True,
            "expected": expected,
            "predicted": predicted,
            "confidence": round(float(confidence), 4),
            "is_match": bool(is_match),
            "backend_active": model.backend_active
        })
    return jsonify({
        "success": True,
        "backend_requested": model.backend_requested,
        "backend_active": model.backend_active,
        "results": results
    })

# 处理反馈（删除图片）
@app.route("/api/admin/handle_report_batch", methods=["POST"])
def handle_report_batch():
    data = request.json
    report_ids = data.get("report_ids", [])
    action = data.get("action") # 'ignore' (currently only support ignore for batch)
    
    if not report_ids or not action:
        return jsonify({"success": False, "message": "缺少必要参数"}), 400
        
    if action != 'ignore':
        return jsonify({"success": False, "message": "批量操作仅支持忽略"}), 400

    feedback_conn = get_feedback_db()
    feedback_cur = feedback_conn.cursor()
    
    try:
        # 批量更新状态
        placeholders = ','.join(['?' for _ in report_ids])
        feedback_cur.execute(f"UPDATE reports SET status = 'ignored' WHERE id IN ({placeholders})", report_ids)
        feedback_conn.commit()
        
        feedback_conn.close()
        return jsonify({"success": True, "message": f"已批量忽略 {len(report_ids)} 条记录"})
        
    except Exception as e:
        logger.error(f"批量处理反馈失败: {e}")
        feedback_conn.close()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/admin/handle_report", methods=["POST"])
def handle_report():
    # If it's a batch request (list of IDs), forward to batch handler
    if request.json and "report_ids" in request.json:
        return handle_report_batch()
        
    data = request.json
    report_id = data.get("report_id")
    action = data.get("action") # 'delete_image', 'delete_glyph', 'ignore'
    
    if not report_id or not action:
        return jsonify({"success": False, "message": "缺少必要参数"}), 400

    feedback_conn = get_feedback_db()
    feedback_cur = feedback_conn.cursor()
    
    # 获取报告详情
    report = feedback_cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not report:
        feedback_conn.close()
        return jsonify({"success": False, "message": "报告不存在"}), 404

    try:
        shufa_conn = get_db()
        shufa_cur = shufa_conn.cursor()

        if action == 'delete_image':
            if report['image_id']:
                # 删除指定图片
                shufa_cur.execute("DELETE FROM images WHERE id = ?", (report['image_id'],))
                # 检查该glyph是否还有其他图片，如果没有，是否要删除glyph？这里暂时保留glyph
                shufa_conn.commit()
                feedback_cur.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
            else:
                 # 如果没有image_id，尝试通过url删除
                if report['image_url']:
                    shufa_cur.execute("DELETE FROM images WHERE url = ?", (report['image_url'],))
                    shufa_conn.commit()
                    feedback_cur.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
                else:
                    shufa_conn.close()
                    feedback_conn.close()
                    return jsonify({"success": False, "message": "无法定位图片，缺少ID和URL"}), 400

        elif action == 'delete_glyph':
            # 删除整个字条目及其所有图片
            shufa_cur.execute("DELETE FROM images WHERE glyph_id = ?", (report['glyph_id'],))
            shufa_cur.execute("DELETE FROM glyphs WHERE id = ?", (report['glyph_id'],))
            shufa_conn.commit()
            feedback_cur.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))

        elif action == 'ignore':
            feedback_cur.execute("UPDATE reports SET status = 'ignored' WHERE id = ?", (report_id,))
        
        else:
            shufa_conn.close()
            feedback_conn.close()
            return jsonify({"success": False, "message": "无效的操作"}), 400

        feedback_conn.commit()
        shufa_conn.close()
        feedback_conn.close()
        
        # 清理缓存
        if action in ['delete_image', 'delete_glyph']:
            image_cache.clear()
            
        return jsonify({"success": True, "message": "操作成功"})

    except Exception as e:
        logger.error(f"处理反馈失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500





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
    rows = conn.execute("SELECT id, url FROM images WHERE glyph_id = ?", (glyph_id,)).fetchall()
    conn.close()

    if rows:
        # 返回所有图片URL和ID
        return jsonify({
            "image_urls": [row["url"] for row in rows],
            "image_ids": [row["id"] for row in rows]
        })
    return jsonify({"image_urls": [], "image_ids": []}), 404

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
            # 修正：前端已经对image_ids进行了重排（最右列的数据在数组前面/后面？取决于前端逻辑）
            # 前端 vertical-right 重排逻辑：[Col Max ... Col 0] (DOM顺序)
            # image_ids[0] 属于最右列。
            # 所以 idx // rows_per_col 越大，列应该越靠左。
            # col = (cols_used - 1) - (idx // rows_per_col) 
            # 让我们重新推演一下。
            # 前端重排：
            # gridPosition = col * charsPerLine + row; 
            # rearrangedCharacters[gridPosition] = paddedCharacters[charIndex];
            # 这里 gridPosition 是 DOM 索引。
            # col 从 max 到 0。
            # 当 col=max 时，gridPosition 很大（数组末尾）。
            # 当 col=0 时，gridPosition 很小（数组开头）。
            # 所以数组开头 (index 0) 对应 col 0 (最左列)。
            # 数组末尾 (index max) 对应 col max (最右列)。
            # 
            # 前端填充逻辑：
            # rearranged[gridPosition] = paddedCharacters[charIndex]
            # charIndex 遍历文本顺序（第一句...最后一句）。
            # 
            # 例子：2列。Col 0 (左), Col 1 (右)。
            # col=1 (右)。gridPos=Row+Rows。填入 charIndex 0..Rows。即第一句填入 Col 1（数组后半部分）。
            # col=0 (左)。gridPos=Row。填入 charIndex Rows..Max。即第二句填入 Col 0（数组前半部分）。
            # 
            # 所以 DOM 数组：[第二句 (左列), 第一句 (右列)]。
            # 
            # 后端 image_ids: [第二句, 第一句]。
            # 
            # 遍历 image_ids：
            # idx=0 (第二句)。我们希望它在左列 (col=0)。
            # idx=Max (第一句)。我们希望它在右列 (col=1)。
            # 
            # 后端之前的逻辑：
            # col = (cols_used - 1) - (idx // rows_per_col)
            # idx=0 -> col=1 (右)。 错！把第二句放到了右边。
            # 
            # 后端修正逻辑：
            # col = idx // rows_per_col
            # idx=0 -> col=0 (左)。 对！
            
            for idx, img in enumerate(pil_images):
                col = idx // rows_per_col
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
