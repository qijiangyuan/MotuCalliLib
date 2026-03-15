import os
import time
from huggingface_hub import hf_hub_download


FILES = [
    "InternVL/added_tokens.json",
    "InternVL/configuration_intern_vit.py",
    "InternVL/configuration_internlm2.py",
    "InternVL/configuration_internvl_chat.py",
    "InternVL/conversation.py",
    "InternVL/generation_config.json",
    "InternVL/model.safetensors.index.json",
    "InternVL/modeling_intern_vit.py",
    "InternVL/modeling_internlm2.py",
    "InternVL/modeling_internvl_chat.py",
    "InternVL/perceiver_resampler.py",
    "InternVL/special_tokens_map.json",
    "InternVL/tokenization_internlm2.py",
    "InternVL/tokenization_internlm2_fast.py",
    "InternVL/tokenizer.model",
    "InternVL/tokenizer_config.json",
    "InternVL/utils.py",
]


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_dir = os.path.join(project_root, "data", "models", "CalliReader")
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
                    local_dir=local_dir,
                )
                print(f"{file_name} done", flush=True)
                break
            except Exception as e:
                print(f"{file_name} failed: {e}", flush=True)
                time.sleep(3)
    print("SUPPORT_DONE", flush=True)


if __name__ == "__main__":
    main()
