# 🏗️ Kiến trúc AnkiAI ImageAddon v6.0

## Tổng quan

AnkiAI ImageAddon dùng pipeline **Accuracy-First**: phân loại NLP cục bộ → search + CLIP rerank → Vision QC đồng bộ, trong ngân sách 3–4 s/thẻ. Cache SQLite 4 tầng, retry queue nền, telemetry cục bộ.

```
Từ vựng + Câu ví dụ
        │
        ▼
  Phân loại 14 nhóm A–N (NLP cục bộ, <1 ms)
        │
   ┌────┴────────────┬──────────────┬──────────┐
   ▼                 ▼              ▼          ▼
 Nhóm dễ          Nhóm AI       Nhóm K/N    Nhóm M
 (0 AI call)   (search+CLIP+QC) (SVG nội bộ) (bỏ qua)
   │                 │              │          │
   │          ┌──────┴──────┐      │          │
   │          ▼             ▼      │          │
   │     Search top-12   CLIP     │          │
   │     + fallback    rerank     │          │
   │          │             │      │          │
   │          └──────┬──────┘      │          │
   │                 ▼              │          │
   │          Vision QC ≤2 vòng    │          │
   │          (1 ảnh/vòng)         │          │
   │                 │              │          │
   └────────┬────────┴──────────────┘          │
            ▼                                  │
     L1 cache → url → download → compress     │
            │                                  │
            ▼                                  ▼
     Gắn ảnh vào thẻ ✓                   Bỏ qua thẻ
```

## Cấu trúc thư mục

```
AnkiAI_ImageAddon/
├── __init__.py                  # Entry point + AddImageTask + Browser menu hooks
├── modules/
│   ├── config.py                # ConfigManager (v10, auto-upgrader, 55+ keys)
│   ├── pipeline.py              # Orchestrator Accuracy-First + budget governor
│   ├── cache.py                 # CacheManager: SQLite 4-tier + retry queue + community
│   ├── bg_handler.py            # BackgroundProcessor + RetryQueue + IdlePrefetch
│   ├── telemetry.py             # TelemetryCollector + suggest_adjustments + feedback→L4
│   ├── quota.py                 # QuotaManager: reserve 20%, 5 degrade levels
│   ├── reranker.py              # CLIP gate + bias theo nhóm (boost/penalty keywords)
│   ├── image_handler.py         # Tải, nén in-memory (≤800px q80 ≤120KB), lưu Anki media
│   ├── ui.py                    # ConfigDialog + FeedbackWidget + QuotaDisplay + VerificationBadge
│   ├── ui_theme.py              # Theme tokens + stylesheet
│   ├── ui_widgets.py            # Widget primitives
│   ├── note_presets.py          # Note type preset management
│   ├── features.py              # Feature flags
│   ├── logging_setup.py         # Rotating 3×1 MB + redact API key
│   ├── model_downloader.py      # Tải model: sha256 + resume + progress
│   ├── sandbox.py               # CLI sandbox (không cần Anki)
│   ├── debug_log.py             # Debug logging helpers
│   ├── http_session_manager.py  # HTTP session pooling
│   ├── api_handler.py           # Legacy AI handler (guard)
│   ├── ai_providers.py          # AI provider registry (legacy)
│   ├── imagen_provider.py       # Imagen provider (legacy)
│   ├── image_providers.py       # Image provider routing (legacy)
│   ├── provider_registry.py     # Provider registry
│   │
│   ├── classification/          # NLP cục bộ — KHÔNG import Qt/Anki
│   │   ├── taxonomy.py          # Phân loại 14 nhóm A–N
│   │   ├── visual_type.py       # Lớp visual_type (7 loại)
│   │   ├── clip_scorer.py       # CLIP 3-tier: ONNX → heuristic → none
│   │   ├── resources.py         # Lazy-load WordNet/spaCy
│   │   └── data/                # 7 bộ dataset tĩnh
│   │       ├── concreteness.json
│   │       ├── idioms.json
│   │       ├── gazetteer.json
│   │       ├── domain_lexicon.json
│   │       ├── function_words.json
│   │       ├── spatial_prepositions.json
│   │       └── stative_verbs.json
│   │
│   ├── llm/                     # LLM clients
│   │   ├── groq_client.py       # Groq: batch auto TPM, pacing, fallback, probe
│   │   ├── gemini_client.py     # Gemini: text backup + vision QC, probe vision model
│   │   └── prompts.py           # P1 (query gen) / P2 (expand) / P3 (verify)
│   │
│   └── providers/               # Image providers (legacy routing)
│       ├── base.py              # BaseProvider interface
│       ├── general.py           # Pexels, Unsplash, Pixabay, DuckDuckGo, Yandex
│       ├── scientific.py        # PubChem, ChEMBL, PhyloPic, RCSB
│       ├── wikimedia.py         # Wikimedia Commons, NASA, Europeana, Met, LoC
│       ├── animated.py          # KLIPY, GIPHY, Pixabay GIF
│       ├── entertainment.py     # IconScout
│       └── legacy_free.py       # Legacy free providers
│
├── image_providers/             # Contract-based providers (GĐ1+)
│   ├── base_provider.py         # Candidate dataclass (frozen) + BaseProvider interface
│   ├── health.py                # HealthBoard: EMA latency/success, fallback động
│   ├── svg_engine.py            # ~26 SVG template (K: giới từ, N: công thức)
│   ├── local_svg_provider.py    # Data-URI SVG, 0 network, score=1.0
│   ├── static/                  # Static image providers
│   │   ├── wikipedia_provider.py    # Wikipedia REST API — 2-step search
│   │   ├── wikidata_provider.py     # Wikidata QID → P18 → Commons URL
│   │   ├── smithsonian_provider.py  # Smithsonian Open Access
│   │   ├── art_museum_provider.py   # Art Institute Chicago + Cleveland Museum
│   │   ├── flickr_provider.py       # Flickr CC-only (NewFlickrProvider)
│   │   ├── themealdb_provider.py    # TheMealDB food photos
│   │   └── biodiversity_provider.py # Biodiversity Heritage Library
│   ├── icon/                    # Icon providers
│   │   ├── iconify_provider.py      # Iconify search API
│   │   ├── noun_project_provider.py # Noun Project OAuth2
│   │   ├── openmoji_provider.py     # OpenMoji local index
│   │   ├── noto_emoji_provider.py   # Noto Emoji local index
│   │   ├── flagcdn_provider.py      # FlagCDN local index
│   │   ├── gameicons_provider.py    # Game-icons.net local index
│   │   └── openclipart_provider.py  # Openclipart SVG search
│   ├── diagram/                 # Diagram providers
│   │   ├── mermaid_provider.py      # mermaid.ink — generates from code
│   │   ├── quickchart_provider.py   # QuickChart.io — generates charts
│   │   ├── storyset_provider.py     # Storyset illustration search
│   │   └── undraw_provider.py       # unDraw local index + color
│   ├── ai_generation/           # AI generation — chốt chặn cuối cùng (§16)
│   │   ├── pollinations_provider.py # Pollinations.ai stateless URL
│   │   └── huggingface_provider.py  # HuggingFace SDXL + local cache
│   ├── animated/                # Animated providers (contract)
│   ├── scientific/              # Scientific providers (contract)
│   └── wikimedia/               # Wikimedia providers (contract)
│
└── user_files/                  # Runtime data (gitignored)
    ├── cache.sqlite             # SQLite 4-tier cache (WAL)
    ├── models/                  # CLIP/WordNet/spaCy models
    ├── logs/                    # Rotating logs (3×1 MB)
    ├── eval_set/                # Eval set 153 từ gán nhãn
    ├── concept_metaphor_map.json  # Proxy families
    ├── undraw_index.json        # unDraw SVG index (~2MB, download 1 lần)
    ├── emoji_index.json         # OpenMoji/Noto Emoji index (~1MB)
    ├── flags_index.json         # FlagCDN country index (~100KB)
    ├── gameicons_index.json     # Game-icons.net index (~2MB)
    ├── svg_cache/               # SVG đã download (unDraw, Openclipart, OpenMoji, Game-icons)
    ├── hf_cache/                # HuggingFace AI-generated images
    └── .gitkeep
```

## Mô tả Module

### Pipeline (`modules/pipeline.py`)

Orchestrator chính — điều phối toàn bộ flow từ phân loại đến gắn ảnh.

**Quy trình:**
1. Phân loại NLP → nhóm + visual_type
2. Nhóm dễ (A/B/C/H/K/N/M) → search trực tiếp hoặc SVG nội bộ
3. Nhóm AI → Groq tạo query → search top-12–15 → CLIP rerank → Vision QC ≤2 vòng
4. Budget governor kẹp deadline từng bước theo `remaining`
5. L1 cache → url → download → nén → gắn vào thẻ

**Budget governor:**
- `card_latency_budget_ms` = 3500 (mặc định)
- Mỗi bước nhận `remaining_ms`, tự bỏ qua nếu không đủ
- Vòng 2 QC: chỉ mở khi `round2_min_remaining_ms` ≥ 2050

**Nhóm D mở rộng AI:** chỉ khi candidates < `min_candidates_before_ai_expand` (mặc định 3)

**Strict mode:** bỏ qua ảnh chưa QC → chỉ trả ảnh đã verify

---

### CacheManager (`modules/cache.py`)

SQLite 4-tier cache, WAL mode, indexes trên `word` và `query`.

| Tầng | Bảng | Khóa chính | Nội dung | TTL |
|------|------|-----------|----------|-----|
| L1 | `l1_lookup` | word + sense_id | url, clip_score, resolved_by, qc_verified, source_provider, attribution | Vĩnh viễn |
| L2 | `l2_lookup` | word + sense_id | query, en_query, group, visual_type | Vĩnh viễn |
| L3 | `l3_candidates` | query | Top candidates (JSON), provider | 30 ngày |
| L4 | `l4_negative` | word + query | "bad" flag | Vĩnh viễn |

**Bảng phụ:**
- `retry_queue`: hàng đợi thử lại (exponential backoff 30→60→120→240s, max 3 retries)
- `telemetry`: bản ghi telemetry (word, group, latency, clip_score, provider, qc_pass)
- `processed_notes`: note_id đã xử lý (tránh lặp)

**Community cache methods:**
- `community_export()` → pack JSON ẩn danh (version 1)
- `community_export_to_file(path)` → ghi pack ra file
- `community_import(pack)` → nhập pack, local wins
- `community_import_from_file(path)` → đọc + nhập từ file

---

### Background Processing (`modules/bg_handler.py`)

Dùng **Anki QueryOp** + **ThreadPoolExecutor** (KHÔNG asyncio, KHÔNG threading.Thread thô).

- `BackgroundProcessor`: điều phối batch processing với progress bar
- `RetryQueue`: thin wrapper quanh CacheManager retry methods
- `IdlePrefetch`: QTimer 300ms phát hiện idle → QueryOp xử lý các thẻ chưa có ảnh

**Thread safety:** `_GLOBAL_DB_LOCK` (RLock) bảo vệ `col.update_note()` / `col.save()`. Callback `on_done` chạy trên main thread.

---

### QuotaManager (`modules/quota.py`)

Quản lý ngân sách API theo model, 5 degrade levels:

| Level | Điều kiện | Hành vi |
|-------|-----------|---------|
| 0 — Full | Tất cả đủ | AI + vision QC bình thường |
| 1 — Workhorse caution | Workhorse near limit | Ưu tiên reserve model |
| 2 — Reserve only | Workhorse exhausted | Dùng reserve model |
| 3 — Text only | Vision exhausted | Bỏ QC, badge ⚠ unverified |
| 4 — No AI | Tất cả exhausted | Chỉ search tĩnh, không AI |

Reserve 20% quota cho interactive (người dùng tương tác trực tiếp).

---

### Telemetry (`modules/telemetry.py`)

TelemetryCollector — **chỉ cục bộ**, không gửi ra ngoài.

- `record()`: ghi mỗi lần xử lý (word, group, latency, clip_score, provider, qc_pass)
- `feedback(word, url, vote)`: 👍 ghi lại, 👎 thêm vào L4 negative cache
- `recent_entries(word)`: xem bản ghi gần đây
- `suggest_adjustments()`: phân tích và đề xuất tinh chỉnh:
  - QC fail rate cao → tăng CLIP threshold
  - CLIP score thấp → giảm threshold
  - Latency cao → xem lại provider
  - Cache hit rate thấp → bật idle prefetch

---

### Classification (`modules/classification/`)

**Pure Python — KHÔNG import Qt hay Anki.**

**taxonomy.py:**
- 14 nhóm A–N dựa trên 7 bộ data tĩnh + spaCy POS + WordNet + Brysbaert concreteness
- Eval accuracy: 100% (153/153 từ)

**visual_type.py:**
- 7 visual type: photo, diagram_or_map, metaphor_photo, illustration, animated_gif, scientific_image, local_svg, none
- Proxy family mapping cho nhóm E (từ trừu tượng → từ cụ thể)

**clip_scorer.py:**
- 3 tier: ONNX (CLIP model) → heuristic (Brysbaert + boost/penalty keywords) → none
- Batch-encode, encode text 1 lần, luôn nạp `en_query`
- Singleton pattern

---

### Reranker (`modules/reranker.py`)

Kết hợp CLIP score + bias theo nhóm:

- **Boost keywords** (nhóm F): map, arrow, diagram, chess, plan, strategy
- **Penalty keywords** (nhóm F): coach, stadium, whistle, shouting, suit, meeting
- Combined score = CLIP score + bias
- Candidate frozen → dùng `dataclasses.replace()` tạo bản mới

---

### LLM Clients (`modules/llm/`)

**groq_client.py:**
- Batch auto TPM, pacing giữa requests
- Fallback khi model không available
- Probe đầu phiên kiểm tra connectivity

**gemini_client.py:**
- Text generation (backup khi Groq down)
- Vision QC: gửi ảnh + context, hỏi "Does this image match the word?"
- Probe đầu phiên phủ cả `gemini_vision_model`

**prompts.py:**
- P1: tạo search query từ word + definition
- P2: mở rộng query khi candidates ít
- P3: verify image match (Vision QC)

---

### SVG Engine (`image_providers/svg_engine.py`)

Template SVG nội bộ, 0 network request:

- **Nhóm K** (22 template): above, below, beside, between, inside, through, towards, around, behind, in front of, opposite, against, along, across, onto, off, past, upon, beneath, within, without, beyond
- **Nhóm N** (4 sub-type): chemical formula (H₂O, CO₂), measurement unit (37°C), math expression (2+2=4), generic fallback

Output: SVG string → `local_svg_provider.py` bọc thành data-URI `Candidate`.

---

### HealthBoard (`image_providers/health.py`)

Dynamic provider ordering dựa trên EMA latency/success:

- Mỗi provider: EMA latency, success rate, overall score
- `order_providers()` → sắp xếp: fast + reliable lên đầu, down xuống cuối
- Thread-safe (RLock)
- Singleton pattern

---

### Image Handler (`modules/image_handler.py`)

- Tải ảnh in-memory (BytesIO), KHÔNG tạo file tạm
- Nén TRƯỚC `col.media.writeData()`:
  - Long-edge resize ≤ 800px
  - JPEG progressive quality reduction (q80 → q70 → ... ≤ 120KB)
  - Bỏ qua nén cho animated (GIF, animated WebP, SVG)
- Rollback orphan media qua `col.media.trash_files`
- `url_only_mode`: chỉ lưu URL, không tải ảnh (kèm cảnh báo)
- Attribution CC ghi vào field riêng

---

### Config (`modules/config.py`)

`ConfigManager` singleton, version 10:
- `CURRENT_CONFIG_VERSION = 10`
- `_upgrade_config()`: tự động nâng cấp từ version cũ
- `_migrate_to_v9()`: migrate keys cũ → mới
- `_migrate_to_v10()`: thêm 20+ config keys cho 21 provider mới
- Key lạ → ignore + warn (không crash)
- 55+ config keys (API keys, pipeline, cache, telemetry, UI, providers)

---

### Provider Registry (`modules/provider_registry.py`)

v6.0 — điều phối 40+ providers (legacy + mới):

**`_BaseProviderAdapter`**: bridge BaseProvider (Candidate interface) → SmartImageSelector (dict interface), cho phép 21 provider mới hoạt động song song với legacy providers.

**`PROVIDER_CHAINS`**: 14 nhóm A–N, mỗi nhóm có ordered fallback chain (§4.2):

| Nhóm | visual_type | Provider chain (ưu tiên) |
|------|-------------|--------------------------|
| A | photo | wikipedia → wikidata → flickr_cc → pixabay → pexels |
| B | photo | (như A, query theo nghĩa đã chọn) |
| C | photo | wikipedia → flagcdn → smithsonian → artic → wikidata |
| D | diagram/photo | biodiversity → smithsonian → wikipedia → wikimedia |
| E | metaphor_photo | storyset → pollinations → huggingface |
| F | diagram_or_map | mermaid → quickchart → storyset → wikimedia |
| G | gif | klipy → giphy → pixabay_animated |
| H | icon | iconify → gameicons → noun_project_new → iconscout |
| I | photo | pixabay → pexels → flickr_cc → wikipedia |
| J | metaphor_photo | storyset → pollinations → huggingface |
| K | local_svg | svg_engine (0 request) |
| L | metaphor_photo | storyset → openverse → giphy → pollinations |
| M | none | **BỎ QUA** — không provider |
| N | local_svg/diagram | svg_engine → quickchart → pubchem |

**Priority tiers** (§3 nguyên tắc 1: "Local trước, AI sau"):
- **Tier 1**: Cache hit + svg_engine nội bộ (~0 ms)
- **Tier 2**: Static index đã cache local (~5 ms): unDraw, OpenMoji, Noto Emoji, FlagCDN, Game-icons, mermaid.ink, QuickChart
- **Tier 3**: API miễn phí (~200–700 ms): Wikipedia, Wikidata, Smithsonian, Art museums, BHL, TheMealDB, Iconify, Storyset
- **Tier 4**: API cần key (~300–800 ms): Flickr, Noun Project
- **Tier 5**: AI generation — CHỐT CHẶN CUỐI CÙNG (~2000–5000 ms): Pollinations, HuggingFace — BẮT BUỘC vision QC

---

### 21 New Providers (`image_providers/`)

Tất cả inherit `BaseProvider`, implement `search(query, visual_type, limit) → List[Candidate]`.

**Common patterns:**
- Synchronous (`requests.Session`, NO asyncio)
- QuotaManager: `quota.allow()` trước mỗi API call, `quota.record()` sau
- HealthBoard: `health.report()` sau mọi request
- Config via `__init__(config={})` dict
- Return `[]` on error (never crash)
- Lazy singletons cho HealthBoard/QuotaManager

**3 loại chiến lược search:**

| Loại | Providers | Đặc điểm |
|------|-----------|-----------|
| **API per query** | Wikipedia, Wikidata, Smithsonian, Art Museum, Flickr, TheMealDB, Biodiversity, Iconify, Noun Project, Storyset, Openclipart | Gọi HTTP mỗi lần search |
| **Local index** | OpenMoji, Noto Emoji, FlagCDN, Game-icons, unDraw | Download index 1 lần → search local → 0 API call sau |
| **Generate (stateless)** | Mermaid, QuickChart, Pollinations | Construct URL từ code/prompt → không cần search API |

**AI generation đặc biệt (§16):**
- `PollinationsProvider`: stateless — chỉ construct URL, visual_type="metaphor_photo", score=0.6
- `HuggingFaceProvider`: POST SDXL → save binary → `file://` URL, visual_type="metaphor_photo", score=0.5
- Cả hai: KHÔNG dùng visual_type "ai_generated" (không hợp lệ theo §6)
- Cả hai: BẮT BUỘC vision QC đồng bộ trước khi chấp nhận

---

## Design Patterns

| Pattern | Ứng dụng |
|---------|----------|
| **Singleton** | ConfigManager, CacheManager, TelemetryCollector, ClipScorer, HealthBoard |
| **Strategy** | CLIP tier (ONNX/heuristic/none), visual_type routing, provider selection |
| **Frozen dataclass** | Candidate, L1Entry, L2Entry, CardResult — immutable |
| **Budget governor** | Pipeline: deadline per-step, skip nếu insufficient remaining |
| **Exponential backoff** | RetryQueue: 30→60→120→240s, max 3 retries |
| **Observer** | QTimer idle detection → IdlePrefetch, HealthBoard EMA updates |
| **Callback** | FeedbackWidget on_vote, BackgroundProcessor on_progress/on_done |
| **WAL** | SQLite write-ahead logging cho crash resilience |

## Threading Model

```
Main Thread (Qt)
    │
    ├── UI events, Anki operations
    ├── QTimer (300ms) → IdlePrefetch trigger
    │
    └── QueryOp → ThreadPoolExecutor (max 5 workers)
                     │
                     ├── Search providers (I/O bound)
                     ├── CLIP scoring (CPU bound)
                     ├── Image download + compress
                     └── LLM calls (I/O bound)
                          │
                          └── on_done callback → Main Thread
```

**Quy tắc:**
- KHÔNG dùng `asyncio` — `ThreadPoolExecutor` + futures
- KHÔNG dùng `threading.Thread` thô — `QueryOp` cho Anki background
- KHÔNG touch `mw` từ worker thread
- `_GLOBAL_DB_LOCK` (RLock) bảo vệ database writes

## Error Handling

| Layer | Chiến lược |
|-------|-----------|
| **LLM** | Retry 3×, fallback Groq↔Gemini, probe đầu phiên |
| **Search** | Fallback providers (HealthBoard ordering), L3 cache |
| **Image** | Progressive quality reduction, format detection, skip animated compression |
| **Pipeline** | Budget governor skip, degrade chain (quota), L4 negative cache |
| **Cache** | WAL crash resilience, migration tombstone, idempotent import |
| **Background** | RetryQueue exponential backoff, exhausted parked, purge |

## Security

- API keys: lưu local-only, KHÔNG gửi ra ngoài, KHÔNG log
- `_RedactFilter` trong logging: thay API key bằng `***`
- Community cache: ẩn danh hoàn toàn (không sentence, không user data)
- Image: tải về local, sync qua AnkiWeb mechanism chính thức
- `.gitignore`: loại trừ `*.sqlite`, `models/`, `logs/`, `*.json` (trừ `.gitkeep`)

## Testing

270 tests trong `tests/`:

| File | Tests | Nội dung |
|------|-------|----------|
| `test_taxonomy.py` | 6 | Phân loại 14 nhóm, eval accuracy |
| `test_visual_type.py` | 6 | Visual type mapping, hồi quy tactics |
| `test_clip_scorer.py` | 19 | CLIP 3-tier, heuristic, batch, ONNX fallback |
| `test_reranker.py` | 12 | CLIP gate, bias, regression tactics |
| `test_svg_engine.py` | 47 | Template K/N, data-URI, provider interface |
| `test_pipeline_budget.py` | 16 | Budget governor, QC round 2 gate, degrade |
| `test_quota.py` | 12 | Reserve, degrade chain, snapshot |
| `test_cache.py` | 24 | L1–L4, WAL, crash resilience, stats |
| `test_cache_migration.py` | 9 | JSON→SQLite migration |
| `test_retry_queue.py` | 20 | Enqueue/dequeue, backoff, wrapper |
| `test_telemetry.py` | 14 | Record, feedback→L4, suggest_adjustments |
| `test_community_cache.py` | 15 | Export, import, local-wins, round-trip |
| `test_health_board.py` | 12 | EMA, ordering, thread-safe |
| `test_latency.py` | 1 | Classification benchmark |
| `test_model_downloader.py` | 3 | SHA256, resume, checksum mismatch |
| `providers/test_providers_contract.py` | 12 | Candidate, BaseProvider, HTTP mock |
| `providers/test_animated.py` | 9 | KLIPY, GIPHY, Pixabay, IconScout |
| `core/*` | 17 | AddImageTask, delay, image handler, presets |
| `integration/*` | 9 | Animated search, provider stats |
| `test_ui_redesign_verification.py` | 7 | Theme, widgets, dialogs |

---

**Architecture Version**: 6.0  
**Last Updated**: August 2026
