import os
import time
from huggingface_hub import hf_hub_download


FILES = [
    "params/best.pt",
    "InternVL/model-00001-of-00004.safetensors",
    "InternVL/model-00002-of-00004.safetensors",
    "InternVL/model-00003-of-00004.safetensors",
    "InternVL/model-00004-of-00004.safetensors",
]


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_dir = os.path.join(project_root, "data", "models", "CalliReader")
    os.makedirs(local_dir, exist_ok=True)
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

    print(f"Download target: {local_dir}", flush=True)
    for f in FILES:
        attempt = 0
        while True:
            attempt += 1
            try:
                print(f"[{f}] attempt {attempt} ...", flush=True)
                path = hf_hub_download(
                    repo_id="gtang666/CalliReader",
                    filename=f,
                    repo_type="model",
                    local_dir=local_dir,
                    local_dir_use_symlinks=False,
                    resume_download=True,
                )
                print(f"[{f}] done: {path}", flush=True)
                break
            except Exception as e:
                print(f"[{f}] failed: {e}", flush=True)
                time.sleep(5)

    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
