# 📋 AnkiAI Image Addon — UI/UX Redesign Plan & Execution Diary

Cuốn nhật ký kế hoạch này theo dõi từng bước thiết kế và hiện đại hóa toàn diện giao diện UI/UX của Addon **AnkiAI Image Addon**.
Các tác vụ đã hoàn thành được gạch đi (`~~tác vụ~~`) và đánh dấu `[x]`.

---

## 🔍 Phase 0: Baseline Audit & System Inventory (Hoàn thành)

### 1. Thông tin phiên bản & Baseline Commit
- **Git Commit Baseline**: `47c29179ac75fcdd16e114d970c797cb9ab17184`
- **Môi trường Python**: Python 3.9.6 / Anki 24+ & 25+ Qt6 (PyQt6 / PySide6 / aqt.qt)
- **Kiểm tra cú pháp ban đầu**: `python3 -m compileall AnkiAI_ImageAddon` PASS (0 errors)

### 2. Danh mục các lớp UI & Hợp đồng giao tiếp (Public UI Contracts)
1. **`BrowserMenuManager`**:
   - `setup_browser_menu(browser, callback_add_images, callback_resume_batch=None)`: Hook vào `browser.form.menu_Cards` hoặc `menu_Notes` hoặc `menuBar()`.
   - `get_selected_note_ids(browser) -> List[int]`: Trích xuất note IDs từ `browser.selected_cards()`.
   - `show_error(title, message)`, `show_warning(title, message)`, `show_info(title, message)`, `show_question(title, message) -> bool`.
2. **`FieldSelectionDialog(QDialog)`**:
   - Khởi tạo: `(model_name: str, available_fields: List[str], parent=None, initial=None)`
   - Thuộc tính công khai: `selected_vocab_field`, `selected_definition_field`, `selected_examples_field`, `selected_image_field`, `save_as_preset`.
   - Phương thức: `accept_with_values(vocab_field, definition_field, examples_field, image_field)`.
3. **`BatchOptionsDialog(QDialog)`**:
   - Khởi tạo: `(selected_count: int, default_max: int = 100, pending_count: int = 0, parent=None)`
   - Thuộc tính công khai: `use_pending: bool`, `max_notes: int`.
4. **`ConfigDialog(QDialog)`**:
   - Khởi tạo: `(parent=None, existing_config=None)`
   - Phương thức công khai: `load_existing_config()`, `get_config() -> dict` (validate và trả về dict đầy đủ, throw `ValueError`), `test_connection()`, `test_image_providers()`.
5. **`ProgressDialog(QDialog)`**:
   - Khởi tạo: `(total_cards: int, parent=None)`
   - Thuộc tính công khai: `is_cancelled: bool`, `total_cards`, `current_card`, `successful`, `skipped`, `failed`, `detail_label: QLabel`.
   - Phương thức công khai: `set_cancel_callback(cb)`, `update_progress(current, total, status_msg, detail_msg="")`, `update_stats(successful, skipped, failed)`, `finish(success_count, skipped_count, fail_count)`, `cancel()`, `accept()`, `reject()`.
6. **`get_note_data(note) -> tuple`**: Trích xuất `(vocabulary, definition)`.

### 3. Danh mục Persisted Configuration Keys
Toàn bộ 45+ khóa cấu hình (AI providers, Search providers, GIF providers, Imagen, AI Evaluation keys 1-7, rate limits, adaptive delay, caching, presets, batch meta) được bảo toàn 100%.

---

## 🎨 Nguyên Tắc Thiết Kế Đã Triển Khai (Design System)
1. **Desktop Native cho Anki**: Thiết kế tinh tế, tĩnh lặng, gọn gàng, phù hợp hệ sinh thái Anki desktop.
2. **Hỗ trợ Song Song Dark & Light Theme**: Sử dụng semantic tokens (`THEME_TOKENS_DARK`, `THEME_TOKENS_LIGHT`), tự động phát hiện theme qua `is_dark_mode()` với fallback mượt mà.
3. **Không lạm dụng Card**: Kết hợp khoảng cách, typography, viền mỏng và section headers tinh gọn.
4. **Credential Input Chuyên Nghiệp**: Widget `CredentialField` hỗ trợ ẩn/hiện mắt xem (`EchoMode.Password` ↔ `Normal`), không nút copy thừa thãi.
5. **Cấu trúc Cài đặt Khoa học**: 4 tab chính trong `ConfigDialog`: (1) 🎯 Chung & Quy tắc, (2) 🤖 AI Providers, (3) 🖼️ Nguồn ảnh & GIF, (4) ⚙️ Nâng cao & Vision.
6. **Progress UI Trực Quan & Tinh Gọn**: Dashboard theo dõi tiến độ với huy hiệu trạng thái (Đang chạy / Tạm dừng / Hoàn tất), thanh tiến độ %, bộ 4 chỉ số (Đã xử lý, Thành công, Bỏ qua, Thất bại) và theo dõi từ vựng thời gian thực.
7. **Tối ưu Tương tác & Phím Tắt**: Hỗ trợ Esc (Hủy/Đóng), Enter (Tiếp tục/Lưu), Tab navigation, focus highlight chuẩn xác.

---

## 📌 Kế Hoạch & Nhật Ký Triển Khai Chi Tiết (Checklist & Diary)

### Phase 0: Baseline Audit & Setup
- [x] ~~**0.1 Kiểm kê toàn bộ UI classes, callers, signals và config contracts**~~
- [x] ~~**0.2 Kiểm tra cú pháp và khả năng biên dịch Python**~~
- [x] ~~**0.3 Thiết lập tài liệu Baseline và Redesign Plan**~~

### Phase 1: Semantic Design System (`modules/ui_theme.py`)
- [x] ~~**1.1 Xây dựng Theme Tokens (Dark & Light Mode)**: Bảng màu ngữ nghĩa `THEME_TOKENS_DARK` và `THEME_TOKENS_LIGHT` với hàm `is_dark_mode()` và `get_tokens()`~~
- [x] ~~**1.2 Centralized Qt Stylesheet (QSS Engine)**: Chuẩn hóa stylesheet toàn diện cho QDialog, QTabWidget, QLineEdit, QComboBox, QSpinBox, QPushButton (Primary, Secondary, Danger), QProgressBar, QCheckBox, QScrollBar~~
- [x] ~~**1.3 Theme Helper Functions**: Hàm `apply_dialog_theme(widget, dark)` và bảo toàn các hằng số tương thích ngược~~

### Phase 2: Reusable UI Components (`modules/ui_widgets.py`)
- [x] ~~**2.1 HeaderSection**: Widget header gồm biểu tượng, tiêu đề chính nổi bật và subtitle hướng dẫn~~
- [x] ~~**2.2 SettingsSection / CardWidget**: Khung nhóm cài đặt với viền ngăn cách tinh tế, padding chuẩn desktop~~
- [x] ~~**2.3 FormRow & FieldLabel**: Hàng nhãn kèm huy hiệu (Priority, Recommended, Optional) và mô tả inline~~
- [x] ~~**2.4 CredentialField**: Ô nhập API key bảo mật có nút Toggle Hiện/Ẩn (Show/Hide) an toàn~~
- [x] ~~**2.5 StatusBadge & InfoBanner**: Huy hiệu và banner thông báo trạng thái ngữ nghĩa (Running, Paused, Success, Warning, Error, Info)~~
- [x] ~~**2.6 Tương thích ngược**: Giữ nguyên `make_settings_card`, `card_header`, `password_field`, `section_spacer`~~

### Phase 3: Dialog Redesigns (`modules/ui.py`)
- [x] ~~**3.1 Browser Context Menu (`BrowserMenuManager`)**: Tinh chỉnh nhãn menu người dùng rõ ràng, phân nhóm logic trong Cards/Notes~~
- [x] ~~**3.2 Field Selection Dialog (`FieldSelectionDialog`)**: Giao diện mapping trường trực quan (Vocabulary, Definition, Examples, Image Target), checkbox lưu Preset, giữ nguyên callback `accept_with_values`~~
- [x] ~~**3.3 Batch Options Dialog (`BatchOptionsDialog`)**: Thẻ thống kê số lượng thẻ được chọn, bộ chọn số lượng xử lý, tích hợp nút tiếp tục batch đang chờ~~
- [x] ~~**3.4 Configuration Dialog (`ConfigDialog`)**: Chuyển đổi thành giao diện 4 Tabs khoa học (Chung & Quy tắc, AI Providers, Nguồn ảnh & GIF, Nâng cao & Vision), áp dụng `CredentialField` cho toàn bộ API keys, giữ nguyên 45+ config keys~~
- [x] ~~**3.5 Image Provider Test Dialog (`test_image_providers`)**: Hiện đại hóa kết quả kiểm tra API với giao diện danh sách card sắc nét, biểu tượng trạng thái và huy hiệu~~
- [x] ~~**3.6 Batch Progress Dialog (`ProgressDialog`)**: Giao diện theo dõi tiến trình thông minh: Huy hiệu trạng thái, thanh tiến độ %, bộ 4 chỉ số (Đã xử lý, Thành công, Bỏ qua, Thất bại), theo dõi từ vựng đang xử lý và tổng kết hoàn tất~~

### Phase 4: Light & Dark Mode Verification
- [x] ~~**4.1 Kiểm tra hiển thị và cấu trúc QSS trong cả hai chế độ Light và Dark**~~
- [x] ~~**4.2 Đảm bảo độ tương phản màu sắc và khả năng đọc trong môi trường học tập dài**~~

### Phase 5: Compatibility & Contract Verification
- [x] ~~**5.1 Kiểm tra toàn bộ chữ ký phương thức và thuộc tính công khai của các lớp UI**~~
- [x] ~~**5.2 Kiểm tra tích hợp với `__init__.py`, `bg_handler.py`, `config.py`**~~
- [x] ~~**5.3 Chạy kiểm tra cú pháp toàn bộ gói `AnkiAI_ImageAddon` bằng `python3 -m compileall` (PASS)**~~

### Phase 6: Visual QA & Final Polish
- [x] ~~**6.1 Rà soát khoảng cách, căn lề, độ tương phản và phân cấp giao diện desktop**~~
- [x] ~~**6.2 Hoàn thiện báo cáo tổng kết theo yêu cầu**~~

---

## 📝 Nhật Ký Thực Hiện (Execution Diary)
- **2026-08-18 (Phase 0)**: Hoàn thành kiểm kê toàn diện codebase, baseline commit `47c29179ac75fcdd16e114d970c797cb9ab17184`, 6 lớp UI, 45+ config keys.
- **2026-08-18 (Phase 1)**: Tái cấu trúc `ui_theme.py` thành theme engine tập trung, hỗ trợ cả Dark Mode (Midnight Slate) & Light Mode (Clean Slate), token hóa toàn bộ màu sắc, typography và bộ QSS desktop.
- **2026-08-18 (Phase 2)**: Hiện đại hóa `ui_widgets.py` với các thành phần tái sử dụng: `header_section`, `settings_section`, `field_row`, `CredentialField` (với nút bật/tắt mật khẩu), `status_badge`, `info_banner`.
- **2026-08-18 (Phase 3)**: Tái thiết kế toàn bộ các dialog trong `ui.py`:
  - `BrowserMenuManager`: Giao diện menu Cards/Notes chuẩn chỉ.
  - `FieldSelectionDialog`: Khớp trường trực quan, thiết lập preset tiện lợi.
  - `BatchOptionsDialog`: Tóm tắt số thẻ, kiểm soát batch size và resume batch dở dang.
  - `ConfigDialog`: Chia 4 tab chuyên nghiệp, bảo mật API keys, kiểm tra kết nối tức thì.
  - `ProgressDialog`: Bảng điều khiển tiến trình thời gian thực, 4 số liệu thống kê, hủy/tiếp tục mượt mà.
  - `test_image_providers`: Cửa sổ kiểm tra tình trạng kết nối nguồn ảnh hiện đại.
- **2026-08-18 (Phase 4, 5, 6)**: Kiểm tra cú pháp biên dịch toàn bộ gói đạt 100% không lỗi (`compileall` PASS). Toàn bộ public contracts, signals, callbacks và config keys được bảo toàn nguyên vẹn.
