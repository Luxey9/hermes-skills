---
name: free-llm-api-sourcing
version: 1.0.0
author: ratman4080
license: MIT
description: Use when sourcing free or uncensored LLM API access.
metadata:
  hermes:
    tags: [llm, api, providers, free-tier, uncensored]
    related_skills: [web-signup-automation, hermes-agent]
---

# Free / Uncensored LLM API Sourcing

## When to Use

- User wants API access to an LLM without paying, or wants an uncensored/abliterated model.
- A provider account turned out to grant nothing (0 credits) and the user says "cari lainnya".
- User asks which providers give a real free tier, or wants a no-key endpoint as a fallback.

Class: finding, validating, and wiring up LLM API access. Sourcing is a *verification* task, not a browsing task — never recommend a provider you have not fired a request at.

## Procedure

1. **Probe the provider's model list endpoint first — it needs no key and tells you a lot:**
   - `curl -s -o out.json -w '%{http_code}' <base>/v1/models`
   - `200` + a model array = the provider exists and the catalog is public (you still need a key to infer). `401` = key required but the provider is alive. `403`/`000` = blocked or not reachable.
   - Run the whole batch at once; the probe script is `scripts/probe_providers.py` (give it URLs, it reports status + model count + uncensored hits).
2. **Scan the catalog for the model class the user wants** — match on `abliterat|uncensor|heretic|unfiltered|nsfw|dolphin|savage|styx` in the model id/name. Report counts honestly: a provider with 22k models may have hundreds of abliterated variants but that says nothing about price.
3. **Distinguish "free model" from "free account":** OpenRouter-style catalogs mark per-model pricing (`pricing.prompt == "0" && pricing.completion == "0"`) — a `:free` suffix model is free to *call*, but you still need a key. A "free tier" on the pricing page is a marketing claim until you fire a request.
4. **Fire one real request per candidate before recommending it.** Nothing else counts as evidence:
   - No key required → plain POST to `<base>/v1/chat/completions`; if it returns a completion, it is a genuine no-key endpoint (Pollinations is the known one; see references).
   - With key → expect a billing error (`402 insufficient_credits`, or `401`) when the account is empty. That is the answer, not a transient fault.
   - Fallback endpoints: some providers reject the streaming/chat path but accept `/v1/messages` (Anthropic-shaped) or `/v1/responses`. Try those before declaring a provider dead.
5. **If the user's own key exists, test it before hunting new providers** — check `HERMES_*_API_KEY` env vars and `providers:` in `$HOME/AppData/Local/hermes/config.yaml` (`base_url`, `model`, `key_env`). The user often already has the provider configured with an empty balance; that is a top-up question, not a sourcing question. Report it that way.
6. **Report the trade-off matrix, not a single answer:** no-key/anon (works, rate-limited, small models) vs. cheap paid flat-rate (huge uncensored catalog) vs. self-host on the user's own hardware vs. top-up of an existing account. Name the concrete price and the concrete model.
7. **When the user supplies multiple keys for one provider, pool them and order by live status:** add each key with `hermes auth add <provider> --type api-key --api-key '<key>' --label '<provider>-N'` (repeat per profile with `-p <profile>` when the work is profile-scoped), fire one real `chat/completions` request per key to learn which are live (`200`) vs empty (`402 insufficient_credits`), then put the live key at priority 0 so it is tried first and keep dead keys as lower-priority spares that reactivate on top-up. Set priority with `hermes auth priority <provider> <target> <priority>` (all positional, no flags); if the CLI cannot resolve the target, edit `profiles/<name>/auth.json` → `credential_pool.<provider>` priorities directly and re-sort. Verify the pool answers before promising failover works.
8. **Wire Hermes-level fallback after the pool:** primary is `model.provider`/`model.default`; append providers with `hermes config set fallback_providers '[{"provider":"<p>","model":"<m>"}]'` and verify with `hermes -p <profile> fallback list`. Point every entry at an endpoint already verified live in step 4, and never repeat the primary as a fallback entry — it burns a retry on the same failure. Fallback fires on rate-limit/5xx/connection/billing errors.

## Pitfalls

- A provider's anonymous/free-tier *documentation* is not evidence. Documented headers like `X-Free-Tier: true` can be stale and return `401 missing_api_key` on every path. Fire the request.
- "Free preview / try free, no card" on a pricing page usually means a playground, not API credits. The account lands at 0 credits and the first API call 402s. See `web-signup-automation` step 5 — confirm the reward lands before farming accounts for it.
- Rate limits and quotas can be per-network, not per-key: a no-key endpoint that answers fine from one path may answer "not enough credits" from the user's network. Test from where the request will actually be made before promising it works.
- Don't present a sequence of failed probes as a recommended workflow. If nothing worked, say nothing worked and give the paid/self-host options — do not dress the dead ends up as guidance.
- Self-hosting is a real answer worth offering when the box has Ollama and enough RAM: check `ollama --version`, `ollama list`, and total RAM first, then propose a model size that actually fits (an 8B Q4 needs ~6GB). Do not propose a 70B on 15GB.
- A Cloudflare `1010` on a probe is not a dead key until retried with a browser `User-Agent` — bare-script requests get challenged while real clients pass, so only the second failure counts.
- A credential pool hides dead keys: test each key with a live request and order by result, working key at priority 0 first, because the pool alone never tells you which member is empty.

## Notes

- Verified provider findings and quirks: `references/providers.md`.
- Probe runner: `scripts/probe_providers.py`.
