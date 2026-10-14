import argparse
import time
from pathlib import Path

import httpx

from contracts.prompt import build_system_prompt

PUBLIC_PROMPT_PATH = Path(__file__).parent / "system_prompt_public.txt"


def ask(
    user_prompt: str,
    canary: str | None = None,
    public_text: str | None = None,
    url: str = "http://127.0.0.1:8080",
    temperature: float = 0.0,
    seed: int = 1,
    max_tokens: int = 128,
    timeout: float = 60.0,
) -> tuple[str, float]:
    """Query model with canary system prompt and return (reply_text, elapsed_seconds)."""
    if public_text is None:
        public_text = (
            PUBLIC_PROMPT_PATH.read_text(encoding="utf-8")
            if PUBLIC_PROMPT_PATH.exists()
            else "You are a helpful assistant."
        )

    if canary is None:
        canary_file = Path("secrets/model_canary.txt")
        if canary_file.exists():
            canary = canary_file.read_text().strip()
        else:
            canary = "BYR-0123456789abcdef"

    sys_prompt = build_system_prompt(public_text, canary)

    req_body = {
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "seed": seed,
        "max_tokens": max_tokens,
        "cache_prompt": False,
    }

    t0 = time.perf_counter()
    resp = httpx.post(f"{url}/v1/chat/completions", json=req_body, timeout=timeout)
    resp.raise_for_status()
    t1 = time.perf_counter()

    data = resp.json()
    reply = data["choices"][0]["message"]["content"]
    elapsed = t1 - t0
    return reply, elapsed


def main():
    parser = argparse.ArgumentParser(description="Ask model with canary system prompt")
    parser.add_argument("--prompt", required=True, help="User prompt")
    parser.add_argument("--canary", default=None, help="Canary string")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="Model endpoint URL")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()

    reply, elapsed = ask(
        user_prompt=args.prompt,
        canary=args.canary,
        url=args.url,
        temperature=args.temperature,
        seed=args.seed,
        max_tokens=args.max_tokens,
    )
    print(f"Reply: {reply}")
    print(f"Latency: {elapsed:.2f} s")


if __name__ == "__main__":
    main()
