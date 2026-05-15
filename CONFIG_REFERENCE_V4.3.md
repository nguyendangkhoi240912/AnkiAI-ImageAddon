# 📋 Config Reference v4.3 - Chi Tiết Tất Cả Settings

**File Config**: `AnkiAI_ImageAddon/config.json`  
**Total Settings**: 42  
**Phiên Bản**: v4.3 (May 3, 2026)

---

## 🔧 Hướng Dẫn Sử Dụng

### Các Bước:
1. Mở `config.json` trong text editor
2. Tìm setting cần sửa
3. Thay đổi giá trị (giữ nguyên format JSON)
4. Lưu file
5. Khởi động lại Anki

---

## 📚 Chi Tiết Từng Setting

### 🤖 AI Providers (Cần Ít Nhất 1)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `gemini_api_key` | string | `""` | API Key Gemini để generate từ khóa (bắt buộc nếu không dùng Groq) |
| `gemini_eval_api_key` | string | `""` | API Key Gemini để đánh giá ảnh (tùy chọn) |
| `gemini_eval_api_key_backup` | string | `""` | Backup API Key thứ 2 cho đánh giá ảnh |
| `gemini_backup_api_key` | string | `""` | Backup API Key thứ 3 (tùy chọn - eval fallback) |
| `gemini_keyword_api_key_backup` | string | `""` | Backup API Key thứ 4 (tùy chọn - keyword fallback) |
| `groq_api_key` | string | `""` | API Key Groq (alternative: nhanh hơn Gemini) |
| `use_ollama` | boolean | `false` | Sử dụng Ollama local (không cần internet) |
| `ollama_url` | string | `"http://localhost:11434"` | URL Ollama local server |

**Ví Dụ**:
```json
{
  "gemini_api_key": "AIzaSyDXXXXXXXXXXXXXXXXXXXXXX",
  "gemini_eval_api_key": "AIzaSyYYYYYYYYYYYYYYYYYYYYYY",
  "groq_api_key": ""
}
```

---

### 🖼️ Image Providers (15+ Nguồn Ảnh)

#### Premium Providers (Cần API Key)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `pexels_api_key` | string | `""` | API Key Pexels (chất lượng cao) |
| `unsplash_api_key` | string | `""` | API Key Unsplash (ảnh chuyên nghiệp) |
| `pixabay_api_key` | string | `""` | API Key Pixabay (nhiều ảnh) |
| `wallhaven_api_key` | string | `""` | API Key Wallhaven (ảnh art/anime) |
| `flickr_api_key` | string | `""` | API Key Flickr (ảnh cộng đồng) |
| `europeana_api_key` | string | `""` | API Key Europeana (bảo tàng/lịch sử) |

#### Google Custom Search

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `google_api_key` | string | `""` | API Key Google Custom Search |
| `google_cx` | string | `""` | Google Custom Search Engine ID (cx) |

#### Free Providers (Không Cần Key)
- Openverse, Lorem Picsum, NASA, LOC (Library of Congress), Wikimedia, Smithsonian, Met Museum, FlagsAPI

---

### ⚡ Adaptive Delay System (v4.3 NEW!)

| Setting | Kiểu | Mặc Định | Phạm Vi | Ý Nghĩa |
|---------|------|---------|--------|--------|
| `enable_adaptive_delay` | boolean | `true` | - | Bật/tắt hệ thống delay để tránh bị IP ban |
| `base_delay_ms` | integer | `100` | 50-500 | Độ trễ cơ bản giữa requests (ms) |
| `max_delay_ms` | integer | `2000` | 1000-5000 | Delay tối đa không vượt quá (ms) |
| `delay_increase_on_429` | integer | `500` | 200-1000 | Tăng delay khi gặp rate limit 429 (ms) |
| `delay_increase_on_timeout` | integer | `200` | 100-500 | Tăng delay khi timeout (ms) |
| `delay_reset_hours` | integer | `1` | 1-24 | Số giờ không fail để reset delay (giờ) |

**Tuning Profiles**:

```json
// Profile 1: Nhanh (Aggressive)
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 50,
  "max_delay_ms": 1000
}

// Profile 2: Cân Bằng (Balanced - DEFAULT ✅)
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 100,
  "max_delay_ms": 2000
}

// Profile 3: An Toàn (Safe)
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 200,
  "max_delay_ms": 3000
}

// Profile 4: Siêu Bảo Vệ (Ultra Safe)
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 300,
  "max_delay_ms": 5000
}
```

---

### 🔍 Smart Selection (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `enable_smart_selection` | boolean | `true` | Tìm ảnh từ nhiều provider (concurrent) |
| `max_concurrent_providers` | integer | `6` | Số provider tìm kiếm cùng lúc (1-15) |
| `smart_cache_ttl_minutes` | integer | `120` | Cache kết quả tìm kiếm (phút) |

**Giải Thích**:
- `enable_smart_selection: true` → Addon tìm ảnh từ 15 providers cùng lúc
- `max_concurrent_providers: 6` → Cùng lúc tìm từ 6 providers (ba lô nhất là 6)

---

### 🛡️ Rate Limit Protection (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `enable_rate_limit_protection` | boolean | `true` | Pause provider khi bị rate limit |
| `rate_limit_pause_duration` | integer | `60` | Bao lâu để pause (giây) |

**Flow**:
```
1. Addon detect 429 (rate limit error)
2. Pause provider 60s
3. Sau 60s → Resume provider
```

---

### 📥 Image Evaluation (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `enable_ai_evaluation` | boolean | `true` | Dùng Gemini Vision để chọn ảnh tốt nhất |

**Khi Bật**:
- Addon download 3-5 ảnh từ providers
- Gemini đánh giá ảnh: kích thước, chất lượng, liên quan
- Chọn ảnh tốt nhất

---

### 🖼️ Image Optimization (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `image_download_timeout` | integer | `15` | Timeout download ảnh (giây) |
| `image_download_retries` | integer | `2` | Số lần retry khi download fail |
| `enable_image_optimization` | boolean | `true` | Tối ưu hóa kích thước/chất lượng ảnh |
| `image_max_width` | integer | `800` | Độ rộng tối đa ảnh (pixel) |
| `image_quality` | integer | `80` | Chất lượng ảnh: 0-100 (80 = cân bằng) |

**Ví Dụ**:
```json
// Chất lượng cao, file size lớn
{
  "image_max_width": 1200,
  "image_quality": 95
}

// Chất lượng thấp, file size nhỏ
{
  "image_max_width": 400,
  "image_quality": 60
}
```

---

### 💾 Caching (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `enable_keyword_cache` | boolean | `true` | Cache từ khóa generate từ AI |
| `keyword_cache_size` | integer | `1000` | Tối đa bao nhiêu keyword trong cache |

**Hiệu Quả**:
- Lần 1 "apple": Gemini generate từ khóa → cache (1-2 giây)
- Lần 2 "apple": Từ cache → instant (~100ms)

---

### 📝 Field Names (Anki Deck Fields)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `vocabulary_field` | string | `"Mặt trước"` | Field chứa từ vựng (vocabulary) |
| `definition_field` | string | `"Định nghĩa"` | Field chứa định nghĩa |
| `image_field` | string | `"Ảnh"` | Field để lưu ảnh |

**Cách Sử Dụng**:
```
Nếu deck của bạn có fields: English, Vietnamese, Picture
Đổi config:
{
  "vocabulary_field": "English",
  "definition_field": "Vietnamese",
  "image_field": "Picture"
}
```

---

### ⚙️ Concurrency & Performance (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `max_concurrent_requests` | integer | `5` | Max yêu cầu concurrent (1-20) |
| `enable_concurrent_downloads` | boolean | `true` | Download ảnh song song |

**Config Mạnh**:
```json
{
  "max_concurrent_requests": 10,
  "enable_concurrent_downloads": true
}
```

**Config Yếu (Internet Chậm)**:
```json
{
  "max_concurrent_requests": 2,
  "enable_concurrent_downloads": false
}
```

---

### 📋 Miscellaneous (v4.2)

| Setting | Kiểu | Mặc Định | Ý Nghĩa |
|---------|------|---------|--------|
| `image_generation_mode` | string | `"search"` | "search" = tìm ảnh, "generate" = tạo ảnh AI |
| `auto_add_on_sync` | boolean | `false` | Tự động thêm ảnh khi sync |

---

## 🎯 Quick Presets

### Preset 1: Hiệu Năng Tối Đa (Performance Max)
```json
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 50,
  "max_delay_ms": 1000,
  "max_concurrent_providers": 8,
  "max_concurrent_requests": 10,
  "enable_concurrent_downloads": true,
  "image_quality": 70,
  "image_max_width": 600
}
```

### Preset 2: Cân Bằng (Balanced - DEFAULT)
```json
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 100,
  "max_delay_ms": 2000,
  "max_concurrent_providers": 6,
  "max_concurrent_requests": 5,
  "enable_concurrent_downloads": true,
  "image_quality": 80,
  "image_max_width": 800
}
```

### Preset 3: Chất Lượng Cao (High Quality)
```json
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 200,
  "max_delay_ms": 3000,
  "max_concurrent_providers": 4,
  "max_concurrent_requests": 3,
  "enable_concurrent_downloads": false,
  "image_quality": 95,
  "image_max_width": 1200
}
```

### Preset 4: An Toàn Tuyệt Đối (Ultra Safe)
```json
{
  "enable_adaptive_delay": true,
  "base_delay_ms": 300,
  "max_delay_ms": 5000,
  "max_concurrent_providers": 3,
  "max_concurrent_requests": 2,
  "enable_concurrent_downloads": false,
  "image_quality": 70,
  "image_max_width": 600
}
```

---

## 🚨 Troubleshooting by Setting

### Vấn Đề: Addon quá chậm

**Giải pháp**:
```json
{
  "base_delay_ms": 50,
  "max_concurrent_providers": 8,
  "enable_concurrent_downloads": true
}
```

### Vấn Đề: Vẫn bị 429 (rate limit)

**Giải pháp**:
```json
{
  "base_delay_ms": 200,
  "delay_increase_on_429": 1000,
  "max_delay_ms": 3000
}
```

### Vấn Đề: Download ảnh fail

**Giải pháp**:
```json
{
  "image_download_timeout": 30,
  "image_download_retries": 5
}
```

### Vấn Đề: Ảnh chất lượng tệ

**Giải pháp**:
```json
{
  "image_quality": 95,
  "image_max_width": 1200,
  "enable_ai_evaluation": true
}
```

### Vấn Đề: Từ khóa không chính xác

**Kiểm tra**:
```json
{
  "gemini_api_key": "Có giá trị không?",
  "enable_keyword_cache": true
}
```

---

## 📊 Comparison: v4.2 vs v4.3

| Tính Năng | v4.2 | v4.3 |
|---|---|---|
| Adaptive Delay | ❌ | ✅ (NEW) |
| Per-Provider Delay | ❌ | ✅ (NEW) |
| Auto Reset Delay | ❌ | ✅ (NEW) |
| 15+ Image Providers | ✅ | ✅ |
| Smart Selection | ✅ | ✅ |
| Rate Limit Protection | ✅ | ✅ (Enhanced) |
| AI Evaluation | ✅ | ✅ |
| Caching | ✅ | ✅ |

---

## 💡 Pro Tips

### Tip 1: Backup Config
```bash
cp config.json config.json.backup
```
Nếu có vấn đề, khôi phục từ backup.

### Tip 2: Validate JSON
Trước khi save, kiểm tra JSON hợp lệ:
- Online: https://jsonlint.com
- Hoặc dùng VS Code → Extensions → JSON Validator

### Tip 3: Monitor Config Changes
Nếu config thay đổi, khởi động lại Anki để apply.

### Tip 4: Environment-Specific Config
Dùng các presets khác nhau trên máy khác:
- Laptop yếu: Preset 4 (Safe)
- Desktop mạnh: Preset 1 (Performance)
- Server: Preset 3 (Quality)

---

## ✅ Checklist: Config Setup

- [ ] Mở `config.json` trong text editor
- [ ] Thêm Gemini API Key (bắt buộc)
- [ ] (Optional) Thêm ít nhất 1 Image Provider key
- [ ] Kiểm tra JSON format hợp lệ
- [ ] Lưu file
- [ ] Khởi động lại Anki
- [ ] Test: Add image 1 lần → Kiểm tra hoạt động

---

**Document Version**: v1.0  
**Last Updated**: May 3, 2026  
**Status**: ✅ Complete & Ready
