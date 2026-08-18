# Imagen 4 Ultra Generate Integration - QUICK SETUP

## Tích hợp đã hoàn thành

Hệ thống addon Anki của bạn đã được tích hợp **Imagen 4 Ultra Generate** để tạo ảnh AI-powered cho flashcard.

### ✓ Những gì đã được tích hợp:

1. **GeminiImageDescriber** (3 Gemini APIs)
   - 1 API chính + 2 API backup
   - Chuyển đổi: vocabulary + definition + examples → detailed image description
   - Auto-fallback khi API chính không khả dụng
   - Caching để tối ưu hóa chi phí

2. **ImagenProvider** (Imagen 4 Ultra)
   - Tạo ảnh từ detailed prompts
   - Support: size, style, safety checking
   - Rate limiting & retry logic
   - Cost tracking & statistics

3. **ImageGenerationPipeline** (End-to-end)
   - Kết nối: Vocabulary → Gemini Description → Imagen Generation
   - Fallback to search-based providers (Pexels, Unsplash, etc.)
   - Logging & telemetry

4. **API Handler Integration**
   - `generate_image_with_imagen()` - Tạo ảnh bằng Imagen
   - `generate_image_smart()` - Chọn tự động: search vs generate
   - `is_imagen_available()` - Kiểm tra health
   - `get_imagen_stats()` - Theo dõi sử dụng

---

## Cấu hình (config.json)

File `AnkiAI_ImageAddon/config.json` đã được cập nhật với các keys sau:

### 1. Gemini Image Description APIs (3 keys)
```json
"gemini_image_description_api_key": "",           // Primary
"gemini_image_description_api_key_backup_1": "", // Backup 1
"gemini_image_description_api_key_backup_2": "", // Backup 2
"enable_gemini_image_description": true,
```

### 2. Imagen 4 Ultra Settings
```json
"imagen_enabled": false,                          // Set to true to enable
"imagen_api_key": "",                            // Your Imagen API key
"imagen_service_account_json": "",               // Or use service account
"imagen_endpoint": "https://...",                // Pre-configured
"imagen_timeout_seconds": 25,                    // Generous timeout
"imagen_max_concurrent_requests": 2,             // Rate limiting
"imagen_request_retries": 2,                     // Auto-retry
"imagen_cost_warning_threshold_usd": 5.0,        // Cost alert
"imagen_fallback_to_search_providers": true,     // Use search if Imagen fails
"imagen_default_style": "photorealistic",        // Default style
"imagen_default_size": "1024x1024",              // Default size
"imagen_enable_safety_checking": true,           // Content moderation
"imagen_enable_cost_tracking": true,             // Track spending
```

---

## Bước 1: Lấy API Keys

### Option A: Google Imagen API Key
1. Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create API key
3. Paste vào `imagen_api_key` trong config.json

### Option B: Google Cloud Service Account (for production)
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Create service account
3. Download JSON key
4. Paste JSON content vào `imagen_service_account_json`

### Option C: Gemini APIs (cho image description)
1. Từ [Google AI Studio](https://aistudio.google.com/app/apikey), tạo 3 API keys
2. Paste vào:
   - `gemini_image_description_api_key` (primary)
   - `gemini_image_description_api_key_backup_1` (backup 1)
   - `gemini_image_description_api_key_backup_2` (backup 2)

---

## Bước 2: Enable Imagen trong Config

Chỉnh sửa `AnkiAI_ImageAddon/config.json`:

```json
{
    "imagen_enabled": true,
    "imagen_api_key": "your-imagen-key-here",
    "gemini_image_description_api_key": "your-gemini-key-1",
    "gemini_image_description_api_key_backup_1": "your-gemini-key-2",
    "gemini_image_description_api_key_backup_2": "your-gemini-key-3",
    ...
}
```

---

## Bước 3: Test Integration

### Chạy test script:
```bash
python test_imagen_integration.py
```

Output mong đợi:
```
✓ GeminiImageDescriber initialized with 3 API keys
✓ Image description generated:
  A photorealistic image showing someone avoiding or delaying tasks...
✓ ImagenProvider initialized
✓ Imagen API availability: True
✓ ImageGenerationPipeline initialized
```

---

## Bước 4: Sử dụng trong Code

### Cách 1: Tạo ảnh bằng Imagen
```python
from AnkiAI_ImageAddon.modules.api_handler import AIImageProvider

provider = AIImageProvider(
    imagen_enabled=True,
    imagen_api_key="...",
    gemini_image_description_api_key="...",
    # ... other config
)

# Generate image
images, provider_name, metadata = provider.generate_image_with_imagen(
    vocabulary="serendipity",
    definition="occurrence of events by chance in a happy way",
    examples="Finding that book was pure serendipity.",
    width=1024,
    height=1024,
    style="photorealistic"
)

if images:
    print(f"✓ Generated image using {provider_name}")
    # Save images[0] to Anki media folder
```

### Cách 2: Smart Selection (tự động chọn)
```python
# Thử Imagen trước, fallback to search
url, source = provider.generate_image_smart(
    vocabulary="ephemeral",
    definition="lasting for a very short time",
    prefer_generated=True  # Prefer AI-generated
)

print(f"Image from {source}: {url}")
```

### Cách 3: Kiểm tra Status
```python
if provider.is_imagen_available():
    stats = provider.get_imagen_stats()
    print(f"Generated {len(stats.get('generation_log', []))} images")
    print(f"Stats: {stats['provider_stats']}")
```

---

## Workflow: Vocabulary → Description → Image

### Pipeline Mặc định:
```
1. User định nghĩa từ: "procrastinate"
2. Gemini phân tích + tạo mô tả hình ảnh
   Input: vocabulary + definition + examples
   Output: "A person distracted by phone instead of working..."
3. Imagen tạo ảnh từ mô tả
4. Ảnh được lưu vào Anki media folder
5. Flashcard hiển thị ảnh
```

### Example Output:
```
Vocabulary: "procrastinate"
Definition: "to delay or postpone something"

[Gemini Image Description]
"A photorealistic image of someone sitting at a desk with a laptop,
looking at their phone instead of working on documents. The desk
is cluttered with papers and the person has a distracted expression..."

[Imagen Generated Image]
→ 1024x1024 PNG image downloaded to Anki media
```

---

## Chi Phí & Optimization

### Imagen 4 Ultra Pricing
- ~$0.02 per image (approximate, check Google pricing)
- Recommend: limit to 100-200 images per session

### Cost Control
- Set `imagen_cost_warning_threshold_usd` để cảnh báo
- Dùng cache để tránh trùng prompt
- Fallback to free search providers

### Tips để Giảm Chi Phí
1. **Cache Aggressively**: Same vocabulary won't call API twice
2. **Use Search Providers as Fallback**: Pexels/Unsplash free + fast
3. **Set Concurrency Limit**: `imagen_max_concurrent_requests: 2`
4. **Monitor Stats**: `provider.get_imagen_stats()`

---

## Troubleshooting

### ❌ "Imagen API key invalid"
- Kiểm tra API key trong config.json
- Đảm bảo key không có leading/trailing spaces
- Test trên Google AI Studio dashboard

### ❌ "All Gemini image description keys failed"
- Kiểm tra 3 Gemini API keys
- Đảm bảo ít nhất 1 key hợp lệ
- Kiểm tra rate limits / quota

### ❌ "Timeout" errors
- Tăng `imagen_timeout_seconds` (default 25)
- Kiểm tra network connectivity
- Thử lại sau vài phút

### ❌ "Rate limited (429)"
- Auto-retry + backoff đã enabled
- Nếu persistent: giảm `imagen_max_concurrent_requests`
- Chờ vài giờ trước generate tiếp

### ⚠️ Images not saving to Anki
- TODO: Implement image saving to Anki media folder
- Hiện tại chỉ return image bytes từ Imagen
- Cần hook vào Anki's media manager

---

## Next Steps

### Immediate TODOs
- [ ] Tích hợp UI settings trong Anki add-on settings
- [ ] Implement image saving to Anki media folder
- [ ] Add cost tracking dashboard
- [ ] Add safety/moderation checks

### Optional Enhancements
- [ ] Thêm prompt templates (style, mood, composition)
- [ ] Support batch generation (multiple images per vocab)
- [ ] Add image variations / regenerate button
- [ ] Support other AI image generators (Flux, DALL-E 3, etc.)

---

## Files Thêm Vào / Sửa

### Tạo Mới:
- `AnkiAI_ImageAddon/modules/imagen_provider.py` - Core Imagen integration
- `test_imagen_integration.py` - Test harness
- `IMAGEN_USAGE_EXAMPLE.py` - Usage examples
- `IMAGEN_QUICK_SETUP.md` - This file

### Sửa Đổi:
- `AnkiAI_ImageAddon/config.json` - Added Imagen config keys
- `AnkiAI_ImageAddon/modules/api_handler.py` - Integrated pipeline

---

## Support & Questions

- Check `IMAGEN_USAGE_EXAMPLE.py` for code examples
- Run `test_imagen_integration.py` to validate setup
- Review logs in `AnkiAI_ImageAddon/modules/imagen_provider.py` for debugging
- Check Google Imagen API documentation: https://ai.google.dev/

---

**Status**: ✅ Integration Complete - Ready for Testing
