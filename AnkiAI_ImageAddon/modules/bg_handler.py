"""
Background Handler Module - Xử lý background để tránh UI freeze
Giai đoạn 4: Chạy xỚ lý ngầm với thanh tiến trình
"""

from aqt.operations import QueryOp
from aqt import mw
from typing import List, Callable, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import logging

# Configure logging
logger = logging.getLogger(__name__)

# 🔒 CRITICAL FIX v5.1: Global database lock to prevent race conditions
# Prevents simultaneous col.update_note() and col.save() from corrupting Anki DB
_GLOBAL_DB_LOCK = threading.RLock()  # RLock allows re-entry by same thread


class BackgroundProcessor:
    """
    Xử lý các thao tác dài hạn ở background
    Sử dụng aqt.operations.QueryOp của Anki để chạy ngầm mà không freeze UI
    """
    
    def __init__(self):
        """Khởi tạo BackgroundProcessor"""
        self.is_running = False
        self.cancelled = False
    
    def process_cards_in_background(
        self,
        note_ids: List[int],
        process_func: Callable,
        on_progress: Optional[Callable] = None,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        title: str = "Processing..."
    ) -> None:
        """
        Xử lý một danh sách note_ids ở background với thanh tiến trình
        
        Args:
            note_ids: Danh sách Note IDs cần xử lý
            process_func: Function để xử lý từng note. Signature: process_func(note_id, progress_callback)
            on_progress: Callback khi cập nhật tiến trình: on_progress(current, total, message)
            on_success: Callback khi xong: on_success(results)
            on_error: Callback khi lỗi: on_error(error_message)
            title: Tiêu đề cho thao tác
        """
        self.is_running = True
        self.cancelled = False
        results = []
        errors = []
        
        def background_work(col):
            """Công việc chính ở background - CONCURRENT processing"""
            try:
                total = len(note_ids)
                pending_remaining = set(note_ids)
                logger.info(f"🚀 Starting background work: Processing {total} notes (concurrent)")
                
                # 🟡 MEDIUM FIX v5.1: Pre-load all notes to avoid N+1 queries
                logger.info(f"📋 Pre-loading {total} notes from database...")
                notes_dict = {}
                for nid in note_ids:
                    try:
                        notes_dict[nid] = col.get_note(nid)
                    except Exception as e:
                        logger.warning(f"Failed to pre-load note {nid}: {e}")
                logger.info(f"✅ Pre-loaded {len(notes_dict)} notes successfully")
                
                db_lock = threading.Lock()
                completed = [0]  # Use list for mutability in closure
                
                def process_single_note(index, note_id):
                    """Process a single note - runs in thread pool"""
                    if self.cancelled:
                        return ("skipped", "Đã hủy")
                    
                    try:
                        # 🟡 MEDIUM FIX: Lookup from pre-loaded dict instead of DB query
                        note = notes_dict.get(note_id)
                        if not note:
                            return (False, f"Note {note_id} not found in pre-loaded cache")
                        
                        logger.debug(f"📌 [{index + 1}/{total}] Retrieved note {note_id} from cache: {note.keys()}")
                        
                        # Process note (AI + image search + download - all network I/O)
                        result = process_func(note)
                        success, message = result
                        
                        logger.info(f"📌 [{index + 1}/{total}] Process result: success={repr(success)}, msg={message}")
                        
                        # 🔧 CRITICAL FIX v5.2: Only update note if success is True (not "skipped" or False)
                        if success is True:
                            # Note was actually modified - save it
                            with db_lock:
                                col.update_note(note)
                            logger.info(f"✅ [{index + 1}/{total}] Note {note_id} updated successfully")
                        elif success == "skipped":
                            logger.info(f"⏭️  [{index + 1}/{total}] Note {note_id} skipped: {message}")
                        else:
                            logger.warning(f"❌ [{index + 1}/{total}] Failed to process note {note_id}: {message}")
                        
                        # Update progress
                        with db_lock:
                            completed[0] += 1
                            current = completed[0]
                        
                        with db_lock:
                            pending_remaining.discard(note_id)

                        if on_progress:
                            progress_msg = f"Đang xử lý thẻ {current}/{total}"
                            on_progress(current, total, progress_msg)
                        
                        return result
                    
                    except Exception as e:
                        error_msg = f"❌ Lỗi xử lý note {note_id}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        
                        with db_lock:
                            completed[0] += 1
                            current = completed[0]
                        if on_progress:
                            on_progress(current, total, f"Lỗi thẻ {current}/{total}")
                        
                        return (False, error_msg)
                
                # 🚀 Process cards concurrently (3 workers)
                max_workers = min(3, total)
                processed_notes_count = [0]  # Track truly processed notes
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for index, note_id in enumerate(note_ids):
                        future = executor.submit(process_single_note, index, note_id)
                        futures[future] = index
                    
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            results.append(result)
                            # Count successful operations (True means note was actually modified)
                            if isinstance(result, tuple) and len(result) >= 2:
                                success_status = result[0]
                                # Only count True as actual success (not "skipped" or False)
                                if success_status is True:
                                    processed_notes_count[0] += 1
                        except Exception as e:
                            error_msg = f"❌ Thread error: {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg, exc_info=True)
                
                # Save all changes at once
                if processed_notes_count[0] > 0:
                    logger.info(f"💾 Saving database... (processed {processed_notes_count[0]} notes with changes)")
                    try:
                        # 🔒 CRITICAL FIX v5.1: Use global lock for col.save()
                        with _GLOBAL_DB_LOCK:
                            col.save()
                        logger.info(f"✅ Database saved successfully! ({processed_notes_count[0]} notes modified)")
                    except Exception as e:
                        error_msg = f"❌ Database save failed: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        errors.append(error_msg)
                        raise
                else:
                    logger.info(f"⏭️  No notes were modified, skipping database save")

                out = {"results": results, "errors": errors}
                if self.cancelled and pending_remaining:
                    out["pending_note_ids"] = list(pending_remaining)
                    logger.info(
                        f"⏸️ Batch paused: {len(pending_remaining)} notes remaining"
                    )
                return out
            
            except Exception as e:
                error_msg = f"Lỗi background: {str(e)}"
                logger.error(error_msg)
                raise
        
        def on_done(result):
            """Callback khi xưng xong - Anki 25.x+ passes result directly"""
            try:
                self.is_running = False
                if on_success:
                    on_success(result)
            
            except Exception as e:
                self.is_running = False
                error_msg = f"Exception during background processing: {str(e)}"
                logger.error(error_msg)
                if on_error:
                    on_error(error_msg)
        
        # Chạy QueryOp (Anki 25.x+ API: keyword args)
        op = QueryOp(parent=mw, op=background_work, success=on_done)
        op.with_progress(title).run_in_background()
    
    def cancel(self):
        """Hủy xử lý hiện tại"""
        self.cancelled = True
    
    def is_processing(self) -> bool:
        """Kiểm tra xem có đang xử lý không"""
        return self.is_running


class ProgressDialog:
    """Dialog hiển thị tiến trình xử lý"""
    
    def __init__(self, title: str = "Đang xử lý...", parent=None):
        """Khởi tạo progress dialog"""
        from aqt.qt import QDialog, QVBoxLayout, QProgressBar, QLabel, QPushButton
        
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle(title)
        self.dialog.setMinimumWidth(400)
        self.dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Label hiển thị trạng thái
        self.status_label = QLabel("Khởi tạo...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        layout.addWidget(self.progress_bar)
        
        # Nút hủy
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self.on_cancel)
        layout.addWidget(self.cancel_button)
        
        self.dialog.setLayout(layout)
        self.cancelled = False
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Cập nhật tiến trình"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"{message}\n({current}/{total})")
    
    def on_cancel(self):
        """Người dùng nhấn hủy"""
        self.cancelled = True
        self.dialog.reject()
    
    def show(self):
        """Hiển thị dialog"""
        self.dialog.show()
    
    def close(self):
        """Đóng dialog"""
        self.dialog.close()
    
    def is_cancelled(self) -> bool:
        """Kiểm tra xem người dùng có nhấn hủy không"""
        return self.cancelled


class ProcessingTask:
    """Một công việc xử lý từng thẻ"""
    
    def __init__(self, name: str):
        """Khởi tạo ProcessingTask"""
        self.name = name
        self.results = []
        self.errors = []
    
    def process_note(self, note) -> Tuple[bool, str]:
        """
        Xử lý một note
        Override method này trong lớp con
        
        Args:
            note: Anki Note object
        
        Returns:
            Tuple (success, message)
        """
        raise NotImplementedError("Override process_note in subclass")
    
    def add_result(self, note_id: int, success: bool, message: str):
        """Lưu kết quả xử lý"""
        if success:
            self.results.append({"note_id": note_id, "message": message})
        else:
            self.errors.append({"note_id": note_id, "error": message})
    
    def get_summary(self) -> dict:
        """Lấy tóm tắt kết quả"""
        return {
            "task_name": self.name,
            "total_processed": len(self.results) + len(self.errors),
            "successful": len(self.results),
            "failed": len(self.errors),
            "results": self.results,
            "errors": self.errors
        }
