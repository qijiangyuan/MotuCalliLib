"""使用独立小型字库验证工作区事务、参数边界和真实像素排版。"""

import importlib
import io
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.env = patch.dict(
            os.environ,
            {
                "MOTU_DB_PATH": str(cls.root / "catalogue.db"),
                "MOTU_WORKSPACE_DB": str(cls.root / "workspace.db"),
                "MOTU_LOG_LEVEL": "error",
            },
        )
        cls.env.start()
        with sqlite3.connect(cls.root / "catalogue.db") as conn:
            conn.executescript("""
              CREATE TABLE fonts(id INTEGER PRIMARY KEY,name TEXT);
              CREATE TABLE authors(id INTEGER PRIMARY KEY,name TEXT);
              CREATE TABLE books(id INTEGER PRIMARY KEY,title TEXT);
              CREATE TABLE glyphs(id INTEGER PRIMARY KEY,han TEXT,font_id INT,author_id INT,book_id INT);
              CREATE TABLE images(id INTEGER PRIMARY KEY,glyph_id INT,url TEXT);
              INSERT INTO fonts VALUES(1,'楷书');
              INSERT INTO authors VALUES(1,'测试书家');
              INSERT INTO books VALUES(1,'测试典籍');
              INSERT INTO glyphs VALUES(1,'春',1,1,1),(2,'和',1,1,1),(3,'景',1,1,1),(4,'明',1,1,1);
              INSERT INTO images VALUES(1,1,'https://example.com/1.png'),(2,2,'https://example.com/2.png'),
              (3,3,'https://example.com/3.png'),(4,4,'https://example.com/4.png'),(5,1,'https://example.com/5.png');
            """)
        conn.close()
        cls.app = importlib.import_module("app_new").app
        cls.product = importlib.import_module("product")
        cls.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.client = self.app.test_client()
        with self.product.workspace() as conn:
            for table in ("works", "favorites", "feedback"):
                conn.execute(f"DELETE FROM {table}")

    def work(self):
        result = self.client.get(
            "/api/compose", query_string={"text": "春和景明"}
        ).get_json()
        return {
            "title": "测试作品",
            "text": result["text"],
            "characters": result["characters"],
            "direction": "vertical-right",
            "cols": 2,
            "size": 160,
            "gap": 0,
            "background": "paper",
        }

    def test_pages_render_without_external_assets(self):
        for route in (
            "/",
            "/library",
            "/calligraphy_set",
            "/works",
            "/settings",
            "/help",
        ):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, route)
            self.assertNotIn(b"cdnjs.cloudflare", response.data)
        self.assertEqual(self.client.get("/missing-page").status_code, 404)

    def test_exact_search_and_pagination(self):
        result = self.client.get("/api/catalogue?han=春和&per_page=1&page=2").get_json()
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["results"][0]["han"], "和")
        self.assertEqual(result["results"][0]["image_ids"], [2])
        self.assertEqual(
            self.client.get("/api/catalogue?author=missing").get_json()["total"], 0
        )

    def test_invalid_pagination_and_json(self):
        for suffix in ("page=x", "per_page=0", "per_page=100000", "page=-1"):
            self.assertEqual(
                self.client.get("/api/catalogue?" + suffix).status_code, 400
            )
        self.assertEqual(self.client.post("/api/works", json=[]).status_code, 400)
        self.assertEqual(
            self.client.post(
                "/api/works", data="broken", content_type="application/json"
            ).status_code,
            400,
        )

    def test_compose_normalization_missing_and_limit(self):
        result = self.client.get(
            "/api/compose", query_string={"text": "春，和。龘"}
        ).get_json()
        self.assertEqual(result["text"], "春和龘")
        self.assertEqual(result["missing"], ["龘"])
        self.assertEqual(
            self.client.get(
                "/api/compose", query_string={"text": "春" * 201}
            ).status_code,
            400,
        )
        self.assertEqual(self.client.get("/api/compose?text=123abc").status_code, 400)

    def test_save_update_reload_delete(self):
        response = self.client.post("/api/works", json=self.work())
        self.assertEqual(response.status_code, 201)
        work_id = response.get_json()["work"]["id"]
        # 新连接能读回，证明是持久化，而不是返回假成功。
        work = self.app.test_client().get(f"/api/works/{work_id}").get_json()["work"]
        self.assertEqual(work["size"], 160)
        self.assertEqual(work["background"], "paper")
        work["title"] = "更新后的作品"
        work["characters"][0]["image_id"] = 5
        self.assertEqual(
            self.client.put(f"/api/works/{work_id}", json=work).status_code, 200
        )
        updated = self.client.get(f"/api/works/{work_id}").get_json()["work"]
        self.assertEqual(updated["characters"][0]["image_id"], 5)
        self.assertEqual(
            len(self.client.get("/api/works?q=更新").get_json()["works"]), 1
        )
        self.assertEqual(self.client.delete(f"/api/works/{work_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/works/{work_id}").status_code, 404)

    def test_wrong_character_image_is_rejected(self):
        work = self.work()
        work["characters"][0]["image_id"] = 2
        self.assertEqual(self.client.post("/api/works", json=work).status_code, 400)
        self.assertEqual(self.client.get("/api/works").get_json()["works"], [])

    def test_favorites_are_idempotent(self):
        for _ in range(2):
            self.assertEqual(self.client.put("/api/favorites/1").status_code, 200)
        self.assertEqual(
            len(self.client.get("/api/favorites").get_json()["results"]), 1
        )
        self.assertEqual(self.client.put("/api/favorites/999").status_code, 404)
        self.client.delete("/api/favorites/1")
        self.assertEqual(self.client.get("/api/favorites").get_json()["results"], [])

    def test_feedback_lifecycle_and_validation(self):
        response = self.client.post(
            "/api/feedback", json={"image_id": 1, "reason": "测试核查记录"}
        )
        self.assertEqual(response.status_code, 201)
        report_id = response.get_json()["id"]
        self.assertEqual(
            self.client.patch(
                f"/api/feedback/{report_id}", json={"status": "reviewed"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/feedback").get_json()["reports"][0]["status"],
            "reviewed",
        )
        self.assertEqual(
            self.client.post(
                "/api/feedback", json={"image_id": 1, "reason": ""}
            ).status_code,
            400,
        )

    def test_restore_merges_deduplicates_and_is_atomic(self):
        self.client.post("/api/works", json=self.work())
        self.client.put("/api/favorites/1")
        self.client.post(
            "/api/feedback", json={"image_id": 1, "reason": "测试核查记录"}
        )
        backup = self.client.get("/api/backup").get_json()
        self.assertEqual(
            self.client.post("/api/restore", json=backup).get_json()["added"], 0
        )
        backup["works"][0]["title"] = "新增作品"
        backup["favorites"].append(999)
        self.assertEqual(self.client.post("/api/restore", json=backup).status_code, 400)
        self.assertEqual(len(self.client.get("/api/works").get_json()["works"]), 1)
        backup["favorites"].pop()
        self.assertEqual(
            self.client.post("/api/restore", json=backup).get_json()["added"], 1
        )
        self.assertEqual(len(self.client.get("/api/feedback").get_json()["reports"]), 1)

    def test_cross_origin_write_is_rejected(self):
        result = self.client.put(
            "/api/favorites/1", headers={"Origin": "https://example.com"}
        )
        self.assertEqual(result.status_code, 403)

    def test_export_four_directions_pixel_order(self):
        colors = {
            1: (255, 0, 0, 255),
            2: (0, 255, 0, 255),
            3: (0, 0, 255, 255),
            4: (255, 255, 0, 255),
        }

        def fixture(image_id):
            stream = io.BytesIO()
            Image.new("RGBA", (80, 80), colors[image_id]).save(stream, "PNG")
            return stream.getvalue()

        expected = {
            "horizontal": [1, 2, 3, 4],
            "horizontal-reverse": [2, 1, 4, 3],
            "vertical-left": [1, 3, 2, 4],
            "vertical-right": [3, 1, 4, 2],
        }
        with patch.object(self.product, "image_bytes", side_effect=fixture):
            for direction, ids in expected.items():
                response = self.client.post(
                    "/api/export",
                    json={
                        "image_ids": [1, 2, 3, 4],
                        "cols": 2,
                        "direction": direction,
                        "size": 80,
                        "gap": 0,
                    },
                )
                self.assertEqual(response.status_code, 200)
                img = Image.open(io.BytesIO(response.data))
                self.assertEqual(img.size, (160, 160))
                actual = [
                    img.getpixel(point)
                    for point in ((40, 40), (120, 40), (40, 120), (120, 120))
                ]
                self.assertEqual(actual, [colors[i] for i in ids], direction)

    def test_export_preserves_aspect_ratio(self):
        stream = io.BytesIO()
        Image.new("RGB", (160, 80), "black").save(stream, "PNG")
        with patch.object(self.product, "image_bytes", return_value=stream.getvalue()):
            response = self.client.post(
                "/api/export", json={"image_ids": [1], "size": 80, "gap": 0}
            )
        img = Image.open(io.BytesIO(response.data))
        self.assertEqual(img.getpixel((40, 5)), (255, 255, 255, 255))
        self.assertEqual(img.getpixel((40, 40)), (0, 0, 0, 255))

    def test_export_failure_and_limits(self):
        for data in (
            {"image_ids": [None]},
            {"image_ids": []},
            {"image_ids": [1], "cols": 0},
            {"image_ids": [1], "direction": "bad"},
            {"image_ids": [1] * 201},
        ):
            self.assertEqual(
                self.client.post("/api/export", json=data).status_code, 400
            )
        with patch.object(self.product, "image_bytes", side_effect=OSError("offline")):
            self.assertEqual(
                self.client.post("/api/export", json={"image_ids": [1]}).status_code,
                422,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
