# Provider auth-stack notes

Distilled recon results for specific signup targets. Append per provider; do not create per-session files.

## abliteration.ai
- Console is Next.js behind Cloudflare; assets under `/console-assets/`.
- Email/password signup: client posts to `/auth/password/sign-up` (form on `/sign-up`, fields email + password + optional referral code).
- OAuth buttons are plain HTML forms: `POST /auth/start/{google,github,microsoft}`.
- Anti-bot: Cloudflare Turnstile (invisible, `render=explicit`, `appearance: "interaction-only"`) + WorkOS Radar device signals (`window.__WorkOSRadarCollector.signalsId`) sent with the signup payload. Headless/scripted signup is high-risk; the bookmarklet route in SKILL.md is the reliable path.
- Free tier exists without card ("Try free, no card required") — but it is a PLAYGROUND preview, not a credit grant. A fresh signup lands with 0 credits; hitting `/v1/chat/completions` returns 402 `insufficient_credits` / billing error. Do not farm accounts here expecting free tokens; the only ways to credits are a paid plan or the referral / `social_bundle` credit programs shown in the console rewards panel.
- Credit-program states to expect in the signup analytics schema (`signup_credit_status`): `granted`, `already_granted`, `not_eligible`, `review_required`, `disabled`, `unavailable` — new accounts are routinely `not_eligible`/`review_required`, so signup credit is not guaranteed.
- The anonymous free tier documented for the API (`X-Free-Tier: 1` / `true`, omit Authorization) is stale: the live endpoint returns 401 `missing_api_key` on `/v1/chat/completions`, `/v1/messages`, and `/v1/responses`. Ignore that doc claim.
- `/console/billing` and `/console/rewards` are auth-gated: an unauthenticated fetch returns the sign-in page (or a 307), so their contents are only readable from a logged-in browser session.

## venice.ai
- Signup lives at `/sign-up` and is backed by Clerk.io — there is no usable public signup POST (direct probes to `/api/auth/*` and `api.venice.ai/api/*` return 400/404). Recon the page HTML/JS for the Clerk key rather than guessing endpoints.
- Clerk enforces what Venice's own privacy copy does not: disposable addresses are refused at the form (`Disposable email addresses are not permitted`) and breached/common passwords are refused via a breach-list check. The site's suggestion that users may use a disposable address does not survive Clerk's gate — use permanent-domain aliases plus a fresh random password per account.
- Free tier is base models only (10 text prompts/day, 15 image/day, API access paid with credits, no card). Uncensored entries on the public model list include `venice-uncensored-1-2`, `venice-uncensored-role-play`, and `gemma-4-uncensored`.
- The public model list (`GET api.venice.ai/api/v1/models`, ~128 entries) is readable without a key; chat completions require one (401 without, x402/payment shape on some routes).
