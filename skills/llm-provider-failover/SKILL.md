---
name: llm-provider-failover
description: "Use when setting up Hermes provider fallback."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
---

# LLM Provider Failover

Configure Hermes primary + fallback model routing with pooled credentials, then verify every link live before claiming done.

## Procedure

1. **Inspect current routing first.** Run `hermes -p <profile> fallback list` and check `model.default` / `model.provider` at the top of the profile `config.yaml`. Never assume the primary from memory.
2. **Add keys to the credential pool, not just `.env`.** Use `hermes -p <profile> auth add <provider> --type api-key --api-key '<KEY>' --label '<label>'` once per key. `.env` values alone do not create pool entries.
3. **Order the pool so a known-good key is tried first.** Pool entries carry `priority` (0 = tried first). Reorder via config edit or CLI priority command; verify order by reading `auth.json` `credential_pool.<provider>` labels only.
4. **Keep fallback distinct from primary.** Setting a fallback entry identical to the primary wastes one retry round-trip on a guaranteed repeat failure. Chain shape: primary X -> fallback Y -> fallback Z, all different routes.
5. **Register optional models as aliases, not fallbacks.** `hermes -p <profile> config set model.aliases.<alias> <provider>/<model>` for models the user invokes manually (`/model <alias>`). Unreliable or quota-limited models stay out of the automatic chain.
6. **Verify each link with a live probe.** Send a minimal `chat/completions` request (`max_tokens: 5`) per provider/model/key and report only OK/FAIL + status code. Do a second probe with a browser `User-Agent` before declaring a Cloudflare-gated endpoint dead.
7. **Mirror to each profile explicitly.** Profiles are clones, not links: `default` and `hero` (or any `-p` profile) each need their own `fallback_providers` and aliases. Verify per profile with `hermes -p <profile> fallback list`.

## Pitfalls

- Probe credentials without ever printing them: check presence by key length and prefix only, send the value straight into the request headers, and report only the result. Full keys must never appear in output, logs, or screenshots.
- A single gateway key can front many upstream accounts: one `sk-...` talking to a local router (9router) may rotate across several OAuth connections internally, so one key in `.env` alongside five connections in the router dashboard is the expected shape, not a missing-key bug.
- Distinguish gateway errors from upstream errors: HTTP 429/503 naming the upstream (e.g. conduit free-premium-limit, temporary interruption) means the key and routing are correct and the upstream is throttling or down; fix by waiting, raising quota, or switching routes, never by re-adding the same key.
- Use `hermes -p <profile>` consistently for auth/fallback commands; overriding `HERMES_HOME` by hand can show an empty pool and mislead into re-adding credentials that already exist.
- After changing `model.provider`, re-check `model.base_url` and `key_env`: Hermes clears route fields that belonged to the old provider, and a stale base_url silently points the new provider at the old endpoint.
