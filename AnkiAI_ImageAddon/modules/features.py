"""
Advanced Features Module v4.5
- Custom AI evaluation prompts
- Database statistics dashboard  
- Scheduled auto-add on sync
- Image history with undo
- Provider performance reporting
- Proper logging
"""

import json
import logging
import threading

# Configure logging
logger = logging.getLogger(__name__)
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class FeatureDatabase:
    """SQLite database for addon features"""
    
    def __init__(self, anki_collection_path: str):
        """
        Initialize feature database
        
        Args:
            anki_collection_path: Path to Anki collection folder
        """
        self.db_path = Path(anki_collection_path) / "AnkiAI_features.db"
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self.init_database()

    def close(self):
        """Close the persistent feature database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
    
    def init_database(self):
        """Initialize database schema if not exists"""
        with self._lock:
            cursor = self._conn.cursor()
            
            # Image history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_history (
                    id INTEGER PRIMARY KEY,
                    note_id INTEGER,
                    image_url TEXT,
                    provider TEXT,
                    added_timestamp DATETIME,
                    field_name TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Provider stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS provider_stats (
                    id INTEGER PRIMARY KEY,
                    provider_name TEXT UNIQUE,
                    total_searches INTEGER DEFAULT 0,
                    successful_searches INTEGER DEFAULT 0,
                    total_images_added INTEGER DEFAULT 0,
                    avg_response_time_ms REAL DEFAULT 0,
                    last_updated DATETIME,
                    reliability_score REAL DEFAULT 1.0
                )
            """)
            
            # Session statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_stats (
                    id INTEGER PRIMARY KEY,
                    session_date DATE,
                    total_notes_processed INTEGER DEFAULT 0,
                    successful_additions INTEGER DEFAULT 0,
                    failed_additions INTEGER DEFAULT 0,
                    total_time_ms INTEGER DEFAULT 0,
                    avg_per_note_ms INTEGER DEFAULT 0
                )
            """)
            
            # Custom prompts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_prompts (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    prompt_text TEXT,
                    created_timestamp DATETIME,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Scheduled tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY,
                    task_type TEXT,
                    schedule TEXT,
                    is_enabled BOOLEAN DEFAULT 1,
                    last_executed DATETIME,
                    deck_names TEXT
                )
            """)
            
            self._conn.commit()
    
    def add_image_to_history(self, note_id: int, image_url: str, provider: str, field_name: str) -> bool:
        """Record image addition in history"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    INSERT INTO image_history (note_id, image_url, provider, added_timestamp, field_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (note_id, image_url, provider, datetime.now(), field_name))
                self._conn.commit()
                return True
        except Exception as e:
            logger.warning(f"Failed to add to history: {e}")
            return False
    
    def remove_image_from_history(self, note_id: int, image_url: str) -> bool:
        """Mark image as removed (soft delete for undo)"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    UPDATE image_history 
                    SET status = 'removed' 
                    WHERE note_id = ? AND image_url = ?
                """, (note_id, image_url))
                self._conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to remove from history: {e}")
            return False
    
    def get_image_history(self, note_id: int, limit: int = 10) -> List[Dict]:
        """Get image history for a note"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    SELECT * FROM image_history 
                    WHERE note_id = ? AND status = 'active'
                    ORDER BY added_timestamp DESC
                    LIMIT ?
                """, (note_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Failed to get history: {e}")
            return []
    
    def update_provider_stats(self, provider: str, response_time_ms: int, success: bool):
        """Update provider performance statistics"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                
                # Check if exists
                cursor.execute("SELECT id FROM provider_stats WHERE provider_name = ?", (provider,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing
                    cursor.execute("""
                        UPDATE provider_stats
                        SET total_searches = total_searches + 1,
                            successful_searches = successful_searches + ?,
                            last_updated = ?
                        WHERE provider_name = ?
                    """, (1 if success else 0, datetime.now(), provider))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO provider_stats 
                        (provider_name, total_searches, successful_searches, last_updated)
                        VALUES (?, 1, ?, ?)
                    """, (provider, 1 if success else 0, datetime.now()))
                
                self._conn.commit()
                return True
        except Exception as e:
            logger.warning(f"Failed to update provider stats: {e}")
            return False
    
    def get_provider_report(self) -> Dict[str, Dict]:
        """Get performance report for all providers"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("SELECT * FROM provider_stats ORDER BY reliability_score DESC")
                
                report = {}
                for row in cursor.fetchall():
                    provider = dict(row)
                    # Calculate reliability
                    if provider['total_searches'] > 0:
                        provider['reliability'] = (provider['successful_searches'] / provider['total_searches']) * 100
                    report[provider['provider_name']] = provider
                
                return report
        except Exception as e:
            logger.warning(f"Failed to get provider report: {e}")
            return {}
    
    def get_session_stats(self) -> Dict:
        """Get today's session statistics"""
        try:
            from datetime import date
            
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    SELECT * FROM session_stats 
                    WHERE session_date = ?
                """, (date.today(),))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return {
                    'session_date': str(date.today()),
                    'total_notes_processed': 0,
                    'successful_additions': 0,
                    'failed_additions': 0
                }
        except Exception as e:
            logger.warning(f"Failed to get session stats: {e}")
            return {}
    
    def update_session_stats(self, successful: int, failed: int, time_ms: int):
        """Update session statistics"""
        try:
            from datetime import date
            
            with self._lock:
                cursor = self._conn.cursor()
                today = date.today()
                
                # Check if session exists
                cursor.execute("SELECT id FROM session_stats WHERE session_date = ?", (today,))
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute("""
                        UPDATE session_stats
                        SET total_notes_processed = total_notes_processed + ?,
                            successful_additions = successful_additions + ?,
                            failed_additions = failed_additions + ?,
                            total_time_ms = total_time_ms + ?
                        WHERE session_date = ?
                    """, (successful + failed, successful, failed, time_ms, today))
                else:
                    cursor.execute("""
                        INSERT INTO session_stats 
                        (session_date, total_notes_processed, successful_additions, failed_additions, total_time_ms)
                        VALUES (?, ?, ?, ?, ?)
                    """, (today, successful + failed, successful, failed, time_ms))
                
                self._conn.commit()
                return True
        except Exception as e:
            logger.warning(f"Failed to update session stats: {e}")
            return False
    
    def save_custom_prompt(self, name: str, prompt_text: str) -> bool:
        """Save a custom evaluation prompt"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO custom_prompts 
                    (name, prompt_text, created_timestamp, is_active)
                    VALUES (?, ?, ?, 1)
                """, (name, prompt_text, datetime.now()))
                self._conn.commit()
                return True
        except Exception as e:
            logger.warning(f"Failed to save prompt: {e}")
            return False
    
    def get_custom_prompts(self) -> List[Dict]:
        """Get all active custom prompts"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    SELECT * FROM custom_prompts 
                    WHERE is_active = 1
                    ORDER BY created_timestamp DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Failed to get prompts: {e}")
            return []
    
    def enable_scheduled_task(self, task_type: str, schedule: str, deck_names: List[str]) -> bool:
        """Enable a scheduled task (sync-based auto-add)"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                deck_str = ",".join(deck_names)
                cursor.execute("""
                    INSERT OR REPLACE INTO scheduled_tasks 
                    (task_type, schedule, is_enabled, deck_names)
                    VALUES (?, ?, 1, ?)
                """, (task_type, schedule, deck_str))
                self._conn.commit()
                return True
        except Exception as e:
            logger.warning(f"Failed to enable task: {e}")
            return False
    
    def get_scheduled_tasks(self) -> List[Dict]:
        """Get all enabled scheduled tasks"""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("SELECT * FROM scheduled_tasks WHERE is_enabled = 1")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Failed to get tasks: {e}")
            return []


class AdvancedFeatures:
    """Manager for all advanced features"""
    
    def __init__(self, db: FeatureDatabase):
        """Initialize advanced features"""
        self.db = db
        self.current_prompt = None
    
    def set_evaluation_prompt(self, prompt_name: str):
        """Set custom evaluation prompt"""
        prompts = self.db.get_custom_prompts()
        for prompt in prompts:
            if prompt['name'] == prompt_name:
                self.current_prompt = prompt['prompt_text']
                return True
        return False
    
    def get_statistics_summary(self) -> Dict:
        """Get comprehensive statistics summary"""
        return {
            'session': self.db.get_session_stats(),
            'providers': self.db.get_provider_report(),
            'timestamp': datetime.now().isoformat()
        }
