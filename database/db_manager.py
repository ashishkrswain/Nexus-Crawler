import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="data/nexus.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()
        
    def get_connection(self):
        """Returns a new database connection."""
        return sqlite3.connect(self.db_path)
        
    def init_db(self):
        """Initializes the schema and enables high-concurrency mode."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Enable WAL (Write-Ahead Logging) for better concurrent writes
        cursor.execute('PRAGMA journal_mode=WAL;')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE,
                content TEXT,
                discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
    def insert_company(self, domain, content, status="SUCCESS"):
        """Inserts a successfully scraped domain into the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO scraped_companies (domain, content, status)
                VALUES (?, ?, ?)
            ''', (domain, content, status))
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Failed to insert {domain}: {e}")
        finally:
            conn.close()
