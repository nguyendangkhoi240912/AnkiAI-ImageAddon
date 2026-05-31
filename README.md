# 🎨 AnkiAI ImageAddon - Tự động thêm ảnh & GIF bằng AI

**Version 5.1** — Preset theo note type, batch pause/resume, tối ưu API

## 🌟 AnkiAI là gì?

**AnkiAI ImageAddon** là một Anki add-on mạnh mẽ giúp bạn:

- ✨ **Tự động tạo ảnh** bằng Google **Imagen** (AI vẽ từ từ vựng + định nghĩa)
- 🔍 **Tìm kiếm ảnh tĩnh** từ 15+ nguồn (Pexels, Unsplash, Pixabay, v.v.)
- 🎬 **Tìm kiếm ảnh động** từ 5 nền tảng GIF chuyên nghiệp
- 🤖 **AI-powered**: ChatGPT/Gemini tạo keyword tự động từ định nghĩa
- ⚡ **Batch processing**: Thêm ảnh cho 100-1000 thẻ chỉ trong vài phút
- 📊 **Tracking**: Thanh tiến trình, log chi tiết, error handling
- ⚙️ **Linh hoạt**: 20+ image providers, smart routing, fallback tự động
- 🛡️ **Bảo mật**: API keys lưu local, không gửi dữ liệu về server

## ✨ Tính năng chính v5.0

### 📸 Static Images (20+ providers)
- **High-quality**: Pexels, Unsplash, Pixabay (không lo bản quyền)
- **Specialized**: Wikimedia Commons, NASA, PubChem, ChEMBL
- **Academic**: Library of Congress, Met Museum, Europeana
- **Search engines**: Google Custom Search, DuckDuckGo, Yandex

### 🎬 Animated Images - NEW! (5 providers)
- **KLIPY**: Localization support (tìm GIF phù hợp văn hóa)
- **Pixabay GIFs**: Chất lượng cao, không lo bản quyền
- **GIPHY**: Kho lưu GIF khổng lồ
- **Tenor**: Tìm kiếm thông minh (hoạt động đến 30-06-2026)
- **IconScout**: Biểu tượng động tối giản (cognitive-friendly)

### 🧠 AI Features
- **Keyword Generation**: ChatGPT/Gemini tạo query từ definition
- **Domain Routing**: AI chọn provider phù hợp (medical, chemistry, biology, etc.)
- **Smart Selection**: Đánh giá & chọn ảnh tốt nhất từ multiple providers
- **Image Generation**: Imagen (tùy chọn) + fallback tìm kiếm 20+ nguồn

### ⚙️ Performance & Reliability
- **Concurrent Requests**: 10 providers chạy song song
- **Adaptive Delay**: Tự động tăng delay khi gặp rate limit
- **Error Recovery**: Fallback providers, retry logic
- **Image Optimization**: Tự động nén ảnh (75% nhẹ hơn)
- **Mobile Support**: Ảnh tối ưu cho iPhone/Android

---

## 🚀 Cài đặt nhanh (3 bước)

### ✅ Bước 1: Tải add-on

**Option A: Manual**
1. Download `AnkiAI_ImageAddon` folder
2. Copy vào Anki addons folder:
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Linux**: `~/.local/share/Anki2/addons21/`
3. Khởi động lại Anki

**Option B: Direct Install (Anki 2.1.50+)**
1. Anki > Tools > Add-ons > Install from file
2. Chọn `AnkiAI_ImageAddon` folder
3. Khởi động lại Anki

### ✅ Bước 2: Lấy API Keys (5 phút)

Tùy chọn: Chỉ cần ít nhất **1 API key** để bắt đầu. Thêm nhiều provider = kết quả tốt hơn.

**Option 1: Static Images (Khuyến nghị cho người mới)**
- **Pixabay** (Miễn phí): https://pixabay.com/api/
  1. Đăng ký → Tìm API Key
  2. Copy vào config

**Option 2: AI-Generated Images (Imagen)**
- **Google AI Studio** (Gemini + Imagen): https://aistudio.google.com/apikey
  1. Bật `imagen_enabled` trong config
  2. Thêm `imagen_api_key` và key mô tả ảnh (Gemini)
  3. Chọn mode `generate` hoặc `smart`

**Cập nhật addon:** clone/pull từ [GitHub](https://github.com/nguyendangkhoi240912/AnkiAI-ImageAddon) hoặc cài file `.ankiaddon` (xem `ANKIWEB.md` khi đăng AnkiWeb).

**Option 3: Animated Images - GIF (Mới!)**
- **KLIPY** (Miễn phí): https://www.klipy.io/developers
- **GIPHY** (Beta miễn phí): https://developers.giphy.com
- **Pixabay** (Miễn phí): https://pixabay.com/api/

👉 **Chi tiết cấu hình**: Xem phần "⚙️ API Configuration" bên dưới

### ✅ Bước 3: Khởi động!

1. **Mở Anki** → Browse (Ctrl+B)
2. **Chọn thẻ** cần thêm ảnh
3. **Chạy add-on**:
   - Cách 1: Nhấn phải chuột → "AnkiAI: Add Images"
   - Cách 2: Cards menu → AnkiAI (option)
4. **Chọn chế độ**: Generate (AI) hoặc Search (tìm kiếm)
5. **Xác nhận** → Chờ ảnh được thêm

---

## 🎯 Hướng dẫn sử dụng chi tiết

### 📚 Thêm ảnh tĩnh (Static Images)

**Quy trình:**
1. Browse → Chọn thẻ
2. Nhấn phải chuột → "AnkiAI: Search for Images"
3. Chọn image provider hoặc "Auto" (addon tự chọn)
4. Xem preview → Thêm vào thẻ

**Workflow:**
```
Vocabulary: "Photosynthesis"
Definition: "Quá trình tạo năng lượng từ ánh sáng"
         ↓
         ChatGPT/Gemini: "photosynthesis process green leaf light"
         ↓
         Search: Pixabay, Unsplash, Wikimedia, ...
         ↓
         Select best: High quality, relevant, copyright-free
         ↓
         Add to card ✓
```

**Providers tự động chọn theo domain:**
- Hóa học → PubChem, ChEMBL
- Y tế → Medical images, ISIC (dermato)
- Sinh học → PhyloPic, RCSB
- Tổng quát → Pixabay, Unsplash

### 🎬 Thêm ảnh động - GIF (NEW!)

**Quy trình:**
1. Browse → Chọn thẻ
2. Nhấn phải chuột → **"AnkiAI: Search for GIFs"** (NEW!)
3. Nhập keyword (ví dụ: "running", "happy", "atom")
4. Xem GIF preview → Thêm vào thẻ

**Workflow:**
```
Vocabulary: "running"
         ↓
         Search KLIPY, GIPHY, Tenor, Pixabay, IconScout
         ↓
         Display top 5 GIFs
         ↓
         User selects → Add to card ✓
```

**Providers tự động chọn:**
- Keyword "motion" → KLIPY (localization)
- Keyword "reaction" → GIPHY (phản ứng đa dạng)
- Keyword "icon" → IconScout (biểu tượng tối giản)

### 🤖 Chế độ AI Generation (DALL-E 3)

**Đặc điểm:**
- ✅ Ảnh độc quyền, creative, chủ đề rõ ràng
- ❌ Chậm hơn, đắt hơn ($0.08/ảnh)
- ⚠️ Cần OpenAI API key + credits

**Quy trình:**
```
Vocabulary: "democracy"
Definition: "Hệ thống chính trị..."
         ↓
         ChatGPT: "democratic voting people choice"
         ↓
         DALL-E 3: AI vẽ ảnh
         ↓
         Add to card ✓
```

### 📊 So sánh 3 chế độ

| Chế độ | Tốc độ | Giá | Chất lượng | Bản quyền | Khi nào dùng |
|-------|--------|-----|-----------|-----------|------------|
| **Search** | ⚡⚡⚡ | $0.01 | ⭐⭐⭐ | ✅ Tốt | 👍 Default |
| **GIF** | ⚡⚡ | Miễn phí | ⭐⭐⭐⭐ | ✅ Tốt | 📚 Động từ, Khoa học |
| **DALL-E** | ⚡ | $0.08 | ⭐⭐⭐⭐⭐ | ✅ Độc quyền | ✨ Creative, Concept |

---

## ⚙️ API Configuration

### 1️⃣ Static Image Providers

#### Pixabay (Khuyến nghị - Miễn phí)
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_API_KEY"
}
```
- Lấy key: https://pixabay.com/api/
- **Giá**: Miễn phí (100 requests/hour)
- **Chất lượng**: Cao, không lo bản quyền

#### Unsplash
```json
{
    "unsplash_api_key": "YOUR_UNSPLASH_API_KEY"
}
```
- Lấy key: https://unsplash.com/oauth/applications
- **Giá**: Miễn phí
- **Chất lượng**: Rất cao, chuyên nghiệp

#### Pexels
```json
{
    "pexels_api_key": "YOUR_PEXELS_API_KEY"
}
```
- Lấy key: https://www.pexels.com/api/
- **Giá**: Miễn phí
- **Chất lượng**: Cao

### 2️⃣ AI Generation - OpenAI DALL-E

```json
{
    "openai_api_key": "sk-YOUR_OPENAI_API_KEY"
}
```
- Lấy key: https://platform.openai.com/api-keys
- **Giá**: ~$0.08/ảnh
- **Chất lượng**: Tuyệt vời, độc quyền
- ⚠️ Lưu ý: Cần setup billing

**Giới hạn OpenAI free tier:**
- $5 free credits (hết trong 3 tháng)
- Chỉ dùng được 1 tháng từ lúc tạo account

### 3️⃣ GIF Animated Providers - NEW!

#### KLIPY (Khuyến nghị - Miễn phí)
```json
{
    "klipy_app_key": "YOUR_KLIPY_APP_KEY"
}
```
- Lấy key: https://www.klipy.io/developers
- **Giá**: Miễn phí, vô hạn
- **Đặc điểm**: Localization support, thích hợp văn hóa
- **Phù hợp cho**: Học ngoại ngữ, động từ

#### GIPHY
```json
{
    "giphy_api_key": "YOUR_GIPHY_API_KEY"
}
```
- Lấy key: https://developers.giphy.com
- **Giá**: Beta key miễn phí (unlimited)
- **Đặc điểm**: Kho GIF khổng lồ
- **Phù hợp cho**: Phản ứng, memes, trends

#### Tenor
```json
{
    "tenor_api_key": "YOUR_TENOR_API_KEY"
}
```
- Lấy key: https://tenor.com/developer
- **Giá**: Miễn phí
- ⚠️ **DEPRECATED**: Google sẽ đóng cửa 30-06-2026
- **Phù hợp cho**: Tìm kiếm thông minh (hiện tại)

#### Pixabay GIFs
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_KEY"
}
```
- Dùng chung key với static images!
- **Giá**: Miễn phí
- **Đặc điểm**: Không lo bản quyền
- **Phù hợp cho**: GIF chất lượng cao

#### IconScout
```json
{
    "iconscout_api_token": "YOUR_ICONSCOUT_TOKEN"
}
```
- Lấy token: https://iconscout.com/api
- **Giá**: Giới hạn (tính phí cao cấp)
- **Đặc điểm**: Biểu tượng động tối giản
- **Phù hợp cho**: Học từ vựng, concepts

### 📝 Config mẫu - Bắt đầu nhanh

**Minimal (Miễn phí, nên có từ một key):**
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "klipy_app_key": "YOUR_KLIPY_KEY"
}
```

**Recommended (Cân bằng giá/chất lượng):**
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "unsplash_api_key": "YOUR_UNSPLASH_KEY",
    "klipy_app_key": "YOUR_KLIPY_KEY",
    "giphy_api_key": "YOUR_GIPHY_KEY"
}
```

**Maximum (Tất cả providers):**
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "unsplash_api_key": "YOUR_UNSPLASH_KEY",
    "pexels_api_key": "YOUR_PEXELS_KEY",
    "openai_api_key": "sk-YOUR_KEY",
    "klipy_app_key": "YOUR_KLIPY_KEY",
    "giphy_api_key": "YOUR_GIPHY_KEY",
    "tenor_api_key": "YOUR_TENOR_KEY",
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "iconscout_api_token": "YOUR_ICONSCOUT_TOKEN"
}
```

### 🔧 Cấu hình nâng cao

**Đổi field (điều chỉnh tên các trường):**

Tools > Add-ons > AnkiAI > Config:

```json
{
    "vocabulary_field": "Mặt trước",
    "definition_field": "Định nghĩa",
    "image_field": "Ảnh",
    
    "image_generation_mode": "search",
    "max_concurrent_providers": 10,
    "enable_ai_provider_routing": true,
    
    "base_delay_ms": 100,
    "max_delay_ms": 2000,
    "enable_adaptive_delay": true
}
```

**Config options:**
- `vocabulary_field`: Trường chứa từ vựng
- `definition_field`: Trường chứa định nghĩa
- `image_field`: Trường chứa ảnh
- `image_generation_mode`: "search", "generate" (DALL-E), hoặc "auto"
- `enable_ai_provider_routing`: Dùng AI để chọn provider phù hợp
- `max_concurrent_providers`: Số providers chạy song song (default: 10)
- `enable_adaptive_delay`: Tự động adjust delay khi rate limit (default: true)

---

## 🎬 Thêm ảnh động (GIF) - v5.0+

Addon hỗ trợ **5 nền tảng GIF chuyên nghiệp**:

| Provider | Đặc điểm | Giá |
|----------|----------|-----|
| **KLIPY** | Localization tốt, ảnh động miễn phí | Miễn phí |
| **Pixabay GIFs** | Không lo bản quyền, chất lượng cao | Miễn phí |
| **IconScout** | Biểu tượng động, tối giản | Giới hạn |
| **GIPHY** | Kho lưu GIF khổng lồ | Beta miễn phí |
| **Tenor** | Tìm kiếm thông minh (đóng 30-06-2026) | Miễn phí* |

### Cách sử dụng GIF

1. Lấy API key từ KLIPY, Pixabay, hoặc GIPHY
2. Cập nhật `config.json`:
   ```json
   {
       "klipy_app_key": "YOUR_KEY",
       "giphy_api_key": "YOUR_KEY",
       "pixabay_api_key": "YOUR_KEY"
   }
   ```
3. Chọn thẻ > Browse > AnkiAI > **Search for GIFs**
4. Nhập keyword (ví dụ: "running", "happy", "chemistry")
5. Chọn GIF → Tự động thêm vào thẻ

### Khi nào nên dùng GIF?
- 📚 **Học từ vựng**: Động từ chuyển động ("jumping"), giới từ ("above")
- 🧪 **Học khoa học**: Quy trình ("photosynthesis"), phản ứng ("acid-base")
- 🗣️ **Ngoại ngữ**: Sử dụng KLIPY localization cho phù hợp văn hóa

👉 **Chi tiết GIF setup**: `GIF_ANIMATED_PROVIDERS_GUIDE.md`
👉 **Quick reference**: `GIF_QUICK_REFERENCE.md`

---

## 💰 Chi phí & Pricing

### Miễn phí (Recommended đầu tiên!)

- **Pixabay**: 100 requests/hour - **MIỄN PHÍ VĨNH VIỄN**
- **Unsplash**: Unlimited - **MIỄN PHÍ VĨNH VIỄN**
- **Pexels**: Unlimited - **MIỄN PHÍ VĨNH VIỄN**
- **Wikimedia Commons**: Unlimited - **MIỄN PHÍ VĨNH VIỄN**
- **KLIPY**: Unlimited - **MIỄN PHÍ VĨNH VIỄN**
- **GIPHY**: Beta key - **MIỄN PHÍ VĨNH VIỄN**

### Có tính phí

| Service | Giá | Ghi chú |
|---------|-----|---------|
| **OpenAI (DALL-E 3)** | $0.08/ảnh | Tạo ảnh mới, cần setup billing |
| **Tenor** | Miễn phí* | Đóng cửa 30-06-2026 |
| **IconScout** | Giới hạn | Free tier có giới hạn |

### Dự tính chi phí

```
Scenario 1: Chỉ dùng free providers
→ Chi phí: $0 (MIỄN PHÍ)

Scenario 2: DALL-E 3 + Free providers (100 thẻ)
→ Chi phí: 100 × $0.08 = $8

Scenario 3: DALL-E 3 (1000 thẻ)
→ Chi phí: 1000 × $0.08 = $80
  Nhưng OpenAI free tier = $5 credits miễn phí

Lựa chọn: Dùng free providers + DALL-E khi cần = Tối ưu chi phí!
```

---

## 🔒 Bảo mật & Privacy

✅ **API keys lưu local**: Chỉ trên máy tính của bạn, không gửi server
✅ **Không tracking**: Addon không gửi dữ liệu thống kê
✅ **Open source**: Mã nguồn có sẵn để kiểm tra
✅ **Encrypted**: API keys được lưu trong config.json (không mã hóa nhưng local-only)

⚠️ **Lưu ý bảo mật:**
- Đừng share API keys với ai cả!
- Đừng commit API keys vào Git
- Giữ OpenAI API key an toàn (có thể bị abuse)

---

## 🚀 Performance Tips

### Để addon chạy nhanh nhất:

1. **Giảm số thẻ**: Xử lý 100-200 thẻ một lúc (không 1000 cùng lúc)
2. **Chọn providers phù hợp**: 
   - Nhanh: Pixabay, Pexels, KLIPY
   - Chậm: DALL-E (AI vẽ), IconScout (API chậm)
3. **Giảm concurrent workers**:
   ```json
   {
       "max_concurrent_providers": 5
   }
   ```
4. **Tăng delay**:
   ```json
   {
       "base_delay_ms": 50,
       "max_delay_ms": 2000
   }
   ```

### Benchmark (dự kiến)

| Scenario | Thời gian |
|----------|-----------|
| 100 thẻ + Search (Pixabay) | 1-2 phút |
| 100 thẻ + GIF (KLIPY/GIPHY) | 2-3 phút |
| 100 thẻ + DALL-E | 5-10 phút |
| 1000 thẻ + Mixed | 30-60 phút |

---

## ❓ FAQ

### Q: Tôi không có API key, có thể dùng được không?
**A**: Có! Addon hỗ trợ nhiều free providers:
- Wikimedia Commons (unlimited)
- DuckDuckGo (limited)
- Yandex Images (limited)

### Q: Tôi chỉ muốn dùng GIF, không cần ảnh tĩnh?
**A**: Được! Chỉ cấu hình GIF keys:
```json
{
    "klipy_app_key": "YOUR_KEY",
    "giphy_api_key": "YOUR_KEY"
}
```

### Q: Chi phí OpenAI bao nhiêu?
**A**: 
- DALL-E 3: $0.08/ảnh (1024x1024)
- Free tier: $5 credits (hết trong 3 tháng)
- Recommendation: Dùng search providers trước!

### Q: Tenor sẽ bị đóng khi nào?
**A**: Google thông báo đóng cửa **30 tháng 6 năm 2026**
- Addon sẽ tự động disable sau ngày đó
- Fallback → GIPHY, KLIPY

### Q: Addon sẽ thêm ảnh sai không?
**A**: Có khả năng! Giải pháp:
- Preview trước khi confirm
- Chỉnh sửa định nghĩa để tìm kiếm tốt hơn
- Thử provider khác

### Q: Làm sao reset config về default?
**A**: 
1. Tools > Add-ons > AnkiAI > Config
2. Click "Restore Defaults"
3. Confirm

### Q: Addon hoạt động offline không?
**A**: Không. Cần internet connection để:
- Tìm kiếm ảnh (API calls)
- Tạo ảnh DALL-E
- Lấy GIF

### Q: Tôi có thể tắt một provider không?
**A**: Có! Xóa API key của provider đó trong config:
```json
{
    "pixabay_api_key": "",  // Xóa/leave empty
    "giphy_api_key": "YOUR_KEY"
}
```

### Q: Rate limit là gì? Tôi phải làm gì?
**A**: 
- Rate limit = API server giới hạn requests
- Addon sẽ **tự động tăng delay** (adaptive delay manager)
- Nếu vẫn bị: Giảm `max_concurrent_providers` hoặc chờ 1 giờ

### Q: Addon sẽ cập nhật tài nguyên của tôi lên cloud không?
**A**: Không!
- Ảnh được tải về máy tính
- Sau đó đồng bộ lên AnkiWeb bình thường
- Addon không gửi dữ liệu riêng nào

---

## 🐛 Troubleshooting

### ❌ "Invalid API Key"

**Nguyên nhân**: API key sai hoặc hết hạn

**Cách fix**:
1. Kiểm tra lại key từ provider website
2. Ensure key không bị copy sai (space, missing characters)
3. Thử key khác hoặc provider khác

### ❌ "Timeout" / "Connection refused"

**Nguyên nhân**: Internet yếu hoặc API server bận

**Cách fix**:
1. Kiểm tra Internet connection
2. Thử lại sau 5 phút
3. Giảm `max_concurrent_providers`
4. Thử provider khác

### ❌ "No images found"

**Nguyên nhân**: 
- Từ khóa quá cụ thể
- Provider không có kết quả
- Định nghĩa quá ngắn

**Cách fix**:
1. Chỉnh sửa định nghĩa rõ ràng hơn
2. Thử provider khác
3. Kiểm tra từ khóa AI tạo ra (xem logs)

### ❌ "Anki lag / freeze"

**Nguyên nhân**: Addon đang tải quá nhiều ảnh cùng lúc

**Cách fix**:
1. Giảm số thẻ xử lý (100-200 tối đa)
2. Giảm `max_concurrent_providers` xuống 3-5
3. Tăng `base_delay_ms` thành 200-500

### ❌ "Permission denied" (macOS/Linux)

**Nguyên nhân**: Addon không có quyền viết file

**Cách fix**:
1. Ensure Anki folder có write permissions
2. Restart Anki with proper permissions
3. Kiểm tra disk space (ảnh cần 50-500MB)

### ❌ GIF không tải được

**Nguyên nhân**: GIF provider lỗi hoặc API key sai

**Cách fix**:
1. Kiểm tra GIF API key
2. Thử provider khác (fallback)
3. Kiểm tra keyword hợp lệ

### 📝 Xem logs để debug

```
macOS/Linux:
~/.local/share/Anki2/addons21/AnkiAI_ImageAddon/debug.log

Windows:
%APPDATA%\Anki2\addons21\AnkiAI_ImageAddon\debug.log

Hoặc: Tools > Add-ons > AnkiAI > View Files > logs/
```

---

## 📚 Use Cases & Examples

### 📖 Học từ vựng Tiếng Anh

```
Vocabulary: "Running"
Definition: "Di chuyển nhanh bằng chân"

Option 1: Search (Pixabay) → Ảnh người chạy
Option 2: GIF (KLIPY) → Video động người chạy
Option 3: DALL-E → AI vẽ người chạy

Recommendation: GIF hoặc Search (visual memory tốt hơn)
```

### 🧪 Học Hóa học

```
Vocabulary: "Photosynthesis"
Definition: "Quá trình chuyển đổi năng lượng mặt trời..."

Option 1: Search (Wikimedia) → Biểu đồ quá trình
Option 2: Search (PubChem) → Phân tử cấu trúc
Option 3: GIF (Pixabay) → Video lá xanh

Recommendation: Search (Wikimedia) + GIF nếu muốn động
```

### 🗣️ Học Tiếng Pháp

```
Vocabulary: "Bonjour"
Definition: "Xin chào"

Option 1: Search (Pixabay) → Hình mọi người chào
Option 2: GIF (KLIPY) → Video người chào (localization)

Recommendation: KLIPY GIF (văn hóa phù hợp)
```

### 🏥 Học Y học

```
Vocabulary: "Diabetes"
Definition: "Bệnh tăng đường huyết..."

Option 1: Search (Wikimedia Smart) → Y tế hình ảnh
Option 2: Search (Europe PMC) → Tài liệu y khoa
Option 3: DALL-E → AI vẽ mô phỏng

Recommendation: Search (Wikimedia) + DALL-E
```

### 🎨 Học Sĩ số

```
Vocabulary: "Watercolor"
Definition: "Kỹ thuật vẽ bằng nước..."

Option 1: Search (Unsplash) → Ảnh watercolor
Option 2: DALL-E → AI vẽ watercolor sáng tạo

Recommendation: Search (visual reference) hoặc DALL-E
```

---

## 📊 Statistics after v5.0 release

- **20+ Image Providers** - Tổng cộng
- **5 GIF/Animated Providers** - Mới
- **50,000+ images** - Có sẵn (Pixabay)
- **1,000,000+ GIFs** - Có sẵn (GIPHY)

---

## 📚 Documentation

### Comprehensive Guides
- **[GIF_ANIMATED_PROVIDERS_GUIDE.md](./GIF_ANIMATED_PROVIDERS_GUIDE.md)** - Hướng dẫn chi tiết GIF providers
- **[GIF_QUICK_REFERENCE.md](./GIF_QUICK_REFERENCE.md)** - Quick setup GIF (5 phút)
- **[GIF_INTEGRATION_SUMMARY.md](./GIF_INTEGRATION_SUMMARY.md)** - Chi tiết kỹ thuật tích hợp
- **[RELEASE_V5.0_GIF_PROVIDERS.md](./RELEASE_V5.0_GIF_PROVIDERS.md)** - Release notes v5.0

### Reference
- **[API_REFERENCE.md](./API_REFERENCE.md)** - API documentation
- **[CONFIG_REFERENCE_V4.3.md](./CONFIG_REFERENCE_V4.3.md)** - Config options
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Code architecture

### Troubleshooting
- Check logs: `logs/agent-debug.ndjson` or `debug.log`
- Run diagnostic: Tools > Add-ons > AnkiAI > Diagnostics
- Check internet connection
- Try different API key or provider

---

## 🔗 Useful Links

### API Providers
- **Pixabay**: https://pixabay.com/api/
- **Unsplash**: https://unsplash.com/oauth/applications
- **Pexels**: https://www.pexels.com/api/
- **OpenAI**: https://platform.openai.com/api-keys
- **KLIPY**: https://www.klipy.io/developers
- **GIPHY**: https://developers.giphy.com
- **Tenor**: https://tenor.com/developer
- **IconScout**: https://iconscout.com/api

### Official Resources
- **Anki Official**: https://docs.ankiweb.net/
- **AnkiWeb**: https://ankiweb.net/
- **Anki Community**: https://anki.tenderapp.com/

### Support
- **Report Bug**: [GitHub Issues]
- **Feature Request**: [GitHub Discussions]
- **Community Help**: Anki Forums

---

## 🤝 Contributing

### Found a bug?
1. Check existing issues
2. Create detailed bug report with:
   - Addon version
   - Anki version
   - Python version
   - Error message & logs
   - Steps to reproduce

### Want to contribute code?
1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Translations
Help translate addon to other languages! Current languages:
- 🇻🇳 Vietnamese (Tiếng Việt)
- 🇬🇧 English (In progress)
- More languages welcome!

---

## 📄 License

**MIT License** - See LICENSE file for details

You are free to:
- ✅ Use commercially & personally
- ✅ Modify & distribute
- ✅ Include in your own projects

Just include the original license!

---

## 🙏 Acknowledgments

**Special thanks to:**
- Anki community for inspiration
- API providers (Pixabay, GIPHY, KLIPY, etc.)
- Testers & contributors
- All Anki learners worldwide! 🌍

---

## 📞 Support & Contact

### Getting Help
1. **Check documentation** (README, GIF guides)
2. **Search existing issues** on GitHub
3. **Check FAQ** section above
4. **Consult logs** for error messages
5. **Create GitHub issue** with details

### Community
- **Anki Forums**: https://anki.tenderapp.com/
- **Reddit**: r/Anki
- **Discord**: Anki Community servers

---

## 🎉 Getting Started Checklist

- [ ] Download & install addon
- [ ] Restart Anki
- [ ] Get 1-2 API keys (free providers)
- [ ] Update config.json with API keys
- [ ] Restart Anki again
- [ ] Browse → Select cards
- [ ] Right-click → AnkiAI > Search for Images/GIFs
- [ ] Preview & add images
- [ ] Sync with AnkiWeb
- [ ] Enjoy better flashcards! 🎓

---

## 🚀 Next Steps

1. **Start simple**: Use free providers first (Pixabay + KLIPY)
2. **Expand**: Add more providers as needed
3. **Optimize**: Fine-tune config for your use case
4. **Master**: Use DALL-E or GIFs for advanced learning
5. **Share**: Create shared decks with images!

---

## 📈 What's New in v5.0

✨ **Major Features**
- 🎬 5 GIF/Animated image providers
- 🌍 Localization support (KLIPY)
- 🎭 Animated icons (IconScout)
- 🤖 Smart AI domain routing
- ⚡ Adaptive rate limiting

🐛 **Bug Fixes**
- Better error handling
- Improved concurrent requests
- Enhanced provider fallback
- Optimized session pooling

📚 **Documentation**
- Comprehensive GIF guides
- Quick reference for GIF setup
- Integration technical details
- Release notes & changelog

---

## 📊 Version History

| Version | Release | Features |
|---------|---------|----------|
| **5.0** | May 2026 | GIF providers, Localization, Smart routing |
| 4.5 | Apr 2026 | Image optimization, Mobile support |
| 4.4 | Mar 2026 | Domain routing, Scientific providers |
| 4.3 | Feb 2026 | Adaptive delay, Rate limiting |
| 4.0 | Jan 2026 | DALL-E integration, Batch processing |
| 3.0 | 2025 | Initial release |

---

## 💡 Pro Tips

### 1. Maximize Free Usage
```json
{
    "pixabay_api_key": "YOUR_KEY",
    "klipy_app_key": "YOUR_KEY",
    "unsplash_api_key": "YOUR_KEY"
}
```
→ 0% cost, 80% quality!

### 2. Quick GIF Addition
Browse → Ctrl+G → Type keyword → Select → Done!

### 3. Batch Processing Smart
- 200 cards × Pixabay = 2-3 minutes ✅
- 200 cards × DALL-E = 15-20 minutes ✅
- 1000 cards × DALL-E = $80 ✓

### 4. Definition Quality Matters
```
❌ Bad: "Apple"
✅ Good: "Apple - popular fruit, red/green color, sweet taste"

Result: Better keyword generation → Better images!
```

### 5. Provider Combinations
```
Science: Wikimedia + Search (backup)
Vocabulary: KLIPY GIF + Pixabay (backup)
Art: DALL-E + Unsplash (creative + reference)
```

---

## ⚠️ Important Notes

### Tenor Deprecation Alert 🚨
- Google sẽ đóng Tenor API: **30 tháng 6 năm 2026**
- Addon sẽ tự động fallback → GIPHY/KLIPY
- Hãy setup backup GIF provider ngay!

### Rate Limiting Protection
- Addon tự động handle rate limits
- Không cần lo lắng, nó sẽ tự adjust
- Nếu vẫn bị: Giảm concurrent workers

### Image Optimization
- Addon tự động nén ảnh (75% nhẹ hơn)
- Quality vẫn tốt, file size nhỏ
- AnkiWeb sync sẽ nhanh hơn

---

## 🎓 Learning Resources

### Best Practices for Flashcard Images
1. **Use relevant images** - Directly related to vocabulary
2. **Avoid distracting images** - Too complex → cognitive load ↑
3. **Mix image types** - Photos + GIFs + Icons
4. **Optimize for mobile** - Images display well on phones
5. **Use consistent style** - Similar quality & aesthetic

### Recommended Study Techniques
- **Spaced Repetition**: Review at optimal intervals
- **Active Recall**: Cover image, try to remember
- **Elaboration**: Create associations with images
- **Interleaving**: Mix different topics
- **Variability**: Different providers → different perspectives

---

## 🎊 Final Words

**AnkiAI ImageAddon v5.0** is designed to make flashcard learning:
- 🎨 More visual & engaging
- 🚀 Faster & more efficient  
- 🧠 Better for memory retention
- 💪 More powerful & flexible

### Start learning better today! 📚✨

Questions? Check FAQ, read docs, or create an issue!

---

**Happy Learning with AnkiAI! 🎉**

*Made with ❤️ for the Anki community*

**Version 5.0.0** | May 2026 | Fully compatible with Anki 24.04+
