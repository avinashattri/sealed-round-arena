import hashlib
import json
import sys
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import hf_hub_download

LOCK = Path("locks/assets.lock.json")
MODEL = {
    "repo_id": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
}  # verify on the repo's Files tab


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def check_or_pin(key, path, lock):
    digest = sha256(path)
    if key in lock and lock[key] != digest:
        sys.exit(f"HASH MISMATCH {key}: expected {lock[key]}, got {digest}")
    lock[key] = digest  # first run pins, later runs verify
    return digest


def main():
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    model_path = hf_hub_download(local_dir="models", **MODEL)
    print("model sha256:", check_or_pin("model", model_path, lock))
    ds = load_dataset("Lakera/gandalf_ignore_instructions", split="train")
    out = Path("data/raw/gandalf_train.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_json(str(out))  # dataset hash can change if library versions change: pin them
    print("gandalf sha256:", check_or_pin("gandalf_train", out, lock))
    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
