# Provider findings — free / uncensored LLM API

Recon results that survived a live request. Append per provider; do not create per-session files. Prices and catalogs move — re-probe with `scripts/probe_providers.py` before relying on a row.

## No-key endpoints (verified working)

- **Pollinations** — `https://text.pollinations.ai/openai` (OpenAI-compatible), plus a one-shot GET form `https://text.pollinations.ai/<url-encoded prompt>`. Model list at `/models`; currently one anonymous-tier model, `openai-fast` (GPT-OSS 20B), tier `anonymous`. No signup, no key.
  - The GET form is more reliable than the POST path; the POST path intermittently returns an empty body.
  - The tier is quota-managed per network, not per key: from some networks both paths answer "The account behind this API key doesn't have enough credits". Probe from the target network before promising it.
  - Client wrapper written for this: `polli.py` in the email-gen toolkit dir.

## Key required, catalog public

- **OpenRouter** — `/api/v1/models` is public and carries per-model pricing; models with `pricing.prompt == "0"` and a `:free` suffix are free to call but still need a logged-in key. Anonymous calls return `401 No cookie auth credentials found`.
- **Featherless** — `/v1/models` returns ~22k models with a large abliterated/uncensored catalog (huihui-ai, failspy, DarkArtsForge, heretic merges). Paid: flat-rate plans from ~$25/mo, or usage-based credits. Best option when the user's real need is *variety* of uncensored models.
- **Chutes** — public `/v1/models` (TEE-suffixed catalog). Requires a key; anonymous calls get rate-limited (`429`).
- **SambaNova** — public `/v1/models`, small curated catalog (DeepSeek, Llama 3.3 70B, gpt-oss-120b). Key required for inference.
- **ArliAI** — uncensored specialist; `/v1/models` returns `401` without a key. Key required.
- **DeepInfra, Novita, Together, Hyperbolic, Groq, Cerebras** — public model lists on most; `401`/`403` on inference without a key.

## Model-list path variants

Most providers serve `<base>/v1/models`, but some use `<base>/v1/openai/models` (DeepInfra) or `<base>/v3/openai/models` (Novita). If `/v1/models` 404s, try those before declaring the provider unreachable.

## abliteration.ai

See `web-signup-automation/references/provider-auth-notes.md` — signup grants no credits; only a paid plan does.
