# 🎬 Quick Reference - GIF Animated Providers

## 5 GIF Provider - So sánh nhanh

| Provider | Lấy Key | Miễn phí | Tốt nhất cho |
|----------|---------|---------|-------------|
| **KLIPY** | https://www.klipy.io/developers | ✅ | Ngoại ngữ + Localization |
| **Pixabay** | https://pixabay.com/api/ | ✅ | Ảnh động không lo bản quyền |
| **GIPHY** | https://developers.giphy.com | ✅ (Beta) | Phản ứng GIF đa dạng |
| **Tenor** | https://tenor.com/developer | ✅* | Gợi ý từ khóa thông minh |
| **IconScout** | https://iconscout.com/api | ⚠️ | Biểu tượng động tối giản |

*Tenor đóng 30-06-2026

---

## 🚀 Setup nhanh (5 phút)

### 1. Tạo 1-2 API keys
Chọn ít nhất 2 provider từ bảng trên.

### 2. Cập nhật config
```json
{
    "klipy_app_key": "YOUR_KEY",
    "giphy_api_key": "YOUR_KEY"
}
```

### 3. Test
Browse → Chọn thẻ → AnkiAI → Search for GIFs → Nhập: "running"

### 4. Chọn GIF → Thêm vào thẻ

---

## 📝 API Keys nhanh

### KLIPY
```
URL: https://www.klipy.io/developers
Path: Developer → Create App Key
Config: "klipy_app_key"
```

### Pixabay
```
URL: https://pixabay.com/api/
Path: API Docs → API Key
Config: "pixabay_api_key"
```

### GIPHY
```
URL: https://developers.giphy.com
Path: Create App → Get API Key
Config: "giphy_api_key"
```

### Tenor
```
URL: https://tenor.com/developer
Path: Create App → Copy API Key
Config: "tenor_api_key"
Warning: Đóng 30-06-2026
```

### IconScout
```
URL: https://iconscout.com/api
Path: API Settings → Create Token
Config: "iconscout_api_token"
```

---

## 💡 Use Cases

### Học từ vựng động từ
```
Keyword: "running", "jumping", "dancing"
Provider: KLIPY (localization tốt)
```

### Học từ vựng giới từ
```
Keyword: "above", "below", "beside", "between"
Provider: IconScout (biểu tượng động)
```

### Học khoa học
```
Keyword: "photosynthesis", "mitosis", "electron"
Provider: Pixabay (chất lượng cao) hoặc IconScout
```

### Học ngoại ngữ (phát âm + hình ảnh)
```
Keyword: "happy", "hello", "goodbye"
Provider: KLIPY (localization + thích hợp văn hóa)
```

### Phản ứng hài hước
```
Keyword: "funny", "laugh", "surprised"
Provider: GIPHY (phản ứng GIF đa dạng)
```

---

## ⚡ Performance Tips

1. **Dùng KLIPY hoặc Pixabay** - Nhanh nhất
2. **Giới hạn 3-5 GIF** mỗi lần tìm kiếm
3. **Chạy 100 thẻ một lần** - Không chạy 1000 thẻ cùng lúc
4. **Để addon delay tự động** - Adaptive Delay xử lý rate limiting

---

## 🔧 Config mẫu cho từng use case

### Giáo dục từ vựng
```json
{
    "klipy_app_key": "YOUR_KEY",
    "pixabay_api_key": "YOUR_KEY",
    "enable_ai_provider_routing": true
}
```

### Giáo dục khoa học
```json
{
    "pixabay_api_key": "YOUR_KEY",
    "iconscout_api_token": "YOUR_TOKEN",
    "giphy_api_key": "YOUR_KEY"
}
```

### Tối ưu tốc độ
```json
{
    "klipy_app_key": "YOUR_KEY",
    "max_concurrent_providers": 3,
    "base_delay_ms": 50,
    "enable_adaptive_delay": true
}
```

---

## ❓ Troubleshooting nhanh

| Vấn đề | Giải pháp |
|-------|----------|
| GIF không tải | Kiểm tra API key đúng? Try provider khác |
| Quá chậm | Giảm `max_concurrent_providers` xuống 3 |
| Rate limit | Addon tự động delay. Chờ một chút |
| Tenor lỗi | Tenor đóng 30-06-2026. Dùng KLIPY/GIPHY |
| Không có GIF | Thử keyword khác hoặc provider khác |

---

## 📚 Tài liệu chi tiết

- **Hướng dẫn đầy đủ**: `GIF_ANIMATED_PROVIDERS_GUIDE.md`
- **Tích hợp kỹ thuật**: `GIF_INTEGRATION_SUMMARY.md`
- **Main README**: `README.md`

---

## 🎯 Mẹo

### Keyword tốt cho từng loại
```
Động từ: running, jumping, walking, sitting
Cảm xúc: happy, sad, angry, confused
Vật chất: water, fire, ice, smoke
Động vật: dog, cat, bird, fish
Quá trình: growth, decay, transformation
```

### Localization (KLIPY)
```
Tiếng Việt: Tìm GIF phù hợp văn hóa Việt
English: Reaction GIFs phù hợp châu Âu/Bắc Mỹ
Spanish: Emojis/GIFs cho học sinh Tây Ban Nha
```

---

**Bắt đầu trong 5 phút. Học hiệu quả hơn ngay!** 🎉
