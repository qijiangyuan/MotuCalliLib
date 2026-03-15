
import os
import sqlite3
import threading
import time
import json
import logging
import traceback
import tempfile
from flask import Flask, render_template, jsonify, request
import requests
import random
from io import BytesIO
from PIL import Image
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    import torch
    HAS_MODEL_LIB = True
except ImportError:
    HAS_MODEL_LIB = False
    print("Warning: transformers or torch not installed. Using mock model.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CalligraphyChecker")

import threading
import time
import json
import logging
import queue
from flask import Flask, render_template, jsonify, request
import requests
import random
from io import BytesIO
from PIL import Image

# ... (imports remain the same)

# Configuration
SHUFA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "shufadb.db")
FEEDBACK_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "feedback.db")
CHECK_POINT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checker_checkpoint.json")
CHECK_INTERVAL = 0.05  # Reduced simulation time
NUM_THREADS = int(os.getenv("CHECKER_NUM_THREADS", "16"))

app = Flask(__name__, template_folder="templates")

class ChineseCalligraphyRecognitionV1:
    def __init__(self, progress_callback=None):
        self.device = "cpu"
        self.mock = True
        self.model_name = None
        self.load_error = ""
        self.progress_callback = progress_callback
        self.backend_requested = os.getenv("CHECKER_OCR_BACKEND", "trocr").strip().lower()
        self.backend_active = "mock"
        if not HAS_MODEL_LIB:
            self.load_error = "transformers or torch not installed"
            return
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.backend_requested in ("callireader", "auto"):
            ok, err = self._init_callireader()
            if ok:
                return
            self.load_error = err
            if self.backend_requested == "callireader":
                return
        ok, err = self._init_trocr()
        if ok:
            return
        if self.load_error:
            self.load_error = f"{self.load_error}; trocr: {err}"
        else:
            self.load_error = f"trocr: {err}"

    def _init_trocr(self):
        candidate = os.getenv("CHECKER_MODEL_NAME", "ZihCiLin/trocr-traditional-chinese-historical-finetune")
        try:
            self.processor = TrOCRProcessor.from_pretrained(candidate, local_files_only=True)
            self.model = VisionEncoderDecoderModel.from_pretrained(candidate, local_files_only=True)
            self.model.to(self.device)
            self.model_name = candidate
            self.backend_active = "trocr"
            self.mock = False
            self.load_error = ""
            return True, ""
        except Exception as e:
            return False, f"{e}\n{traceback.format_exc()}"

    def _init_callireader(self):
        try:
            from transformers import AutoModel, AutoTokenizer
            from ultralytics import YOLO
        except Exception as e:
            return False, f"callireader deps missing: {e}"
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_dir = os.getenv("CHECKER_CALLIREADER_DIR", os.path.join(project_root, "data", "models", "CalliReader"))
        required_paths = [
            os.path.join(base_dir, "inference.py"),
            os.path.join(base_dir, "models", "model.py"),
            os.path.join(base_dir, "config", "configu.py"),
            os.path.join(base_dir, "InternVL", "config.json"),
            os.path.join(base_dir, "InternVL", "preprocessor_config.json"),
            os.path.join(base_dir, "InternVL", "model-00001-of-00004.safetensors"),
            os.path.join(base_dir, "InternVL", "model-00002-of-00004.safetensors"),
            os.path.join(base_dir, "InternVL", "model-00003-of-00004.safetensors"),
            os.path.join(base_dir, "InternVL", "model-00004-of-00004.safetensors"),
            os.path.join(base_dir, "params", "best.pt")
        ]
        missing = [p for p in required_paths if not os.path.exists(p)]
        if missing:
            missing_rel = [os.path.relpath(p, base_dir) for p in missing]
            return False, f"callireader files missing ({len(missing_rel)}): {', '.join(missing_rel)}"
        internvl_path = os.path.join(base_dir, "InternVL")
        yolo_checkpoint = os.path.join(base_dir, "params", "best.pt")
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        try:
            self.callireader_model = AutoModel.from_pretrained(
                internvl_path,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
                _fast_init=False,
                trust_remote_code=True,
                load_in_4bit=True,
                device_map='auto',
                # llm_int8_enable_fp32_cpu_offload=True
            ).eval()
            # if self.device == "cuda":
            #     self.callireader_model = self.callireader_model.cuda()
            # else:
            #     self.callireader_model = self.callireader_model.to("cpu")
            self.callireader_tokenizer = AutoTokenizer.from_pretrained(internvl_path, trust_remote_code=True)
            self.callireader_detector = YOLO(yolo_checkpoint)
            self.callireader_generation_config = {
                "num_beams": 1,
                "max_new_tokens": 1024,
                "do_sample": False
            }
            self.callireader_prompt = os.getenv("CHECKER_CALLIREADER_PROMPT", "这幅书法作品内容是什么？")
            self.model_name = "gtang666/CalliReader"
            self.backend_active = "callireader"
            self.mock = False
            self.load_error = ""
            return True, ""
        except Exception as e:
            return False, f"{e}\n{traceback.format_exc()}"

    def predict(self, image_url, expected_char):
        if self.mock:
            time.sleep(0.02)
            r = random.random()
            if r > 0.05:
                return expected_char, random.uniform(0.8, 0.99), True
            return "X", random.uniform(0.3, 0.7), False
        if self.backend_active == "callireader":
            return self._predict_callireader(image_url, expected_char)
        try:
            if image_url.startswith("/static/"):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                local_path = os.path.join(project_root, image_url.lstrip("/"))
                image = Image.open(local_path).convert("RGB")
            elif image_url.startswith("http"):
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert("RGB")
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                local_path = os.path.join(project_root, image_url.lstrip("/"))
                if not os.path.exists(local_path):
                    return "Error", 0.0, False
                image = Image.open(local_path).convert("RGB")

            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.to(self.device)
            outputs = self.model.generate(
                pixel_values,
                return_dict_in_generate=True,
                output_scores=True,
                max_new_tokens=5
            )
            generated_ids = outputs.sequences
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            confidence = 1.0
            if outputs.scores:
                probs = []
                for i, score_tensor in enumerate(outputs.scores):
                    probs_step = torch.nn.functional.softmax(score_tensor, dim=-1)
                    if i + 1 < generated_ids.shape[1]:
                        token_id = generated_ids[0, i + 1]
                        token_prob = probs_step[0, token_id].item()
                        probs.append(token_prob)
                if probs:
                    confidence = sum(probs) / len(probs)
            predicted_char = generated_text.strip()
            is_match = predicted_char == expected_char
            return predicted_char, confidence, is_match
        except Exception:
            return "Error", 0.0, False

    def _predict_callireader(self, image_url, expected_char):
        try:
            if image_url.startswith("http"):
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                    f.write(response.content)
                    image_path = f.name
            elif image_url.startswith("/static/"):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                image_path = os.path.join(project_root, image_url.lstrip("/"))
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                image_path = os.path.join(project_root, image_url.lstrip("/"))
            result, _ = self.callireader_model.chat_ocr(
                self.callireader_tokenizer,
                self.callireader_detector,
                image_path,
                self.callireader_prompt,
                self.callireader_generation_config,
                use_p=True,
                hard_vq=False,
                drop_zero=True,
                repetition_penalty=1.2,
                return_history=True,
                verbose=False
            )
            predicted_text = (result or "").strip().replace(" ", "")
            is_match = expected_char in predicted_text
            predicted_char = expected_char if is_match else (predicted_text[:1] if predicted_text else "Error")
            confidence = 0.92 if is_match else (0.45 if predicted_text else 0.0)
            return predicted_char, confidence, is_match
        except Exception:
            return "Error", 0.0, False

class CheckerService:
    def __init__(self):
        self.is_running = False
        self.workers = []
        self.queue = queue.Queue(maxsize=100) # Task queue
        self.stats = {
            "total": 0,
            "processed": 0,
            "mismatches": 0,
            "errors": 0,
            "current_image": None,
            "current_image_id": None,
            "status": "stopped",
            "last_processed_id": 0,
            "logs": [],
            "model_download_model": "",
            "model_download_file": "",
            "model_download_percent": 0.0,
            "model_backend_requested": "",
            "model_backend_active": ""
        }
        self.stats_lock = threading.Lock()
        self.db_lock = threading.Lock()
        self.model = None
        self.model_lock = threading.Lock()
        self.last_start_error = ""
        self._last_progress_log_percent = -1
        
        # Load checkpoint but FORCE STOPPED STATUS
        self._load_checkpoint()
        self.stats["status"] = "stopped"
        self.is_running = False

    def add_log(self, msg):
        """Thread-safe logging to stats"""
        with self.stats_lock:
            # Keep only last 50 logs
            if len(self.stats["logs"]) > 50:
                self.stats["logs"].pop(0)
            self.stats["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        logger.info(msg) # Also log to console

    def on_model_progress(self, model_name, file_desc, percent):
        with self.stats_lock:
            self.stats["model_download_model"] = model_name
            self.stats["model_download_file"] = file_desc or ""
            self.stats["model_download_percent"] = round(float(percent), 1)
        p = int(percent)
        if p >= self._last_progress_log_percent + 5:
            self._last_progress_log_percent = p
            file_part = f" {file_desc}" if file_desc else ""
            self.add_log(f"Model download [{model_name}]{file_part}: {percent:.1f}%")

    def _load_checkpoint(self):
        if os.path.exists(CHECK_POINT_FILE):
            try:
                with open(CHECK_POINT_FILE, 'r') as f:
                    data = json.load(f)
                    self.stats["last_processed_id"] = data.get("last_processed_id", 0)
                    self.stats["processed"] = data.get("processed", 0)
                    self.stats["mismatches"] = data.get("mismatches", 0)
                    self.stats["errors"] = data.get("errors", 0)
                    # Don't load status from checkpoint, force stop
                    self.stats["status"] = "stopped" 
                    logger.info(f"Loaded checkpoint: last_processed_id={self.stats['last_processed_id']}")
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")

    def _save_checkpoint(self):
        try:
            with open(CHECK_POINT_FILE, 'w') as f:
                json.dump({
                    "last_processed_id": self.stats["last_processed_id"],
                    "processed": self.stats["processed"],
                    "mismatches": self.stats["mismatches"],
                    "errors": self.stats["errors"]
                    # Don't save status, or save as stopped
                }, f)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def start(self):
        if self.is_running:
            return False
        self.last_start_error = ""
        self._last_progress_log_percent = -1
        self.is_running = True
        self.stats["status"] = "running"
        self.stats["model_download_model"] = ""
        self.stats["model_download_file"] = ""
        self.stats["model_download_percent"] = 0.0
        self.stats["model_backend_requested"] = ""
        self.stats["model_backend_active"] = ""
        self.add_log("Service started. Initializing model in main thread...")
        
        # Initialize model in main thread (blocking for first time)
        with self.model_lock:
             if not self.model:
                 try:
                     self.add_log("Loading model... (This might freeze for a while)")
                     self.model = ChineseCalligraphyRecognitionV1(progress_callback=self.on_model_progress)
                     self.stats["model_backend_requested"] = self.model.backend_requested
                     self.stats["model_backend_active"] = self.model.backend_active
                     if self.model.mock:
                         self.add_log(f"Model backend request: {self.model.backend_requested}, active: mock")
                         self.add_log(f"Model unavailable, switched to mock mode. {self.model.load_error}")
                     else:
                         self.add_log(f"Model backend request: {self.model.backend_requested}, active: {self.model.backend_active}")
                         self.add_log(f"Model loaded successfully on {self.model.device} ({self.model.model_name})")
                 except Exception as e:
                     self.add_log(f"Model load FAILED: {e}")
                     self.last_start_error = str(e)
                     self.is_running = False
                     self.stats["status"] = "error"
                     return False
        
        # Start producer thread
        self.add_log("Starting producer thread...")
        self.producer_thread = threading.Thread(target=self._run_producer)
        self.producer_thread.daemon = True
        self.producer_thread.start()
        
        # Start worker threads
        self.add_log(f"Starting {NUM_THREADS} worker threads...")
        self.workers = []
        for i in range(NUM_THREADS):
            t = threading.Thread(target=self._run_worker, args=(i,))
            t.daemon = True
            t.start()
            self.workers.append(t)
            
        return True

    def stop(self):
        self.is_running = False
        self.stats["status"] = "stopping"
        self._save_checkpoint()

    def _run_producer(self):
        """Reads images from DB and puts into queue"""
        try:
            conn = sqlite3.connect(SHUFA_DB_PATH, timeout=60)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count (approximate)
            cursor.execute("SELECT COUNT(*) FROM images WHERE id > ?", (self.stats.get("last_processed_id", 0),))
            remaining = cursor.fetchone()[0]
            with self.stats_lock:
                 # total = processed so far + remaining
                 self.stats["total"] = self.stats["processed"] + remaining

            query = """
                SELECT i.id as image_id, i.url, i.glyph_id, g.han, 
                       f.name as font, a.name as author, b.title as book_title 
                FROM images i
                JOIN glyphs g ON i.glyph_id = g.id
                LEFT JOIN fonts f ON g.font_id = f.id
                LEFT JOIN authors a ON g.author_id = a.id
                LEFT JOIN books b ON g.book_id = b.id
                WHERE i.id > ?
                ORDER BY i.id ASC
            """
            
            cursor.execute(query, (self.stats.get("last_processed_id", 0),))
            
            while self.is_running:
                row = cursor.fetchone()
                if not row:
                    break
                
                # Put task into queue (blocking if full)
                while self.is_running:
                    try:
                        self.queue.put(dict(row), timeout=1)
                        # logger.info(f"Task queued: {row['image_id']}") # Debug
                        break
                    except queue.Full:
                        # logger.debug("Queue full, waiting...") # Debug
                        time.sleep(0.1) # Add sleep to avoid busy waiting
                        continue
                
                if not self.is_running:
                    break
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Producer error: {e}")
            self.stop()

    def _run_worker(self, worker_id):
        """Worker thread to process images"""
        # Ensure model is loaded (already loaded in start, just check here)
        self.add_log(f"Worker {worker_id} started.")
        
        # Connect to feedback DB per thread
        try:
            feedback_conn = sqlite3.connect(FEEDBACK_DB_PATH, timeout=60)
        except Exception as e:
            self.add_log(f"Worker {worker_id} failed to connect to DB: {e}")
            return

        while self.is_running:
            try:
                try:
                    image_data = self.queue.get(timeout=1)
                except queue.Empty:
                    # If producer finished and queue empty, we are done? 
                    # For now just loop check is_running
                    continue
                
                # self.add_log(f"Worker {worker_id} processing {image_data['image_id']}") # Reduce log spam
                
                # Update current status
                with self.stats_lock:
                    self.stats["current_image"] = image_data["url"]
                    self.stats["current_image_id"] = image_data["image_id"]
                
                # Process
                try:
                    if self.model and self.model.mock:
                        predicted, conf, is_match = self.model.predict(image_data["url"], image_data["han"])
                    else:
                        with self.model_lock:
                            predicted, conf, is_match = self.model.predict(image_data["url"], image_data["han"])
                    
                    if not is_match or conf < 0.6:
                         with self.stats_lock:
                             self.stats["mismatches"] += 1
                         
                         reason = f"conf: {conf:.2f}" # Simplified reason
                         if predicted != image_data["han"]:
                             reason = f"Rec: {predicted} (conf: {conf:.2f})"

                         # Write to DB (with local connection)
                         # Use retry logic
                         for _ in range(3):
                            try:
                                with self.db_lock: # Optional extra safety
                                    feedback_conn.execute("INSERT INTO reports (glyph_id, image_id, han, font, author, book_title, image_url, reason, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')", 
                                        (image_data["glyph_id"], image_data["image_id"], image_data["han"], image_data["font"], image_data["author"], image_data["book_title"], image_data["url"], reason))
                                    feedback_conn.commit()
                                break
                            except sqlite3.OperationalError:
                                time.sleep(0.5)
                
                except Exception as e:
                    with self.stats_lock:
                        self.stats["errors"] += 1
                    logger.error(f"Worker {worker_id} error: {e}")

                # Update stats
                with self.stats_lock:
                    self.stats["processed"] += 1
                    if image_data["image_id"] > self.stats["last_processed_id"]:
                        self.stats["last_processed_id"] = image_data["image_id"]
                
                # Save checkpoint periodically
                if self.stats["processed"] % 20 == 0:
                    self._save_checkpoint()

                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
        
        feedback_conn.close()

checker_service = CheckerService()

@app.route("/")
def index():
    return render_template("checker_index.html")

@app.route("/api/status")
def get_status():
    with checker_service.stats_lock:
        # Force stopped if not actually running
        if not checker_service.is_running:
             checker_service.stats["status"] = "stopped"
        # Always return the latest logs even if stopped
        return jsonify(checker_service.stats)

@app.route("/api/start", methods=["POST"])
def start_check():
    logger.info("Received start request")
    if checker_service.start():
        return jsonify({"success": True, "message": "Started"})
    if checker_service.last_start_error:
        return jsonify({"success": False, "message": checker_service.last_start_error})
    return jsonify({"success": False, "message": "Already running"})

@app.route("/api/stop", methods=["POST"])
def stop_check():
    checker_service.stop()
    return jsonify({"success": True, "message": "Stopping..."})

if __name__ == "__main__":
    print("Starting Checker UI on http://127.0.0.1:5001")
    app.run(port=5001, debug=True, use_reloader=False)
