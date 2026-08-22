# 📋 Changelog — AnkiAI ImageAddon

---

## Version 6.0 — Pipeline Accuracy-First (August 2026)

### 🏗️ Kiến trúc mới hoàn toàn

Rewrite toàn bộ pipeline từ keyword-AI sang **Accuracy-First**:
phân loại cục bộ → search + CLIP rerank → Vision QC, với ngân sách 3–4 s/thẻ.

#### GĐ0 — Dọn nền & cleanup
- Audit repo thật, đối chiếu Master Spec v9
- Đồng bộ local/public Git
- Tạo `user_files/.gitkeep`, dời cache JSON vào `user_files/`
- Cập nhật `.gitignore` cho runtime data (sqlite, models, logs, json)
- Gộp trùng docs: 14 guides → `docs/guides/`, ~43 archive → `docs/archive/`
- Auto-gen `STRUCTURE.txt` trong `build.py` thay viết tay
- Gỡ Tenor (đóng cửa 30/6/2026) + guard legacy config key
- Audit `image_handler.py` (nén in-memory, rollback orphan) và `bg_handler.py` (QueryOp + ThreadPoolExecutor)
- 47/47 tests passed, build `.ankiaddon` sạch

#### GĐ1 — Shadow Classifier + Contract + Sandbox
- `image_providers/base_provider.py`: `Candidate` dataclass frozen + `BaseProvider` interface
- Tách `api_handler.py` → `image_providers/` (4 subpackage: static, animated, scientific, wikimedia)
- `test_providers_contract.py` (12 tests, HTTP mock)
- 7 bộ dataset tĩnh trong `classification/data/` (concreteness, idioms, gazetteer, domain_lexicon, function_words, spatial_prepositions, stative_verbs)
- `model_downloader.py` (sha256 + resume + progress) + `resources.py` (lazy-load)
- `classification/{taxonomy,visual_type}.py` — 14 nhóm A–N + 7 visual_type
- Shadow mode: chạy song song, không can thiệp note database
- `eval_set_v1.json` (153 từ gán nhãn, phủ trọn 14 nhóm)
- `test_taxonomy.py` 100% accuracy, `test_visual_type.py` hồi quy "tactics"
- `sandbox.py` CLI: `python -m modules.sandbox --word ... --stage all`
- `test_latency.py`: p95 = 0.036 ms/từ (budget 50ms)
- CI GitHub Actions: Python 3.9–3.12
- 70/70 tests passed

#### GĐ2 — CLIP + Reranker
- `classification/clip_scorer.py` (3 tier: ONNX → heuristic → none, batch-encode, encode text 1 lần)
- `modules/reranker.py` (CLIP gate + bias nhóm: boost map/arrow/diagram, phạt coach/stadium/whouting)
- Tắt dần AI "Smart Selection" cũ khi `enable_clip_reranker=True`
- `model_downloader.py`: `ensure_clip_model(tier)` + `CLIP_MODELS` dict
- `config.py`: config_version=9, upgrader, 7 keys GĐ2 mới
- `image_providers/health.py` (HealthBoard): EMA latency/success, thứ tự fallback động, thread-safe
- Dependency strategy ghi trong DEVELOPMENT.md
- 113/113 tests passed

#### GĐ3 — Proxy Map + SVG
- `user_files/concept_metaphor_map.json` (30 proxy families + 12 nhóm mở rộng)
- `image_providers/svg_engine.py` (~26 template: 22 giới từ nhóm K + 4 sub-type nhóm N)
- `image_providers/local_svg_provider.py`: data-URI SVG, 0 network, score=1.0
- Integration: taxonomy → svg_engine, K/N trả ảnh 0 request
- 160/160 tests passed

#### GĐ4 — LLM + Quota + Pipeline Accuracy-First
- `llm/groq_client.py` (batch auto TPM, pacing, fallback, probe đầu phiên)
- `llm/gemini_client.py` (text backup + vision QC xương sống, probe cả vision model)
- `llm/prompts.py` (P1/P2/P3)
- `modules/quota.py` (reserve 20%, 5 degrade levels, 12 tests)
- `modules/pipeline.py` (orchestrator §9 + budget governor: chỉ thị 3,4; QC 1 ảnh/từ: chỉ thị 1)
- `test_pipeline_budget.py` (16 tests)
- Nối UI vào pipeline mới, XOÁ hành vi "AI keyword từng thẻ"
- `min_candidates_before_ai_expand` cho nhóm D (chỉ thị 7)
- `logging_setup.py`: rotating 3×1 MB trong `user_files/logs/` + redact API key
- `image_handler.py` implement: nén TRƯỚC `add_file()` (≤800px, JPEG q80, ≤120KB), progressive quality
- `config.py`: 28 keys GĐ4 mới
- 188/188 tests passed

#### GĐ5 — SQLite Cache + Retry Queue + Telemetry
- `modules/cache.py` SQLite 4-tier (WAL, indexes): L1 word→url, L2 word+sense→query, L3 query→candidates TTL 30d, L4 negative
- JSON → SQLite migration (cả vị trí mới/cũ) + `migration.done` tombstone
- `test_cache.py` 24 tests (WAL, crash resilience) + `test_cache_migration.py` 9 tests
- retry_queue: 8 methods trong cache.py + RetryQueue wrapper trong bg_handler.py
- IdlePrefetch: QTimer 300ms + QueryOp, đọc config idle_prefetch_enabled/batch
- `modules/telemetry.py`: TelemetryCollector + suggest_adjustments + feedback (👍→record, 👎→L4 negative)
- `test_telemetry.py` 14 tests
- UI: FeedbackWidget (callback-based 👍/👎), QuotaDisplayWidget (color-coded), VerificationBadge (✓/⚠)
- ConfigDialog thêm "Pipeline · Cache · Telemetry" card (7 keys mới)
- 255/255 tests passed

#### GĐ6 — Community Cache
- 4 methods trong `cache.py`: `community_export()`, `community_export_to_file()`, `community_import()`, `community_import_from_file()`
- Pack format version 1, anonymous (word/sense_id/group/visual_type/url/clip_score/qc_verified/source_provider/attribution)
- Local wins on conflict, version mismatch rejects pack
- `test_community_cache.py` 15 tests
- 270/270 tests passed

### 📊 Metrics tổng hợp

| GĐ | Tests | Eval accuracy | p95 latency | AI calls/ngày |
|----|-------|---------------|-------------|---------------|
| GĐ0 | 47/47 | — | — | — |
| GĐ1 | 70/70 | 100.00% | 0.036 ms | 0 |
| GĐ2 | 113/113 | — | — | 0 |
| GĐ3 | 160/160 | — | — | 0 |
| GĐ4 | 188/188 | — | — | 0 |
| GĐ5 | 255/255 | — | — | — |
| GĐ6 | 270/270 | — | — | — |

### 🔑 Config keys mới (v6.0)

```
clip_tier, clip_confidence_threshold, strict_accuracy_mode,
card_latency_budget_ms, idle_prefetch_enabled, idle_prefetch_batch,
telemetry_enabled, url_only_mode, groq_model, gemini_vision_model,
groq_batch_deadline_ms, min_candidates_before_ai_expand,
community_cache_enabled, round2_min_remaining_ms, ...
```

Config version: 9 (tự động upgrade từ các version cũ).

---

## Version 5.0 — GIF & Animated Providers (May 2026)

### 🆕 New Features
- 5 GIF/Animated providers: KLIPY, GIPHY, Tenor, Pixabay GIF, IconScout
- Localization support (KLIPY)
- Animated icons (IconScout)
- Smart AI domain routing
- Adaptive rate limiting

### 🐛 Bug Fixes
- Better error handling
- Improved concurrent requests
- Enhanced provider fallback
- Optimized session pooling

---

## Version 4.0 — DALL-E & Batch (January 2026)

- DALL-E 3 integration
- Batch processing for 1000+ cards
- Image optimization (75% smaller)

---

## Version 3.0 — Initial Release (2025)

- Basic image search from 15+ sources
- ChatGPT keyword generation
- Unsplash + Pixabay integration
- Basic progress dialog

---

**Phiên bản hiện tại**: 6.0.0  
**Ngày phát hành**: August 2026  
**Trạng thái**: Stable ✅  
**Tương thích**: Anki 24.04+ (Qt6)
