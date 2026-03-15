import os
import time
from huggingface_hub import hf_hub_download


FILES = [
    "params/callialign.pth",
    "params/gauss_norm.pth",
    "params/gauss_norm_mu_sigma.pth",
    "params/mlp1.pth",
    "params/new1000_token_embedding.pth",
    "params/orderformer.pth",
    "params/token_embedding.pth",
    "params/vit_model.pt",
]


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_dir = os.path.join(project_root, "data", "models", "CalliReader")
    os.makedirs(os.path.join(local_dir, "params"), exist_ok=True)
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    for file_name in FILES:
        attempt = 0
        while True:
            attempt += 1
            try:
                print(f"{file_name} attempt {attempt}", flush=True)
                hf_hub_download(
                    repo_id="gtang666/CalliReader",
                    filename=file_name,
                    repo_type="model",
                    local_dir=local_dir
                )
                print(f"{file_name} done", flush=True)
                break
            except Exception as e:
                print(f"{file_name} failed: {e}", flush=True)
                time.sleep(5)
    print("PARAMS_DONE", flush=True)


if __name__ == "__main__":
    main()
