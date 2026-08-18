# 🧪 Hướng Dẫn Test & Troubleshooting v5.2

## 📋 Checklist Trước Khi Test

- [ ] Backup config.json của addon
- [ ] Xóa folder logs/
- [ ] Restart Anki hoàn toàn (không chỉ reload addon)
- [ ] Chọn đúng 5 thẻ chưa có ảnh

## 🎯 Test Case

### Test 1: Thêm Ảnh Bình Thường
1. Chọn 5 thẻ trong Browser (chắc chắn không có ảnh)
2. Chuột phải → "AnkiAI: Tự động thêm ảnh bằng AI"
3. Chọn fields đúng
4. Nhấn "Động"
5. **Kỳ Vọng**:
   - Progress bar tăng từ 0 → 100% dần dần (mỗi 500ms cập nhật một lần)
   - Sau khi xong, hiển thị: "✅ Thành công: X"
   - Refresh browser, kiểm tra ảnh đã được thêm vào các thẻ

### Test 2: Mix Thẻ (Có Ảnh + Không Có)
1. Chọn 5 thẻ: 3 cái chưa có ảnh, 2 cái đã có ảnh
2. Cài đặt skip_existing_images = True
3. Thêm ảnh
4. **Kỳ Vọng**:
   - Hiển thị: "✅ Thành công: 3, ℹ Bỏ qua: 2"
   - Chỉ 3 thẻ được update

### Test 3: Field Không Tồn Tại
1. Chọn 1 thẻ
2. Thay đổi image_field thành "NonExistentField"
3. Thêm ảnh
4. **Kỳ Vọng**:
   - Hiển thị: "✅ Thành công: 0, ❌ Thất bại: 1"
   - Lỗi: "Field 'NonExistentField' không tồn tại"

## 📊 Xem Log

Log file sẽ được ghi tại:
```
AnkiAI_ImageAddon/logs/ankiai.log
```

Kiểm tra các log messages quan trọng:
```
✅ Note modified, will be saved by background processor
✅ Note {note_id} updated successfully
⏭️ Note {note_id} skipped: {message}
❌ Failed to process note {note_id}: {message}
💾 Saving database... (processed X notes)
✅ Database saved successfully!
```

## 🔍 Debug Chi Tiết

### Nếu Progress Vẫn Showing 100% Ngay Lập Tức
1. Kiểm tra log để xem có exception không:
   ```bash
   tail -50 AnkiAI_ImageAddon/logs/ankiai.log | grep -i error
   ```
2. Nếu có "API Error" → kiểm tra API keys
3. Nếu có "Image Error" → kiểm tra image providers
4. Nếu có "Field error" → kiểm tra field selection

### Nếu Tất Cả Thẻ Thất Bại
1. Kiểm tra error message trong progress dialog
2. Kiểm tra log file
3. Likely causes:
   - AI API key không có hoặc sai
   - Image field name sai
   - Network issue (timeout)
   - Image provider lỗi

### Nếu Ảnh Không Được Lưu Nhưng Không Có Lỗi
1. Kiểm tra col.save() có được gọi không:
   ```bash
   grep "Saving database" AnkiAI_ImageAddon/logs/ankiai.log
   ```
2. Kiểm tra file ảnh có được lưu vào media folder:
   ```bash
   ls -la ~/Anki2/{YourProfile}/collection.media/ | tail -10
   ```

## 📞 Troubleshooting Commands

### 1. Xem tất cả errors
```bash
grep -i "error\|fail" AnkiAI_ImageAddon/logs/ankiai.log
```

### 2. Xem flow xử lý một note
```bash
grep "note_1234567890" AnkiAI_ImageAddon/logs/ankiai.log
```

### 3. Xem database operations
```bash
grep "Saving database\|Database saved\|update_note\|col.save" AnkiAI_ImageAddon/logs/ankiai.log
```

### 4. Xem progress updates
```bash
grep "PROGRESS\|progress_bar\|setFormat" AnkiAI_ImageAddon/logs/ankiai.log
```

## 🚀 Performance Expectations

### Thời Gian Dự Kiến (5 thẻ)
- Khởi tạo: ~1 giây
- AI processing (keyword generation): ~10-15 giây
- Image download: ~5-10 giây (tùy network)
- Database save: ~1 giây
- **Tổng**: ~20-30 giây cho 5 thẻ

### Resource Usage
- CPU: Peaks during AI processing, moderate during downloads
- Memory: Should not exceed 100MB
- Network: ~20-50 MB total (5 images x 4-10MB each)

## ✅ Validation Checklist

Sau khi test, kiểm tra:
- [ ] Progress bar tăng dần (không jump to 100%)
- [ ] Final result hiển thị số lượng chính xác
- [ ] Browser tự động refresh
- [ ] Ảnh hiển thị trong Anki
- [ ] Log file không có critical errors
- [ ] Database được save (check timestamp)

## 🎓 Key Improvements v5.2

1. **Proper result parsing**: Distinguish True/False/"skipped"
2. **Correct database updates**: Only update notes that were modified
3. **Better error messages**: Know exactly why each note failed
4. **Improved logging**: Every step is logged for debugging
5. **Atomic operations**: All notes processed or none (failure handling)
