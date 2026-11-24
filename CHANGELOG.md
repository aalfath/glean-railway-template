# Changelog

Breaking changes are listed first in each entry.

## 0.3.0 (template 1), 2026-11-24

- First release: Glean v0.3.0 (commit `3a0c39dc`), web and admin images pinned by digest, pgvector 0.8.7 on PostgreSQL 16, Redis 8.4.8.
- Backend built without PyTorch/sentence-transformers (local embedding provider unavailable; use an OpenAI-compatible embedding API).
- First boot creates the admin and the first reader account from generated passwords and turns open sign-up off.
