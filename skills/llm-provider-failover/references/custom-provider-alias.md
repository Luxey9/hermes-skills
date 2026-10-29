# Custom (no-plugin) provider alias

Worked sequence for routing a third-party OpenAI-compatible API into Hermes chat without a shipped provider plugin. Reference case: Meta Model API / Muse (base `https://api.meta.ai/v1`, models `muse-spark-1.3`, `muse-wonder-1.0`, `muse-image-1.0`, `muse-spark-1.3-contributor`).

## 1. Confirm endpoint shape before config

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://api.meta.ai/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer dummy' \
  -d '{"model":"muse-spark-1.3","messages":[{"role":"user","content":"hi"}]}'
# 401 + {"error":{"code":"invalid_api_key"}} => route good, key missing
```

A 404, HTML body, or redirect means the path or base URL is wrong — stop and re-read the docs.

## 2. Key into .env, route into config.yaml

```bash
printf '\nHERMES_CUSTOM_<NAME>_API_KEY=<key>\n' >> "$LOCALAPPDATA/hermes/.env"   # Windows
hermes config set model.aliases.muse.model muse-spark-1.3
hermes config set model.aliases.muse.provider custom
hermes config set model.aliases.muse.base_url https://api.meta.ai/v1
hermes config set model.aliases.muse.api_mode chat_completions
hermes config set model.aliases.muse.key_env HERMES_CUSTOM_MUSE_API_KEY
hermes config get model.aliases        # confirm the block landed
```

Alias (not `model.default`) keeps the user's current provider live; switching is `/model muse` in chat. Add a second alias for the bigger model rather than overwriting the first.

## 3. Billing semantics — ask before recommending

Three products can share one vendor account and each has its own meter:

| Surface | Billing | Reaches Hermes? |
|---|---|---|
| Consumer app subscription | flat, metered in prompts/tokens per period | no API access |
| CLI/coding-agent subscription | flat monthly, metered per prompt window, key auto-bound to that CLI | no — that credential is CLI-only |
| Dashboard API key | pay-as-you-go per token | yes |

So the alias must use a pay-as-you-go dashboard key even when the user already pays for a plan. Cheap escape hatch worth offering: the vendor's discounted/training-data tier (Meta: `*-contributor` variants at ~10x lower token price, content used for training) or an aggregator that already carries the model (OpenRouter exposes all Muse variants at matching prices, one key for everything). Self-hosted open weights are the only zero-token-cost route.

## 4. Verify for real

Replace `dummy` with the stored key and re-run the curl, then `/model <alias>` and one short turn in chat. Report status codes, never the key. If the key is absent, say plainly that the config is staged and the round-trip is untested.
