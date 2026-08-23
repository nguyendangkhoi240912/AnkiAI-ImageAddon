# 🎨 AnkiAI ImageAddon

**Phiên bản 6.1** — Pipeline Accuracy-First + 21 nguồn ảnh mới: phân loại 14 nhóm → CLIP rerank → Vision QC

## 🌟 AnkiAI là gì?

**AnkiAI ImageAddon** tự động gắn ảnh & GIF cho thẻ từ vựng Anki, dùng pipeline **Accuracy-First**:

- 🧠 **Phân loại 14 nhóm A–N** bằng NLP cục bộ (0 AI call, <1 ms/từ)
- 🎯 **Lớp visual_type** → chọn chiến lược hình ảnh phù hợp nhất
- 🔍 **CLIP 3-tier reranker** — chọn ảnh chính xác nhất từ top candidates
- 👁️ **Vision QC đồng bộ ≤2 vòng** — Gemini kiểm chứng ảnh trước khi gắn
- ⏱️ **Budget governor 3–4 s/thẻ** — không treo UI, không vượt ngân sách
- 💾 **SQLite 4-tier cache** — L1 word→url, L2 word+sense→query, L3 query→candidates, L4 negative
- 🔄 **Retry queue + Idle prefetch** — tự động thử lại khi lỗi, prefetch nền khi rảnh
- 📊 **Telemetry + 👍/👎 feedback** — đo lường chất lượng, đề xuất tinh chỉnh
- 🤝 **Community cache** — xuất/nhập pack L1/L2 ẩn danh, local luôn thắng
- 🖼️ **SVG nội bộ** — nhóm K (giới từ) & N (công thức) trả ảnh 0 request
- 🆕 **21 nguồn ảnh mới** — Wikipedia, Wikidata, Smithsonian, Iconify, mermaid.ink, QuickChart, Pollinations AI, v.v.

## ✨ Kiến trúc Pipeline v6.1

```
Từ vựng + Câu ví dụ
        │
        ▼
  ┌─────────────────────┐
  │  Phân loại NLP cục bộ │  ← 14 nhóm A–N + 7 visual_type
  │  <1 ms, 0 AI call     │  ← taxonomy.py + 7 bộ data tĩnh
  └─────────┬───────────┘
            │
     ┌──────┴──────┬──────────────┬──────────────┐
     ▼             ▼              ▼              ▼
  Nhóm dễ      Nhóm AI        Nhóm K/N       Nhóm M
  (0 AI)       (search+CLIP)  (SVG nội bộ)   (không ảnh)
  0.6–1.5s     3–4s budget    0 request      bỏ qua
     │             │              │              │
     │    ┌────────┴────────┐    │              │
     │    ▼                 ▼    │              │
     │  Search top-12    CLIP   │              │
     │  + fallback      rerank  │              │
     │    │                 │    │              │
     │    └────────┬────────┘    │              │
     │             ▼              │              │
     │      Vision QC ≤2 vòng    │              │
     │      (Gemini, 1 ảnh/vòng) │              │
     │             │              │              │
     └──────┬──────┴──────────────┘              │
            ▼                                    │
     L1 cache → url → download → compress       │
            │                                    │
            ▼                                    ▼
     Gắn ảnh vào thẻ ✓                      Bỏ qua thẻ
```

### 14 nhóm phân loại

| Nhóm | Ví dụ | Visual type | AI cần? |
|------|-------|-------------|---------|
| **A** | apple, tree, mountain | photo | ❌ |
| **B** | car, house, bridge | photo | ❌ |
| **C** | doctor, teacher | photo | ❌ |
| **D** | democracy, economy | photo/illustration | ✅ (nếu <3 candidates) |
| **E** | love, freedom | metaphor_photo | ✅ |
| **F** | tactics, strategy | diagram_or_map | ✅ |
| **G** | metaphor, irony | illustration (CLIP thấp) | ✅ |
| **H** | running, laughing | animated_gif | ❌ |
| **I** | music, cooking | animated_gif/photo | ✅ |
| **J** | heartbeat, pulse | animated_gif | ✅ |
| **K** | above, between, through | **local_svg** | ❌ |
| **L** | cell, molecule | scientific_image | ✅ |
| **M** | the, of, and | none | ❌ |
| **N** | H₂O, 37°C, 2+2=4 | **local_svg** | ❌ |

## 🆕 21 Nguồn ảnh mới (v6.1)

Tích hợp 21 nguồn ảnh theo chuẩn `BaseProvider`, phân loại 4 nhóm với 3 chiến lược search:

### 3 chiến lược search

| Chiến lược | Mô tả | Providers |
|-------------|-------|-----------|
| **API per query** | Gọi HTTP mỗi lần search | Wikipedia, Wikidata, Smithsonian, Art Museum, Flickr, TheMealDB, Biodiversity, Iconify, Noun Project, Storyset, Openclipart |
| **Local index** | Download index 1 lần → search local → 0 API call sau | OpenMoji, Noto Emoji, FlagCDN, Game-icons, unDraw |
| **Generate (stateless)** | Construct URL từ code/prompt → không cần search API | Mermaid, QuickChart, Pollinations |

### 21 provider theo loại ảnh

**Static (7):**
- 📷 **Wikipedia** — 2-step search (article → lead image), CC-BY-SA-3.0
- 🔗 **Wikidata** — QID → P18 image → Commons URL, CC0
- 🏛️ **Smithsonian Open Access** — museum artifacts, Public Domain
- 🎨 **Art Institute Chicago + Cleveland** — combined, IIIF URLs, Public Domain / CC0
- 📸 **Flickr CC-only** — chỉ Creative Commons licenses + SafeSearch, cần API key
- 🍣 **TheMealDB** — food photos, CC-BY
- 🌿 **Biodiversity Heritage Library** — scientific illustrations, Public Domain

**Icon (7):**
- 🔣 **Iconify** — icon search API, MIT/Apache
- 🎯 **Noun Project** — OAuth2, CC-BY-3.0
- 😀 **OpenMoji** — local index, CC-BY-SA-4.0
- 🫠 **Noto Emoji** — Google Fonts SVG, Apache-2.0
- 🏳️ **FlagCDN** — country flag SVGs, Public Domain
- ⚔️ **Game-icons.net** — local index, CC-BY-3.0
- ✂️ **Openclipart** — SVG search, CC0

**Diagram (4):**
- 📊 **mermaid.ink** — generates diagrams from Mermaid.js code, MIT
- 📈 **QuickChart.io** — generates Chart.js charts, MIT
- 🎨 **Storyset** — illustration search, CC-BY-4.0
- ✏️ **unDraw** — local index + color customization, MIT

**AI Generation (2) — chốt chặn cuối cùng:**
- 🤖 **Pollinations.ai** — stateless URL, metaphor_photo, CC-BY
- 🧠 **HuggingFace Inference** — SDXL → local cache, metaphor_photo, CC-BY
- ⚠️ Cả hai BẮT BUỘC vision QC, KHÔNG dùng visual_type "ai_generated"

### Priority tiers

| Tier | Latency | Providers |
|------|---------|-----------|
| **1** | ~0 ms | Cache hit + svg_engine nội bộ |
| **2** | ~5 ms | unDraw, OpenMoji, Noto Emoji, FlagCDN, Game-icons, mermaid.ink, QuickChart |
| **3** | ~200–700 ms | Wikipedia, Wikidata, Smithsonian, Art museums, BHL, TheMealDB, Iconify, Storyset |
| **4** | ~300–800 ms | Flickr, Noun Project (cần API key) |
| **5** | ~2–5 s | Pollinations, HuggingFace — CHỐT CHẶN CUỐI CÙNG, bắt buộc Vision QC |

## 🚀 Cài đặt

### Yêu cầu
- Anki 24.04+ (Qt6)
- API keys (xem bên dưới)

### Cài đặt

**Option A: Từ file .ankiaddon**
1. Download `AnkiAI_ImageAddon-6.1.0.ankiaddon`
2. Anki → Tools → Add-ons → Install from file
3. Khởi động lại Anki

**Option B: Manual**
1. Clone/pull từ [GitHub](https://github.com/nguyendangkhoi240912/AnkiAI-ImageAddon)
2. Copy `AnkiAI_ImageAddon` vào thư mục addons:
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **Linux**: `~/.local/share/Anki2/addons21/`
3. Khởi động lại Anki

## 🔑 API Keys

Chỉ cần ít nhất **1 key** để bắt đầu. Nhiều key = chất lượng tốt hơn.

### Miễn phí — không cần key

| Provider | Ghi chú |
|----------|---------|
| **Wikipedia** | REST API, 5000 req/ngày |
| **Wikidata** | SPARQL, 5000 req/ngày |
| **Smithsonian** | Open Access, 1000 req/ngày |
| **Art Institute Chicago** | Public API, 1000 req/ngày |
| **Cleveland Museum** | Public API, 1000 req/ngày |
| **TheMealDB** | Food photos, 500 req/ngày |
| **Biodiversity Heritage Library** | Scientific illustrations, 1000 req/ngày |
| **Iconify** | Icon search, 1000 req/ngày |
| **Storyset** | Illustrations, 100 req/ngày |
| **Openclipart** | SVG search, không giới hạn |
| **mermaid.ink** | Diagram generation, không giới hạn |
| **QuickChart.io** | Chart generation, 1000 req/ngày |
| **Pollinations.ai** | AI generation, 200 req/ngày |

### Miễn phí (cần đăng ký key)

| Provider | Key config | Lấy key |
|----------|-----------|---------|
| **Pixabay** | `pixabay_api_key` | https://pixabay.com/api/ |
| **Wikimedia** | không cần key | — |
| **KLIPY (GIF)** | `klipy_app_key` | https://www.klipy.io/developers |
| **GIPHY** | `giphy_api_key` | https://developers.giphy.com |
| **Flickr** | `flickr_api_key` | https://www.flickr.com/services/api/ |
| **Noun Project** | `noun_project_client_id` + `noun_project_client_secret` | https://thenounproject.com/developers/ |

### AI (cần cho nhóm khó D/E/F/G/I/J/L)

| Provider | Key config | Mục đích | Lấy key |
|----------|-----------|----------|---------|
| **Groq** | `groq_api_key` | Tạo query, mở rộng search | https://console.groq.com |
| **Gemini** | `gemini_api_key` | Vision QC (kiểm chứng ảnh) | https://aistudio.google.com/apikey |
| **HuggingFace** | `huggingface_api_token` | AI generation (SDXL) | https://huggingface.co/settings/tokens |

### Config mẫu

**Cơ bản (miễn phí):**
```json
{
    "pixabay_api_key": "YOUR_KEY",
    "klipy_app_key": "YOUR_KEY"
}
```

**Đầy đủ (khuyến nghị):**
```json
{
    "pixabay_api_key": "YOUR_KEY",
    "klipy_app_key": "YOUR_KEY",
    "flickr_api_key": "YOUR_KEY",
    "groq_api_key": "YOUR_KEY",
    "gemini_api_key": "YOUR_KEY"
}
```

## 📦 Cấu trúc dự án

```
AnkiAI_ImageAddon/
├── __init__.py                  # Entry point + AddImageTask
├── modules/
│   ├── config.py                # Quản lý cấu hình (v10, upgrader, 55+ keys)
│   ├── pipeline.py              # Orchestrator Accuracy-First + budget governor
│   ├── cache.py                 # SQLite 4-tier + retry queue + community cache
│   ├── bg_handler.py            # BackgroundProcessor + RetryQueue + IdlePrefetch
│   ├── telemetry.py             # TelemetryCollector + suggest_adjustments
│   ├── quota.py                 # QuotaManager + degrade chain
│   ├── reranker.py              # CLIP gate + bias theo nhóm
│   ├── image_handler.py         # Tải, nén, lưu ảnh vào Anki media
│   ├── ui.py                    # ConfigDialog, FeedbackWidget, QuotaDisplay
│   ├── provider_registry.py     # Provider registry v6 — 40+ providers, PROVIDER_CHAINS
│   ├── classification/
│   │   ├── taxonomy.py          # Phân loại 14 nhóm A–N
│   │   ├── visual_type.py       # Lớp visual_type (7 loại)
│   │   ├── clip_scorer.py       # CLIP 3-tier (ONNX → heuristic fallback)
│   │   ├── resources.py         # Lazy-load WordNet/spaCy
│   │   └── data/                # 7 bộ dataset tĩnh (concreteness, idioms, v.v.)
│   ├── llm/
│   │   ├── groq_client.py       # Groq LLM (batch TPM, pacing)
│   │   ├── gemini_client.py     # Gemini text + vision QC
│   │   └── prompts.py           # P1/P2/P3 prompts
│   ├── providers/               # Image providers (general, scientific, animated, v.v.)
│   ├── sandbox.py               # CLI sandbox (chạy độc lập, không cần Anki)
│   └── model_downloader.py      # Tải model (sha256 + resume + progress)
├── image_providers/
│   ├── base_provider.py         # Candidate dataclass + BaseProvider interface
│   ├── health.py                # HealthBoard (EMA latency/success → fallback động)
│   ├── svg_engine.py            # ~26 SVG template K/N
│   ├── local_svg_provider.py    # Data-URI SVG, 0 network
│   ├── static/                  # 7 static providers (Wikipedia, Wikidata, Smithsonian, Art Museum, Flickr, TheMealDB, Biodiversity)
│   ├── icon/                    # 7 icon providers (Iconify, Noun Project, OpenMoji, Noto Emoji, FlagCDN, Game-icons, Openclipart)
│   ├── diagram/                 # 4 diagram providers (Mermaid, QuickChart, Storyset, unDraw)
│   ├── ai_generation/           # 2 AI providers (Pollinations, HuggingFace) — chốt chặn cuối
│   ├── animated/                # Animated providers (contract)
│   ├── scientific/              # Scientific providers (contract)
│   └── wikimedia/               # Wikimedia providers (contract)
├── user_files/                  # Dữ liệu runtime (không commit)
│   ├── cache.sqlite             # SQLite 4-tier cache
│   ├── models/                  # CLIP/WordNet models
│   ├── eval_set/                # Eval set 153 từ gán nhãn
│   ├── undraw_index.json        # unDraw SVG index
│   ├── emoji_index.json         # OpenMoji/Noto Emoji index
│   ├── flags_index.json         # FlagCDN country index
│   ├── gameicons_index.json     # Game-icons.net index
│   ├── svg_cache/               # SVG đã download
│   ├── hf_cache/                # HuggingFace AI images
│   └── concept_metaphor_map.json
└── tests/                       # 332 tests
```

## 🧪 Testing

```bash
# Chạy toàn bộ test suite
.venv/bin/pytest tests/ -v

# Chạy riêng
.venv/bin/pytest tests/test_taxonomy.py              # Phân loại 14 nhóm
.venv/bin/pytest tests/test_pipeline_budget.py        # Pipeline + budget
.venv/bin/pytest tests/test_cache.py                 # SQLite 4-tier cache
.venv/bin/pytest tests/test_community_cache.py       # Community cache
.venv/bin/pytest tests/test_telemetry.py             # Telemetry + feedback
.venv/bin/pytest tests/test_new_providers_contract.py # 21 new providers contract
```

**Kết quả hiện tại:** 270/270 legacy tests + 62/62 new provider tests passed ✅

## 🔧 CLI Sandbox

Chạy pipeline độc lập không cần Anki:

```bash
python -m modules.sandbox --word "tactics" --sentence "Military tactics..." --stage all
```

Hiển thị: phân loại nhóm → visual_type → search candidates → CLIP scores → QC verdict.

## 📊 Hiệu năng

| Metric | Giá trị | Ghi chú |
|--------|---------|---------|
| Phân loại NLP | ~0.03 ms/từ | p95 = 0.036 ms |
| Nhóm dễ (0 AI) | 0.6–1.5 s/thẻ | A/B/C/H/K/N/M |
| Nhóm AI | 3–4 s/thẻ | Budget governor kẹp |
| AI calls/ngày | ~60–70 | Cho 3.000 thẻ |
| Nén ảnh | ≤800px, JPEG q80, ≤120KB | Tự động progressive |
| Eval accuracy | 100% (153/153 từ) | 14 nhóm A–N |

## 🛡️ Cache SQLite 4 tầng

| Tầng | Khóa | Nội dung | TTL |
|------|------|----------|-----|
| **L1** | word + sense_id | url + metadata | Vĩnh viễn |
| **L2** | word + sense_id | query đã tối ưu | Vĩnh viễn |
| **L3** | query | Top candidates | 30 ngày |
| **L4** | word + query | Negative cache | Vĩnh viễn |

Tính năng bổ sung:
- **Retry queue**: exponential backoff (30→60→120→240s), max 3 retries
- **Idle prefetch**: QTimer 300ms phát hiện rảnh → QueryOp xử lý nền
- **Community cache**: xuất/nhập pack L1/L2 ẩn danh, local-wins, version guard

## ⚙️ Cấu hình nâng cao

Mở **Tools → Add-ons → AnkiAI → Config** hoặc trực tiếp sửa `config.json`:

### Pipeline & Cache

| Key | Mặc định | Mô tả |
|-----|----------|-------|
| `clip_tier` | `"heuristic"` | CLIP tier: `onnx`, `heuristic`, `none` |
| `strict_accuracy_mode` | `false` | Bật → bỏ qua ảnh chưa QC |
| `card_latency_budget_ms` | `3500` | Ngân sách thời gian/thẻ |
| `idle_prefetch_enabled` | `true` | Prefetch nền khi rảnh |
| `idle_prefetch_batch` | `5` | Số thẻ prefetch mỗi chu kỳ |
| `telemetry_enabled` | `true` | Thu thập telemetry cục bộ |
| `url_only_mode` | `false` | Chỉ lưu URL, không tải ảnh |
| `groq_model` | `"llama-3.3-70b"` | Model Groq cho tạo query |
| `gemini_vision_model` | `"gemini-2.0-flash"` | Model Gemini cho Vision QC |
| `groq_batch_deadline_ms` | `8000` | Deadline cho batch AI |
| `min_candidates_before_ai_expand` | `3` | Nhóm D: số candidates tối thiểu |

### Provider keys (v6.1 mới)

| Key | Mặc định | Mô tả |
|-----|----------|-------|
| `provider_timeout_s` | `15` | HTTP timeout cho tất cả providers |
| `wikipedia_api_base` | `https://en.wikipedia.org/api/` | Wikipedia REST API base |
| `wikidata_api_base` | `https://www.wikidata.org/` | Wikidata SPARQL endpoint |
| `smithsonian_api_base` | `https://api.si.edu/` | Smithsonian Open Access |
| `smithsonian_api_key` | `""` | Smithsonian API key (tùy chọn) |
| `artic_api_base` | `https://api.artic.edu/` | Art Institute Chicago |
| `cleveland_api_base` | `https://openaccess-api.clevelandart.org/` | Cleveland Museum |
| `flickr_api_key` | `""` | Flickr API key |
| `themealdb_base` | `https://www.themealdb.com/api/` | TheMealDB |
| `bhl_api_base` | `https://www.biodiversitylibrary.org/api/` | Biodiversity Heritage Library |
| `iconify_base` | `https://api.iconify.design/` | Iconify icon search |
| `noun_project_client_id` | `""` | Noun Project OAuth2 |
| `noun_project_client_secret` | `""` | Noun Project OAuth2 |
| `openclipart_base` | `https://openclipart.org/` | Openclipart |
| `storyset_api_base` | `https://storyset.com/` | Storyset |
| `undraw_index_url` | `https://undraw.co/illustrations` | unDraw index |
| `undraw_accent_color` | `#6c63ff` | Màu accent cho unDraw SVG |
| `mermaid_base_url` | `https://mermaid.ink/` | Mermaid diagram |
| `quickchart_base_url` | `https://quickchart.io/` | QuickChart |
| `pollinations_base_url` | `https://image.pollinations.ai/` | Pollinations AI |
| `huggingface_api_token` | `""` | HuggingFace Inference |
| `huggingface_model` | `stabilityai/stable-diffusion-xl-base-1.0` | HuggingFace model |

## 🤝 Community Cache

Chia sẻ cache L1/L2 ẩn danh với cộng đồng:

- **Export**: chỉ chứa word, sense_id, group, visual_type, url, clip_score, source_provider, attribution — **KHÔNG** sentence, **KHÔNG** user data
- **Import**: local luôn thắng trên conflict
- **Format**: JSON pack version 1, trao đổi qua GitHub Release
- **Opt-in**: bật/tắt trong config (`community_cache_enabled`)

## 📈 Lịch sử phiên bản

| Phiên bản | Tháng | Nội dung |
|-----------|-------|----------|
| **6.1** | 8/2026 | 21 nguồn ảnh mới (Wikipedia, Wikidata, Smithsonian, Iconify, Mermaid, QuickChart, Pollinations AI, v.v.), config v10, provider registry v6 |
| **6.0** | 8/2026 | Pipeline Accuracy-First: 14 nhóm, CLIP, Vision QC, SQLite 4-tier, telemetry, community cache |
| 5.0 | 5/2026 | GIF providers, localization, smart routing |
| 4.0 | 1/2026 | DALL-E integration, batch processing |
| 3.0 | 2025 | Initial release |

## ⚠️ Ghi chú quan trọng

- **Tenor đã đóng cửa 30/6/2026** — Provider đã gỡ bỏ. Dùng KLIPY, GIPHY, Pixabay GIF thay thế. Key cũ `tenor_api_key` được bỏ qua an toàn.
- **Smart Selection AI cũ đã tắt** — Pipeline v6.0+ dùng CLIP reranker thay thế AI keyword từng thẻ. Bật `enable_clip_reranker=True` để kích hoạt.
- **SQLite thay JSON** — Cache cũ JSON tự động migrate sang SQLite khi khởi động.
- **21 provider mới tự kích hoạt** — Không cần config thêm cho các provider miễn phí. Provider cần key (Flickr, Noun Project, HuggingFace) chỉ chạy khi có key.
- **AI generation là chốt chặn cuối** — Pollinations/HuggingFace chỉ dùng khi tất cả provider khác thất bại, và BẮT BUỘC vision QC.

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — Kiến trúc code
- **[CHANGELOG.md](./CHANGELOG.md)** — Lịch sử thay đổi
- **[docs/guides/](docs/guides/)** — Hướng dẫn chi tiết (API reference, config, debug, GIF, v.v.)

## 📄 License

MIT License — xem file LICENSE.

---

*Made with ❤️ for the Anki community*

**Version 6.1.0** | August 2026 | Anki 24.04+
