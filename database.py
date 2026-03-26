import pymysql
import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'vk_bot'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True
        }

    def _get_connection(self):
        return pymysql.connect(**self.config)

    def check_user_exists(self, vk_id: int) -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE vk_id = %s", (vk_id,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def register_user(self, vk_id: int, login: str, password: str) -> bool:
        conn = self._get_connection()
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (vk_id, login, password_hash) VALUES (%s, %s, %s)",
                    (vk_id, login, password_hash)
                )
            return True
        except pymysql.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user_id(self, vk_id: int):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE vk_id = %s", (vk_id,))
                result = cur.fetchone()
                return result['id'] if result else None
        finally:
            conn.close()

    def get_user_credentials(self, vk_id: int):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT login, password_hash FROM users WHERE vk_id = %s",
                    (vk_id,)
                )
                result = cur.fetchone()
                if result:
                    return {
                        'login': result['login'],
                        'password_hash': result['password_hash']
                    }
                return None
        finally:
            conn.close()

    def add_value(self, vk_id: int, value: int, date: str) -> bool:
        """Добавляет заправку. created_at заполнится автоматически."""
        if value <= 0:
            return False
        
        user_id = self.get_user_id(vk_id)
        if not user_id:
            return False
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_values (user_id, value, added_at) VALUES (%s, %s, %s)",
                    (user_id, value, date)
                )
            return True
        except Exception as e:
            print(f"Error adding value: {e}")
            return False
        finally:
            conn.close()

    def get_monthly_values(self, vk_id: int):
        """Получает заправки за текущий календарный месяц с полной датой и временем"""
        user_id = self.get_user_id(vk_id)
        if not user_id:
            return {'values': [], 'total': 0}
        
        # Вычисляем первый день текущего месяца
        first_day_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT value, added_at, created_at 
                       FROM user_values 
                       WHERE user_id = %s 
                       AND created_at >= %s
                       ORDER BY created_at DESC""",
                    (user_id, first_day_of_month)
                )
                values = cur.fetchall()
                total = sum(row['value'] for row in values)
                return {'values': values, 'total': total}
        finally:
            conn.close()

    def get_monthly_total(self, vk_id: int) -> int:
        """Возвращает общую сумму заправок за текущий месяц"""
        user_id = self.get_user_id(vk_id)
        if not user_id:
            return 0
        
        # Вычисляем первый день текущего месяца
        from datetime import datetime
        first_day_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT SUM(value) as total 
                       FROM user_values 
                       WHERE user_id = %s 
                       AND created_at >= %s""",
                    (user_id, first_day_of_month)
                )
                result = cur.fetchone()
                return result['total'] if result['total'] else 0
        finally:
            conn.close()