# 🎨 AnkiAI ImageAddon

**Phiên bản 6.0** — Pipeline Accuracy-First: phân loại 14 nhóm → CLIP rerank → Vision QC

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

## ✨ Kiến trúc Pipeline v6.0

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

## 🚀 Cài đặt

### Yêu cầu
- Anki 24.04+ (Qt6)
- API keys (xem bên dưới)

### Cài đặt

**Option A: Từ file .ankiaddon**
1. Download `AnkiAI_ImageAddon-6.0.0.ankiaddon`
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

### Miễn phí (khuyến nghị)

| Provider | Key config | Lấy key |
|----------|-----------|---------|
| **Pixabay** | `pixabay_api_key` | https://pixabay.com/api/ |
| **Wikimedia** | không cần key | — |
| **KLIPY (GIF)** | `klipy_app_key` | https://www.klipy.io/developers |
| **GIPHY** | `giphy_api_key` | https://developers.giphy.com |

### AI (cần cho nhóm khó D/E/F/G/I/J/L)

| Provider | Key config | Mục đích | Lấy key |
|----------|-----------|----------|---------|
| **Groq** | `groq_api_key` | Tạo query, mở rộng search | https://console.groq.com |
| **Gemini** | `gemini_api_key` | Vision QC (kiểm chứng ảnh) | https://aistudio.google.com/apikey |

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
    "groq_api_key": "YOUR_KEY",
    "gemini_api_key": "YOUR_KEY"
}
```

## 📦 Cấu trúc dự án

```
AnkiAI_ImageAddon/
├── __init__.py                  # Entry point + AddImageTask
├── modules/
│   ├── config.py                # Quản lý cấu hình (v9, upgrader)
│   ├── pipeline.py              # Orchestrator Accuracy-First + budget governor
│   ├── cache.py                 # SQLite 4-tier + retry queue + community cache
│   ├── bg_handler.py            # BackgroundProcessor + RetryQueue + IdlePrefetch
│   ├── telemetry.py             # TelemetryCollector + suggest_adjustments
│   ├── quota.py                 # QuotaManager + degrade chain
│   ├── reranker.py              # CLIP gate + bias theo nhóm
│   ├── image_handler.py         # Tải, nén, lưu ảnh vào Anki media
│   ├── ui.py                    # ConfigDialog, FeedbackWidget, QuotaDisplay
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
│   └── local_svg_provider.py    # Data-URI SVG, 0 network
├── user_files/                  # Dữ liệu runtime (không commit)
│   ├── cache.sqlite             # SQLite 4-tier cache
│   ├── models/                  # CLIP/WordNet models
│   ├── eval_set/                # Eval set 153 từ gán nhãn
│   └── concept_metaphor_map.json
└── tests/                       # 270 tests
```

## 🧪 Testing

```bash
# Chạy toàn bộ test suite
.venv/bin/pytest tests/ -v

# Chạy riêng
.venv/bin/pytest tests/test_taxonomy.py      # Phân loại 14 nhóm
.venv/bin/pytest tests/test_pipeline_budget.py  # Pipeline + budget
.venv/bin/pytest tests/test_cache.py         # SQLite 4-tier cache
.venv/bin/pytest tests/test_community_cache.py  # Community cache
.venv/bin/pytest tests/test_telemetry.py     # Telemetry + feedback
```

**Kết quả hiện tại:** 270/270 tests passed ✅

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

## 🤝 Community Cache

Chia sẻ cache L1/L2 ẩn danh với cộng đồng:

- **Export**: chỉ chứa word, sense_id, group, visual_type, url, clip_score, source_provider, attribution — **KHÔNG** sentence, **KHÔNG** user data
- **Import**: local luôn thắng trên conflict
- **Format**: JSON pack version 1, trao đổi qua GitHub Release
- **Opt-in**: bật/tắt trong config (`community_cache_enabled`)

## 📈 Lịch sử phiên bản

| Phiên bản | Tháng | Nội dung |
|-----------|-------|----------|
| **6.0** | 8/2026 | Pipeline Accuracy-First: 14 nhóm, CLIP, Vision QC, SQLite 4-tier, telemetry, community cache |
| 5.0 | 5/2026 | GIF providers, localization, smart routing |
| 4.0 | 1/2026 | DALL-E integration, batch processing |
| 3.0 | 2025 | Initial release |

## ⚠️ Ghi chú quan trọng

- **Tenor đã đóng cửa 30/6/2026** — Provider đã gỡ bỏ. Dùng KLIPY, GIPHY, Pixabay GIF thay thế. Key cũ `tenor_api_key` được bỏ qua an toàn.
- **Smart Selection AI cũ đã tắt** — Pipeline v6.0 dùng CLIP reranker thay thế AI keyword từng thẻ. Bật `enable_clip_reranker=True` để kích hoạt.
- **SQLite thay JSON** — Cache cũ JSON tự động migrate sang SQLite khi khởi động.

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — Kiến trúc code
- **[CHANGELOG.md](./CHANGELOG.md)** — Lịch sử thay đổi
- **[docs/guides/](docs/guides/)** — Hướng dẫn chi tiết (API reference, config, debug, GIF, v.v.)

## 📄 License

MIT License — xem file LICENSE.

---

*Made with ❤️ for the Anki community*

**Version 6.0.0** | August 2026 | Anki 24.04+
