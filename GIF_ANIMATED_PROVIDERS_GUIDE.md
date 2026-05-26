# 🎬 Hướng dẫn các nguồn ảnh động GIF - AnkiAI ImageAddon v5.0

Addon đã tích hợp **5 nền tảng cung cấp ảnh động (GIF)** chuyên nghiệp. Hướng dẫn này sẽ giúp bạn cấu hình và sử dụng các provider này để làm phong phú thẻ flashcard của mình.

---

## 📋 Danh sách các GIF Provider

### 1. 🎯 KLIPY API - Nền tảng ảnh động miễn phí tối ưu

#### Đặc điểm nổi bật:
- **Miễn phí hoàn toàn** cho các ứng dụng cá nhân
- Hỗ trợ **định vị địa lý (Localization)** mạnh mẽ
- Dễ dàng truy cập trực tiếp vào URLs tệp tin GIF chất lượng cao
- Hỗ trợ cả GIF và MP4

#### Điểm mạnh cho Anki:
- Tìm kiếm ảnh động thích hợp với ngôn ngữ và văn hóa từng quốc gia
- **Cực kỳ hữu ích khi học Ngoại ngữ**
- Định dạng API trả về cho phép nhúng trực tiếp vào thẻ Anki

#### Cách lấy API Key:
1. Truy cập: https://www.klipy.io/developers
2. Đăng ký tài khoản (hoặc đăng nhập nếu đã có)
3. Tạo "App Key" mới
4. Copy **App Key** vào config

#### Cấu hình:
```json
{
    "klipy_app_key": "YOUR_KLIPY_APP_KEY_HERE"
}
```

#### Giá cả:
- **Miễn phí** cho cá nhân
- Không giới hạn API calls

---

### 2. 🎨 Pixabay GIFs - Ảnh động chất lượng cao, không lo bản quyền

#### Đặc điểm nổi bật:
- Hàng chục nghìn **ảnh GIF chất lượng cao**
- Bao gồm: phản ứng hài hước, động vật, hiệu ứng nghệ thuật
- **Không bắt buộc ghi công tác giả**
- Hỗ trợ cấp phép miễn phí cho cả mục đích thương mại

#### Điểm mạnh cho Anki:
- **Không lo vấn đề bản quyền** khi chia sẻ bộ thẻ (Shared Decks)
- Tất cả tài nguyên được cấp phép sử dụng miễn phí
- Đồng bộ trực tiếp GIF gốc vào bộ sưu tập

#### Cách lấy API Key:
1. Truy cập: https://pixabay.com/api/
2. Đăng ký tài khoản (hoặc đăng nhập)
3. Tạo API Key mới
4. Copy key vào config

#### Cấu hình:
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_API_KEY_HERE"
}
```

#### Giá cả:
- **Miễn phí** (100 requests/hour)
- Phiên bản premium có sẵn nếu cần nhiều requests

---

### 3. 🎭 IconScout - Chuyên về biểu tượng động

#### Đặc điểm nổi bật:
- **335.000+ biểu tượng hoạt họa**
- Định dạng: GIF, Lottie JSON, SVG, MP4
- Thiết kế tối giản và chuyên nghiệp

#### Điểm mạnh cho Anki:
- **Hiệu quả cho học từ vựng**: động từ, giới từ chỉ vị trí
- **Lý tưởng cho các quy trình khoa học phức tạp**
- Biểu tượng động tối giản giảm tải nhận thức (cognitive load)
- Giúp não bộ ghi nhớ bối cảnh chính xác và nhanh hơn

#### Cách lấy API Token:
1. Truy cập: https://iconscout.com/api
2. Đăng ký/Đăng nhập
3. Tạo API token
4. Copy token vào config (tùy chọn - một số chức năng miễn phí)

#### Cấu hình:
```json
{
    "iconscout_api_token": "YOUR_ICONSCOUT_TOKEN_HERE"
}
```

#### Giá cả:
- Một số chức năng **miễn phí**
- Gói premium có sẵn để truy cập đầy đủ

---

### 4. 🌟 GIPHY - Thư viện GIF lớn nhất thế giới

#### Đặc điểm nổi bật:
- **"Ông vua"** của GIF toàn cầu
- Số lượng ảnh động lên đến hàng triệu
- Phản ứng (reaction GIFs) phổ biến

#### Điểm mạnh cho Anki:
- Kho lưu trữ **cực kỳ phong phú**
- Hỗ trợ mô hình tính phí nhưng có Beta key cho cá nhân
- Tìm kiếm thủ công hoặc API

#### Cách lấy API Key:
1. Truy cập: https://developers.giphy.com
2. Tạo một app mới
3. Xin Beta key hoặc API key
4. Copy vào config

#### Cấu hình:
```json
{
    "giphy_api_key": "YOUR_GIPHY_API_KEY_HERE"
}
```

#### Giá cả:
- **Beta key miễn phí** cho cá nhân
- Phiên bản thương mại có tính phí

---

### 5. ⏳ Tenor - Thư viện ảnh động khổng lồ từ Google

#### Đặc điểm nổi bật:
- Kho lưu trữ **GIF và Sticker cực kỳ phổ biến**
- Tích hợp vào bàn phím ảo và ứng dụng nhắn tin
- Công cụ tìm kiếm thông minh

#### Điểm mạnh cho Anki:
- **Gợi ý từ khóa liên quan** thông minh
- Tìm kiếm và lọc nội dung vô cùng tinh tế
- Ví dụ: "evil smile", "big smile" khi gõ "smile"

#### ⚠️ Lưu ý quan trọng:
**Google đã thông báo kế hoạch đóng cửa API Tenor vào 30 tháng 6 năm 2026**

💡 **Khuyến nghị**: Nếu xây dựng tự động hóa, hãy ưu tiên các nền tảng khác như KLIPY hoặc Pixabay

#### Cách lấy API Key:
1. Truy cập: https://tenor.com/developer
2. Tạo app mới
3. Xin API key
4. Copy vào config (nhanh - thời gian có hạn!)

#### Cấu hình:
```json
{
    "tenor_api_key": "YOUR_TENOR_API_KEY_HERE"
}
```

#### Giá cả:
- **Miễn phí** (sẽ đóng cửa 30-06-2026)

---

## 🛠️ Cấu hình hoàn chỉnh

Dưới đây là cấu hình đầy đủ để sử dụng tất cả GIF provider:

```json
{
    "klipy_app_key": "YOUR_KLIPY_KEY",
    "giphy_api_key": "YOUR_GIPHY_KEY",
    "tenor_api_key": "YOUR_TENOR_KEY",
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "iconscout_api_token": "YOUR_ICONSCOUT_TOKEN",
    
    "enable_ai_provider_routing": true,
    "max_concurrent_providers": 10,
    "enable_adaptive_delay": true,
    "base_delay_ms": 100,
    "max_delay_ms": 2000
}
```

---

## 🚀 Cách sử dụng

### Tùy chọn 1: Giao diện Browse (Recommended)

1. **Mở Anki**
2. **Browse** (Ctrl+B) → Chọn thẻ
3. **AnkiAI > Search for GIFs** → Nhập keyword (ví dụ: "running", "happy", "chemistry")
4. **Chọn GIF** → Tự động thêm vào thẻ

### Tùy chọn 2: Auto-add trên Sync

Cấu hình `"auto_add_on_sync": true` để addon tự động tìm và thêm GIF khi bạn sync bộ sưu tập.

---

## 💡 Mẹo sử dụng

### Cho học từ vựng:
- **Động từ**: "running", "jumping", "crying"
- **Giới từ chỉ vị trí**: "on top of", "beside", "under"
- **Tính từ**: "happy", "sad", "angry"

### Cho học khoa học:
- **Phản ứng hóa học**: "electron transfer", "acid-base"
- **Quá trình sinh học**: "photosynthesis", "mitosis"
- **Vật lý**: "wave motion", "pendulum"

### Cho học ngoại ngữ:
- Sử dụng **localization** của KLIPY để tìm GIF phù hợp văn hóa
- Kết hợp GIF với **text annotation** để cải thiện nhớ

---

## 🔧 Khắc phục sự cố

### GIF không tải được
1. **Kiểm tra API key** có đúng không
2. **Kiểm tra internet connection**
3. **Thử provider khác** (fallback tự động hoạt động)

### Quá chậm
1. Giảm `"max_concurrent_providers"` xuống 5
2. Tăng `"base_delay_ms"` thành 200
3. Tắt provider không cần thiết bằng cách xóa API key

### Giới hạn rate limit
- Addon có **Adaptive Delay Manager** tự động
- Nó sẽ tăng delay khi gặp 429 errors
- Reset tự động sau `"delay_reset_hours"`

---

## 📊 So sánh các Provider

| Feature | KLIPY | Pixabay | IconScout | GIPHY | Tenor |
|---------|-------|---------|-----------|-------|-------|
| **Miễn phí** | ✅ | ✅ | Giới hạn | ✅ (Beta) | ✅* |
| **Localization** | ✅✅✅ | ❌ | ❌ | ❌ | ❌ |
| **Biểu tượng động** | ❌ | ❌ | ✅✅✅ | ❌ | ❌ |
| **Số lượng GIF** | Lớn | Rất lớn | Khổng lồ | Khổng lồ | Khổng lồ |
| **Bản quyền** | Tốt | Tuyệt vời | Tốt | Trung bình | Trung bình |
| **Tính ổn định** | Cao | Cao | Cao | Cao | Thấp** |

*Tenor đóng cửa 30-06-2026
**API shape có thể thay đổi

---

## 📝 Cấu hình chi tiết cho từng use case

### 1. Giảng dạy từ vựng
```json
{
    "klipy_app_key": "YOUR_KLIPY_KEY",
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "enable_ai_provider_routing": true,
    "image_generation_mode": "search"
}
```

### 2. Giảng dạy khoa học
```json
{
    "pixabay_api_key": "YOUR_PIXABAY_KEY",
    "iconscout_api_token": "YOUR_ICONSCOUT_TOKEN",
    "giphy_api_key": "YOUR_GIPHY_KEY"
}
```

### 3. Giảng dạy ngoại ngữ
```json
{
    "klipy_app_key": "YOUR_KLIPY_KEY",
    "pixabay_api_key": "YOUR_PIXABAY_KEY"
}
```

---

## 🔗 Liên kết hữu ích

- **KLIPY**: https://www.klipy.io/developers
- **Pixabay**: https://pixabay.com/api/
- **IconScout**: https://iconscout.com/api
- **GIPHY**: https://developers.giphy.com
- **Tenor**: https://tenor.com/developer

---

## ✅ Checklist cài đặt

- [ ] Cài đặt addon AnkiAI ImageAddon v5.0+
- [ ] Lấy API keys từ ít nhất 2 provider
- [ ] Cập nhật `config.json` trong thư mục addon
- [ ] Khởi động lại Anki
- [ ] Test: Browse > Chọn thẻ > AnkiAI > Search for GIFs
- [ ] Thêm GIF vào thẻ
- [ ] Sync để lưu thay đổi

---

## 💬 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra logs tại `logs/agent-debug.ndjson`
2. Xem error message trong Anki console (Tools > Error Handler)
3. Thử tắt/bật lại addon
4. Kiểm tra Internet connection

---

**Happy learning with GIFs! 🎉**
