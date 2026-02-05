"""
Memory Manager - SQLite-based long-term memory for storing queries and preferences
"""
import sqlite3
import json
import threading
from datetime import datetime
from typing import Any, Optional, Dict, List
from pathlib import Path


class MemoryManager:
    """Thread-safe SQLite-based memory storage for query history and user preferences"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
            
        # Default database path in the same directory as this file
        if db_path is None:
            db_path = Path(__file__).parent / "memory.db"
        
        self.db_path = str(db_path)
        self._local = threading.local()
        self._init_database()
        self._initialized = True
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_database(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Query history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task TEXT NOT NULL,
                tools_used TEXT,
                final_answer TEXT,
                execution_time REAL,
                success INTEGER DEFAULT 1
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
    
    # ========================
    # Query History Methods
    # ========================
    
    def save_interaction(
        self,
        task: str,
        tools_used: List[str],
        final_answer: str,
        execution_time: float = 0.0,
        success: bool = True
    ) -> int:
        """
        Save a completed task interaction to history
        
        Args:
            task: The original task text
            tools_used: List of tool names used
            final_answer: The final response
            execution_time: Time taken in seconds
            success: Whether the task succeeded
            
        Returns:
            The ID of the inserted record
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO query_history (timestamp, task, tools_used, final_answer, execution_time, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            task,
            json.dumps(tools_used),
            final_answer,
            execution_time,
            1 if success else 0
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent queries
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of query records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, task, tools_used, final_answer, execution_time, success
            FROM query_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]
    
    def search_queries(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search query history by keyword
        
        Args:
            keyword: Search term
            limit: Maximum results
            
        Returns:
            List of matching query records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, task, tools_used, final_answer, execution_time, success
            FROM query_history
            WHERE task LIKE ? OR final_answer LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"%{keyword}%", f"%{keyword}%", limit))
        
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]
    
    def get_context_for_task(self, task: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find relevant past interactions for context
        
        Uses simple keyword matching to find similar past queries.
        
        Args:
            task: Current task text
            limit: Maximum context items
            
        Returns:
            List of relevant past interactions
        """
        # Extract keywords (simple approach: split and filter)
        keywords = [word.lower() for word in task.split() if len(word) > 3]
        
        if not keywords:
            return []
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build query with OR conditions for each keyword
        conditions = " OR ".join(["task LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]
        params.append(limit)
        
        cursor.execute(f"""
            SELECT id, timestamp, task, tools_used, final_answer, execution_time, success
            FROM query_history
            WHERE {conditions}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)
        
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]
    
    def clear_history(self) -> int:
        """
        Clear all query history
        
        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM query_history")
        count = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM query_history")
        conn.commit()
        
        return count
    
    def get_history_stats(self) -> Dict[str, Any]:
        """Get statistics about query history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM query_history")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM query_history WHERE success = 1")
        successful = cursor.fetchone()[0]
        
        return {
            "total_queries": total,
            "successful_queries": successful,
            "failed_queries": total - successful
        }
    
    # ========================
    # Preferences Methods
    # ========================
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference
        
        Args:
            key: Preference key
            value: Preference value (will be JSON serialized)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO preferences (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat()))
        
        conn.commit()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference
        
        Args:
            key: Preference key
            default: Default value if not found
            
        Returns:
            The preference value or default
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row is None:
            return default
        
        return json.loads(row[0])
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM preferences")
        rows = cursor.fetchall()
        
        return {row[0]: json.loads(row[1]) for row in rows}
    
    def delete_preference(self, key: str) -> bool:
        """
        Delete a preference
        
        Args:
            key: Preference key to delete
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM preferences WHERE key = ?", (key,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    def clear_preferences(self) -> int:
        """
        Clear all preferences
        
        Returns:
            Number of preferences deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM preferences")
        count = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM preferences")
        conn.commit()
        
        return count
    
    # ========================
    # Helper Methods
    # ========================
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary"""
        result = dict(row)
        if 'tools_used' in result and result['tools_used']:
            result['tools_used'] = json.loads(result['tools_used'])
        if 'success' in result:
            result['success'] = bool(result['success'])
        return result


# Module-level memory instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get or create the memory manager singleton"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
