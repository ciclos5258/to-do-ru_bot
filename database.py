import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path="todo_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    text TEXT NOT NULL,
                    is_done BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    name TEXT NOT NULL,
                    time TEXT NOT NULL,
                    reminder_datetime TIMESTAMP,
                    is_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            ''')
            conn.commit()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule (
                    user_id INTEGER,
                    day TEXT,
                    time TEXT,
                    text TEXT
                )
            """)
            conn.commit()
    def add_user(self, chat_id, username, first_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (chat_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (chat_id, username, first_name))
            conn.commit()
    
    def add_task(self, chat_id, text):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO tasks (chat_id, text) VALUES (?, ?)', (chat_id, text))
            conn.commit()
            return True
    
    def get_tasks(self, chat_id, show_done=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if show_done:
                cursor.execute('SELECT id, text, is_done FROM tasks WHERE chat_id = ? ORDER BY created_at DESC', (chat_id,))
            else:
                cursor.execute('SELECT id, text, is_done FROM tasks WHERE chat_id = ? AND is_done = FALSE ORDER BY created_at DESC', (chat_id,))
            return cursor.fetchall()
    
    def mark_task_done(self, task_id, chat_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE tasks SET is_done = TRUE WHERE id = ? AND chat_id = ?', (task_id, chat_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_task(self, task_id, chat_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = ? AND chat_id = ?', (task_id, chat_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_reminder(self, chat_id, name, time_str):
        current_dt = datetime.now()
        try:
            reminder_time = datetime.strptime(time_str, '%H:%M')
            reminder_dt = current_dt.replace(hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0)
            if reminder_dt <= current_dt:
                reminder_dt += timedelta(days=1)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO reminders (chat_id, name, time, reminder_datetime) VALUES (?, ?, ?, ?)', (chat_id, name, time_str, reminder_dt))
                conn.commit()
                return True
        except ValueError:
            return False
    
    def get_user_reminders(self, chat_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, time, is_sent FROM reminders WHERE chat_id = ? ORDER BY time', (chat_id,))
            return cursor.fetchall()
    
    def get_due_reminders(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, chat_id, name, time, is_sent FROM reminders WHERE is_sent = FALSE AND reminder_datetime <= ?', (datetime.now(),))
            return cursor.fetchall()
    
    def mark_reminder_sent(self, reminder_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE reminders SET is_sent = TRUE WHERE id = ?', (reminder_id,))
            conn.commit()
    
    def delete_reminder(self, reminder_id, chat_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM reminders WHERE id = ? AND chat_id = ?', (reminder_id, chat_id))
            conn.commit()
            return cursor.rowcount > 0
    def add_schedule_item(self, user_id, day, time, text):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO schedule (user_id, day, time, text) VALUES (?, ?, ?, ?)",
                (user_id, day, time, text)
            )
            conn.commit()
    def get_schedule_for_now(self, day, time):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, text FROM schedule WHERE day = ? AND time = ?",
                (day, time)
            )
            return cursor.fetchall()
        
    def get_full_schedule(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT day, time, text FROM schedule WHERE user_id = ? ORDER BY day, time",
                (user_id,)
            )
            return cursor.fetchall()