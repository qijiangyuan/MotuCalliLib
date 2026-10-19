"""墨研书法的字典、作品、收藏与导出服务。

字库保持只读；个人作品和反馈保存在独立的工作库中。
"""

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import io
import json
import math
import os
import sqlite3
import threading

from flask import Blueprint, abort, jsonify, render_template, request, send_file
from PIL import Image, ImageOps
import requests

ROOT = Path(__file__).resolve().parent
INFO = json.loads((ROOT / "product_info.json").read_text(encoding="utf-8"))
DIRECTIONS = ("horizontal", "horizontal-reverse", "vertical-left", "vertical-right")
MAX_CHARS = 200
bp = Blueprint("product", __name__)
_stats_lock = threading.Lock()
_stats_cache = None
_app = None


@contextmanager
def catalogue():
    path = Path(_app.config["CATALOGUE_DB"]).resolve()
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def workspace():
    conn = sqlite3.connect(_app.config["WORKSPACE_DB"], timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def integer(value, name, minimum=1, maximum=100):
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValueError(f"{name}必须为整数")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{name}须在 {minimum} 至 {maximum} 之间")
    return number


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("请提交有效的 JSON 对象")
    return data


def text_field(data, key, limit, default=""):
    value = data.get(key, default)
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"{key}须为不超过 {limit} 个字符的文字")
    return value.strip()


def is_han(char):
    n = ord(char)
    return (
        0x3400 <= n <= 0x4DBF
        or 0x4E00 <= n <= 0x9FFF
        or 0xF900 <= n <= 0xFAFF
        or 0x20000 <= n <= 0x323AF
    )


def composition_text(value):
    if not isinstance(value, str) or not value or len(value) > 1000:
        raise ValueError("请输入 1 至 200 个汉字")
    result = "".join(c for c in value if is_han(c))
    if not result or len(result) > MAX_CHARS:
        raise ValueError("集字内容须为 1 至 200 个汉字")
    return result


def glyph_dict(conn, row, all_images=False):
    result = dict(row)
    limit = "" if all_images else " LIMIT 1"
    images = conn.execute(
        "SELECT id FROM images WHERE glyph_id=? ORDER BY id" + limit, (result["id"],)
    ).fetchall()
    result["image_ids"] = [r["id"] for r in images]
    result["image_urls"] = [f"/media/{r['id']}" for r in images]
    result["image_count"] = conn.execute(
        "SELECT COUNT(*) FROM images WHERE glyph_id=?", (result["id"],)
    ).fetchone()[0]
    return result


GLYPH_SELECT = """SELECT g.id,g.han,f.name AS font,a.name AS author,b.title AS book_title
FROM glyphs g LEFT JOIN fonts f ON g.font_id=f.id
LEFT JOIN authors a ON g.author_id=a.id LEFT JOIN books b ON g.book_id=b.id"""


@bp.get("/api/catalogue")
def search_catalogue():
    args = request.args
    page = integer(args.get("page", 1), "页码", 1, 100000)
    size = integer(args.get("per_page", 24), "每页条数", 1, 60)
    han = text_field(args, "han", 200)
    where, values = [], []
    if han:
        chars = list(dict.fromkeys(c for c in han if not c.isspace()))
        where.append("g.han IN (" + ",".join("?" for _ in chars) + ")")
        values.extend(chars)
    for key, column in (("font", "f.name"), ("author", "a.name"), ("book", "b.title")):
        value = text_field(args, key, 200)
        if value:
            where.append(column + "=?")
            values.append(value)
    clause = " WHERE " + " AND ".join(where) if where else ""
    with catalogue() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM (" + GLYPH_SELECT + clause + ")", values
        ).fetchone()[0]
        rows = conn.execute(
            GLYPH_SELECT + clause + " ORDER BY g.id LIMIT ? OFFSET ?",
            values + [size, (page - 1) * size],
        ).fetchall()
        results = [glyph_dict(conn, row) for row in rows]
    return jsonify(
        results=results,
        total=total,
        page=page,
        per_page=size,
        pages=math.ceil(total / size),
    )


@bp.get("/api/glyphs/<int:glyph_id>")
def glyph_detail(glyph_id):
    with catalogue() as conn:
        row = conn.execute(GLYPH_SELECT + " WHERE g.id=?", (glyph_id,)).fetchone()
        if row is None:
            abort(404, description="未找到该字形")
        result = glyph_dict(conn, row, all_images=True)
    return jsonify(result)


@bp.get("/api/statistics")
def statistics():
    global _stats_cache
    with _stats_lock:
        if _stats_cache is None:
            with catalogue() as conn:
                _stats_cache = {
                    table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("glyphs", "images", "authors", "books", "fonts")
                }
                _stats_cache["characters"] = conn.execute(
                    "SELECT COUNT(DISTINCT han) FROM glyphs"
                ).fetchone()[0]
    result = dict(_stats_cache)
    with workspace() as conn:
        result["works"] = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        result["favorites"] = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[
            0
        ]
    result["software"] = INFO
    return jsonify(result)


@bp.get("/api/compose")
def compose():
    text = composition_text(request.args.get("text", ""))
    conditions, values = [], []
    for key, column in (
        ("font", "f.name"),
        ("calligrapher", "a.name"),
        ("book", "b.title"),
    ):
        value = text_field(request.args, key, 200)
        if value:
            conditions.append(column + "=?")
            values.append(value)
    extra = " AND " + " AND ".join(conditions) if conditions else ""
    by_char = {}
    with catalogue() as conn:
        for char in dict.fromkeys(text):
            row = conn.execute(
                GLYPH_SELECT
                + " WHERE g.han=?"
                + extra
                + " AND EXISTS(SELECT 1 FROM images i WHERE i.glyph_id=g.id)"
                + " ORDER BY g.id LIMIT 1",
                [char] + values,
            ).fetchone()
            if row:
                item = glyph_dict(conn, row)
                by_char[char] = {
                    **item,
                    "glyph_id": item["id"],
                    "image_id": item["image_ids"][0],
                }
            else:
                by_char[char] = {
                    "han": char,
                    "glyph_id": None,
                    "image_id": None,
                    "image_ids": [],
                    "image_urls": [],
                }
    characters = [by_char[c] for c in text]
    return jsonify(
        success=True,
        text=text,
        characters=characters,
        missing=[c for c in dict.fromkeys(text) if not by_char[c]["image_id"]],
    )


def validate_work(data):
    text = composition_text(data.get("text"))
    title = text_field(data, "title", 60, text[:20]) or text[:20]
    direction = data.get("direction", "horizontal")
    if direction not in DIRECTIONS:
        raise ValueError("不支持的排列方式")
    cols = integer(data.get("cols", 5), "单行字数", 1, 20)
    choices = data.get("characters")
    if not isinstance(choices, list) or len(choices) != len(text):
        raise ValueError("选字数量与作品文字不一致，请重新生成")
    normalized = []
    with catalogue() as conn:
        for char, choice in zip(text, choices):
            if not isinstance(choice, dict) or choice.get("han") != char:
                raise ValueError("作品选字与原文不一致")
            image_id = choice.get("image_id")
            if image_id is None:
                normalized.append({"han": char, "image_id": None, "glyph_id": None})
                continue
            image_id = integer(image_id, "图片编号", 1, 2147483647)
            row = conn.execute(
                GLYPH_SELECT
                + " JOIN images i ON i.glyph_id=g.id"
                + " WHERE i.id=? AND g.han=?",
                (image_id, char),
            ).fetchone()
            if row is None:
                raise ValueError(f"{char}的图片不存在或不属于该汉字")
            normalized.append(
                {**dict(row), "glyph_id": row["id"], "image_id": image_id}
            )
    filters = {
        key: text_field(
            (
                data.get("filters", {})
                if isinstance(data.get("filters", {}), dict)
                else {}
            ),
            key,
            200,
        )
        for key in ("font", "calligrapher", "book")
    }
    size = integer(data.get("size", 240), "字格尺寸", 80, 400)
    gap = integer(data.get("gap", 12), "字格间距", 0, 60)
    background = data.get("background", "white")
    if background not in ("white", "paper", "transparent"):
        raise ValueError("不支持的背景")
    return {
        "text": text,
        "title": title,
        "direction": direction,
        "cols": cols,
        "characters": normalized,
        "filters": filters,
        "size": size,
        "gap": gap,
        "background": background,
    }


def work_row(row):
    return {
        **json.loads(row["content"]),
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@bp.get("/api/works")
def list_works():
    query = text_field(request.args, "q", 100)
    with workspace() as conn:
        rows = conn.execute(
            "SELECT * FROM works ORDER BY updated_at DESC,id DESC"
        ).fetchall()
    works = [work_row(row) for row in rows]
    return jsonify(
        works=[w for w in works if query in w["title"] or query in w["text"]]
    )


@bp.post("/api/works")
def create_work():
    content = validate_work(payload())
    with workspace() as conn:
        cur = conn.execute(
            "INSERT INTO works(content) VALUES (?)",
            (json.dumps(content, ensure_ascii=False),),
        )
        row = conn.execute(
            "SELECT * FROM works WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return jsonify(success=True, work=work_row(row), message="作品已保存"), 201


@bp.route("/api/works/<int:work_id>", methods=["GET", "PUT", "DELETE"])
def work_detail(work_id):
    content = validate_work(payload()) if request.method == "PUT" else None
    with workspace() as conn:
        row = conn.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
        if row is None:
            abort(404, description="作品不存在或已删除")
        if request.method == "DELETE":
            conn.execute("DELETE FROM works WHERE id=?", (work_id,))
            return jsonify(success=True)
        if content:
            conn.execute(
                "UPDATE works SET content=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
                + " WHERE id=?",
                (json.dumps(content, ensure_ascii=False), work_id),
            )
            row = conn.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
    return jsonify(success=True, work=work_row(row))


@bp.get("/api/favorites")
def favorites():
    with workspace() as conn:
        ids = [
            r[0]
            for r in conn.execute(
                "SELECT glyph_id FROM favorites ORDER BY created_at DESC"
            )
        ]
    items = []
    with catalogue() as conn:
        for glyph_id in ids:
            row = conn.execute(GLYPH_SELECT + " WHERE g.id=?", (glyph_id,)).fetchone()
            if row:
                items.append(glyph_dict(conn, row))
    return jsonify(results=items)


@bp.route("/api/favorites/<int:glyph_id>", methods=["PUT", "DELETE"])
def favorite(glyph_id):
    if request.method == "PUT":
        with catalogue() as conn:
            if not conn.execute(
                "SELECT id FROM glyphs WHERE id=?", (glyph_id,)
            ).fetchone():
                abort(404, description="字形不存在")
        with workspace() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO favorites(glyph_id) VALUES (?)", (glyph_id,)
            )
    else:
        with workspace() as conn:
            conn.execute("DELETE FROM favorites WHERE glyph_id=?", (glyph_id,))
    return jsonify(success=True)


@bp.route("/api/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "GET":
        with workspace() as conn:
            rows = conn.execute(
                "SELECT * FROM feedback ORDER BY id DESC LIMIT 200"
            ).fetchall()
        return jsonify(reports=[dict(row) for row in rows])
    data = payload()
    image_id = integer(data.get("image_id"), "图片编号", 1, 2147483647)
    reason = text_field(data, "reason", 500)
    if len(reason) < 2:
        raise ValueError("请填写至少 2 个字的纠错说明")
    with catalogue() as conn:
        row = conn.execute(
            "SELECT g.id,g.han FROM glyphs g JOIN images i ON g.id=i.glyph_id"
            + " WHERE i.id=?",
            (image_id,),
        ).fetchone()
        if row is None:
            abort(404, description="图片不存在")
    with workspace() as conn:
        cur = conn.execute(
            "INSERT INTO feedback(glyph_id,image_id,han,reason) VALUES (?,?,?,?)",
            (row["id"], image_id, row["han"], reason),
        )
    return jsonify(success=True, id=cur.lastrowid, message="纠错记录已保存"), 201


@bp.patch("/api/feedback/<int:report_id>")
def update_feedback(report_id):
    status = payload().get("status")
    if status not in ("pending", "reviewed"):
        raise ValueError("无效的处理状态")
    with workspace() as conn:
        if not conn.execute(
            "UPDATE feedback SET status=? WHERE id=?", (status, report_id)
        ).rowcount:
            abort(404, description="记录不存在")
    return jsonify(success=True)


@bp.get("/api/backup")
def backup():
    with workspace() as conn:
        data = {
            "format": "motu-workspace",
            "schema_version": 1,
            "software": INFO["name"],
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "works": [
                work_row(row) for row in conn.execute("SELECT * FROM works ORDER BY id")
            ],
            "favorites": [r[0] for r in conn.execute("SELECT glyph_id FROM favorites")],
            "feedback": [
                dict(r) for r in conn.execute("SELECT * FROM feedback ORDER BY id")
            ],
        }
    stream = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    return send_file(
        stream,
        mimetype="application/json",
        as_attachment=True,
        download_name="moyan-workspace-backup.json",
    )


@bp.post("/api/restore")
def restore():
    data = payload()
    if data.get("format") != "motu-workspace" or data.get("schema_version") != 1:
        raise ValueError("不是受支持的墨研工作区备份")
    works, favs, reports = (
        data.get("works"),
        data.get("favorites"),
        data.get("feedback", []),
    )
    if (
        not isinstance(works, list)
        or len(works) > 1000
        or not isinstance(favs, list)
        or len(favs) > 5000
        or not isinstance(reports, list)
        or len(reports) > 5000
    ):
        raise ValueError("备份格式或条目数量无效")
    normalized = [
        json.dumps(validate_work(w), ensure_ascii=False)
        for w in works
        if isinstance(w, dict)
    ]
    if len(normalized) != len(works):
        raise ValueError("备份中的作品格式无效")
    checked_favs = []
    checked_reports = []
    with catalogue() as conn:
        for item in favs:
            item = integer(item, "收藏编号", 1, 2147483647)
            if not conn.execute("SELECT id FROM glyphs WHERE id=?", (item,)).fetchone():
                raise ValueError("备份引用了当前字库中不存在的收藏")
            checked_favs.append(item)
        for item in reports:
            if not isinstance(item, dict):
                raise ValueError("纠错记录格式无效")
            iid = integer(item.get("image_id"), "图片编号", 1, 2147483647)
            row = conn.execute(
                "SELECT g.id,g.han FROM glyphs g JOIN images i ON g.id=i.glyph_id"
                + " WHERE i.id=?",
                (iid,),
            ).fetchone()
            reason = text_field(item, "reason", 500)
            status = item.get("status", "pending")
            if not row or len(reason) < 2 or status not in ("pending", "reviewed"):
                raise ValueError("备份中的纠错记录无效")
            checked_reports.append((row["id"], iid, row["han"], reason, status))
    added = 0
    with workspace() as conn:
        existing = {r[0] for r in conn.execute("SELECT content FROM works")}
        for content in normalized:
            if content not in existing:
                conn.execute("INSERT INTO works(content) VALUES (?)", (content,))
                existing.add(content)
                added += 1
        conn.executemany(
            "INSERT OR IGNORE INTO favorites(glyph_id) VALUES (?)",
            [(i,) for i in checked_favs],
        )
        for report in checked_reports:
            if not conn.execute(
                "SELECT id FROM feedback WHERE image_id=? AND reason=?",
                (report[1], report[3]),
            ).fetchone():
                conn.execute(
                    "INSERT INTO feedback(glyph_id,image_id,han,reason,status) VALUES (?,?,?,?,?)",
                    report,
                )
    return jsonify(
        success=True,
        added=added,
        message=f"恢复完成，新增 {added} 件作品，已有内容保留",
    )


@lru_cache(maxsize=128)
def image_bytes(image_id):
    """只按字库内编号读取图像，不接受客户端任意远程 URL。"""
    with catalogue() as conn:
        row = conn.execute("SELECT url FROM images WHERE id=?", (image_id,)).fetchone()
    if row is None:
        raise ValueError("图片不存在")
    local_dir = _app.config["LOCAL_IMAGE_DIR"]
    if _app.config["USE_LOCAL_IMAGES"]:
        for ext in (".jpg", ".png", ".jpeg", ".webp", ".bmp"):
            path = Path(local_dir) / f"{image_id}{ext}"
            if path.is_file():
                raw = path.read_bytes()
                break
        else:
            raw = None
    else:
        raw = None
    if raw is None:
        from urllib.parse import urlsplit

        if urlsplit(row["url"]).scheme not in ("https", "http"):
            raise ValueError("图片地址协议不受支持")
        with requests.get(row["url"], timeout=(4, 12), stream=True) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > 8 * 1024 * 1024:
                    raise ValueError("图片文件超过大小限制")
            raw = bytes(data)
    with Image.open(io.BytesIO(raw)) as img:
        if img.width * img.height > 20000000:
            raise ValueError("图片尺寸超过限制")
        img.load()
        result = io.BytesIO()
        img.convert("RGBA").save(result, "PNG")
    return result.getvalue()


@bp.get("/media/<int:image_id>")
def media(image_id):
    try:
        return send_file(
            io.BytesIO(image_bytes(image_id)), mimetype="image/png", max_age=3600
        )
    except (ValueError, requests.RequestException, OSError):
        abort(404, description="原始图片暂不可用，请选择其他字形或检查图片源连接")


def layout_position(index, count, cols, direction):
    if direction.startswith("vertical"):
        column, row = divmod(index, cols)
        if direction == "vertical-right":
            column = math.ceil(count / cols) - 1 - column
    else:
        row, column = divmod(index, cols)
        if direction == "horizontal-reverse":
            column = min(cols, count) - 1 - column
    return column, row


@bp.post("/api/export")
def export_work():
    data = payload()
    ids = data.get("image_ids")
    if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_CHARS:
        raise ValueError("导出须包含 1 至 200 张字形图片")
    if any(i is None or i == "placeholder" for i in ids):
        raise ValueError("作品存在缺字，请完成选字后导出")
    ids = [integer(i, "图片编号", 1, 2147483647) for i in ids]
    cols = integer(data.get("cols", 5), "单行字数", 1, 20)
    size = integer(data.get("size", 240), "字格尺寸", 80, 400)
    gap = integer(data.get("gap", 12), "字格间距", 0, 60)
    direction = data.get("direction", "horizontal")
    if direction not in DIRECTIONS:
        raise ValueError("不支持的排列方式")
    background = data.get("background", "white")
    if background not in ("white", "paper", "transparent"):
        raise ValueError("不支持的背景")
    across, down = min(cols, len(ids)), math.ceil(len(ids) / cols)
    if direction.startswith("vertical"):
        across, down = down, across
    width, height = across * (size + gap) + gap, down * (size + gap) + gap
    if width * height > 36000000:
        raise ValueError("输出图片过大，请减少文字或字格尺寸")
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            raw_images = list(pool.map(image_bytes, ids))
    except (ValueError, requests.RequestException, OSError):
        return (
            jsonify(success=False, message="部分原始图片无法读取，请重新选字后导出"),
            422,
        )
    color = {"white": "#ffffff", "paper": "#f4eedf", "transparent": (255, 255, 255, 0)}[
        background
    ]
    output = Image.new("RGBA", (width, height), color)
    for index, raw in enumerate(raw_images):
        with Image.open(io.BytesIO(raw)) as original:
            img = ImageOps.contain(
                original.convert("RGBA"), (size, size), Image.Resampling.LANCZOS
            )
        col, row = layout_position(index, len(ids), cols, direction)
        x = gap + col * (size + gap) + (size - img.width) // 2
        y = gap + row * (size + gap) + (size - img.height) // 2
        output.alpha_composite(img, (x, y))
    stream = io.BytesIO()
    output.save(stream, "PNG", dpi=(300, 300))
    stream.seek(0)
    return send_file(
        stream,
        mimetype="image/png",
        as_attachment=True,
        download_name="moyan-calligraphy.png",
    )


@bp.get("/works")
def works_page():
    return render_template("works.html", page="works")


@bp.get("/help")
def help_page():
    return render_template("help.html", page="help")


def init_product(app):
    global _app
    _app = app
    app.config.update(
        CATALOGUE_DB=os.getenv("MOTU_DB_PATH", str(ROOT / "data" / "shufadb.db")),
        WORKSPACE_DB=os.getenv(
            "MOTU_WORKSPACE_DB", str(ROOT / "data" / "workspace.db")
        ),
        LOCAL_IMAGE_DIR=os.getenv("LOCAL_IMAGE_DIR", str(ROOT / "data" / "images")),
        USE_LOCAL_IMAGES=os.getenv("USE_LOCAL_IMAGES", "false").lower() == "true",
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    Path(app.config["WORKSPACE_DB"]).parent.mkdir(parents=True, exist_ok=True)
    with workspace() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS works (
          id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
        CREATE TABLE IF NOT EXISTS favorites (
          glyph_id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT, glyph_id INTEGER NOT NULL,
          image_id INTEGER NOT NULL, han TEXT NOT NULL, reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
    app.register_blueprint(bp)
    app.context_processor(lambda: {"software": INFO})

    @app.errorhandler(ValueError)
    def invalid_request(error):
        return jsonify(success=False, message=str(error)), 400

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(success=False, message="提交内容超过 8 MB 限制"), 413

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith(("/api/", "/media/")):
            return jsonify(success=False, message=str(error.description)), 404
        return (
            render_template("error.html", page="", message="页面不存在", code=404),
            404,
        )

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        app.logger.error("Database failure: %s", error)
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    success=False, message="数据暂不可用，请检查字库配置或稍后重试"
                ),
                503,
            )
        return (
            render_template("error.html", page="", message="字库暂不可用", code=503),
            503,
        )

    @app.before_request
    def same_origin_writes():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            from urllib.parse import urlsplit

            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                return jsonify(success=False, message="不允许跨站修改工作区"), 403
