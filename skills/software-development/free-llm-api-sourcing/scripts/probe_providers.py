"""Probe a batch of LLM provider endpoints without keys.

Reports HTTP status, model count, and abliterated/uncensored hits per provider.
Everything here is a read of a public model list - no keys, no writes, no cost.

Usage:
  python probe_providers.py                      # built-in known-endpoint list
  python probe_providers.py <base_url> [...]     # ad-hoc: base URLs or full /v1/models URLs

A base URL is expanded to <base>/v1/models. Pass the full URL to override
(some providers use /v3/openai/models or /v1/openai/models).
"""

import json
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINTS = [
    "https://openrouter.ai/api/v1/models",
    "https://llm.chutes.ai/v1/models",
    "https://api.featherless.ai/v1/models",
    "https://api.deepinfra.com/v1/openai/models",
    "https://api.novita.ai/v3/openai/models",
    "https://api.sambanova.ai/v1/models",
    "https://api.together.xyz/v1/models",
    "https://api.hyperbolic.xyz/v1/models",
    "https://api.groq.com/openai/v1/models",
    "https://api.cerebras.ai/v1/models",
    "https://api.arliai.com/v1/models",
    "https://text.pollinations.ai/models",
]

UNCENSORED_KEYWORDS = (
    "abliterat", "uncensor", "heretic", "unfiltered", "nsfw", "dark",
    "dolphin", "savage", "styx",
)


def fetch(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001 - probe tool, any failure is just a status
        return None, f"{type(e).__name__}: {e}"


def extract_models(body: str) -> list[dict]:
    try:
        data = json.loads(body)
    except Exception:  # noqa: BLE001
        return []
    if isinstance(data, dict):
        data = data.get("data") or data.get("hydra:member") or data.get("member") or []
    if not isinstance(data, list):
        return []
    out = []
    for m in data:
        if isinstance(m, dict):
            out.append(m)
        elif isinstance(m, str):
            out.append({"id": m})
    return out


def is_free(model: dict) -> bool:
    p = model.get("pricing") or {}
    return str(p.get("prompt")) == "0" and str(p.get("completion")) == "0"


def main() -> None:
    args = sys.argv[1:]
    urls = args or DEFAULT_ENDPOINTS
    urls = [u if "/models" in u else u.rstrip("/") + "/v1/models" for u in urls]

    for url in urls:
        status, body = fetch(url)
        models = extract_models(body)
        hits = [m for m in models if any(k in (m.get("id") or "").lower() for k in UNCENSORED_KEYWORDS)]
        free = [m for m in models if is_free(m)]
        print(f"[{status}] {len(models):>6} models  {url}")
        if free:
            print(f"        {len(free)} marked free at the model level")
        for m in hits[:8]:
            print(f"        uncensored: {m.get('id')}")
        if len(hits) > 8:
            print(f"        ... +{len(hits) - 8} more uncensored")
        if not models and status not in (200,):
            print(f"        {body[:100]}")


if __name__ == "__main__":
    main()
