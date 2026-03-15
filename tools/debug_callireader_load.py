import os
import traceback

import torch
from transformers import AutoModel, AutoTokenizer
from ultralytics import YOLO


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.join(project_root, "data", "models", "CalliReader")
    internvl_path = os.path.join(base_dir, "InternVL")
    yolo_checkpoint = os.path.join(base_dir, "params", "best.pt")
    print(f"internvl_path={internvl_path}")
    print(f"yolo_checkpoint_exists={os.path.exists(yolo_checkpoint)}")
    try:
        model = AutoModel.from_pretrained(
            internvl_path,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        ).eval()
        print(f"model_loaded={type(model)}")
    except Exception:
        print("model_load_failed")
        traceback.print_exc()
        return
    try:
        tokenizer = AutoTokenizer.from_pretrained(internvl_path, trust_remote_code=True)
        print(f"tokenizer_loaded={type(tokenizer)}")
    except Exception:
        print("tokenizer_load_failed")
        traceback.print_exc()
    try:
        detector = YOLO(yolo_checkpoint)
        print(f"detector_loaded={type(detector)}")
    except Exception:
        print("detector_load_failed")
        traceback.print_exc()


if __name__ == "__main__":
    main()
