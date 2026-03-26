import pymysql
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from logger import setup_logger

load_dotenv()

# Создаем логгер для базы данных
db_logger = setup_logger('database', 'database.log')

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
        
        # Инициализация шифрования
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            db_logger.error("ENCRYPTION_KEY not found in .env file")
            raise ValueError("ENCRYPTION_KEY not found in .env file")
        self.cipher = Fernet(encryption_key.encode())
        
        db_logger.info(f"Database initialized with config: {self.config['host']}:{self.config['port']}/{self.config['database']}")

    def _get_connection(self):
        """Создает новое соединение с БД"""
        try:
            conn = pymysql.connect(**self.config)
            db_logger.debug("Database connection created")
            return conn
        except Exception as e:
            db_logger.error(f"Failed to create database connection: {e}")
            raise

    def _encrypt_password(self, password: str) -> str:
        """Шифрует пароль"""
        try:
            encrypted = self.cipher.encrypt(password.encode()).decode()
            db_logger.debug("Password encrypted successfully")
            return encrypted
        except Exception as e:
            db_logger.error(f"Password encryption failed: {e}")
            raise

    def _decrypt_password(self, encrypted_password: str) -> str:
        """Расшифровывает пароль"""
        try:
            decrypted = self.cipher.decrypt(encrypted_password.encode()).decode()
            db_logger.debug("Password decrypted successfully")
            return decrypted
        except Exception as e:
            db_logger.error(f"Password decryption failed: {e}")
            raise

    def check_user_exists(self, vk_id: int) -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE vk_id = %s", (vk_id,))
                result = cur.fetchone() is not None
                db_logger.debug(f"Check user exists for vk_id {vk_id}: {result}")
                return result
        except Exception as e:
            db_logger.error(f"Error checking user exists for vk_id {vk_id}: {e}")
            return False
        finally:
            conn.close()

    def register_user(self, vk_id: int, login: str, password: str) -> bool:
        conn = self._get_connection()
        try:
            encrypted_password = self._encrypt_password(password)
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (vk_id, login, password_hash) VALUES (%s, %s, %s)",
                    (vk_id, login, encrypted_password)
                )
            db_logger.info(f"User registered successfully: vk_id={vk_id}, login={login}")
            return True
        except pymysql.IntegrityError:
            db_logger.warning(f"User already exists: vk_id={vk_id}, login={login}")
            return False
        except Exception as e:
            db_logger.error(f"Error registering user vk_id={vk_id}: {e}")
            return False
        finally:
            conn.close()

    def get_user_id(self, vk_id: int):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE vk_id = %s", (vk_id,))
                result = cur.fetchone()
                user_id = result['id'] if result else None
                db_logger.debug(f"Get user_id for vk_id {vk_id}: {user_id}")
                return user_id
        except Exception as e:
            db_logger.error(f"Error getting user_id for vk_id {vk_id}: {e}")
            return None
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
                    try:
                        decrypted_password = self._decrypt_password(result['password_hash'])
                        db_logger.debug(f"Credentials retrieved for vk_id {vk_id}: login={result['login']}")
                        return {
                            'login': result['login'],
                            'password': decrypted_password
                        }
                    except Exception as e:
                        db_logger.error(f"Error decrypting password for vk_id {vk_id}: {e}")
                        return {
                            'login': result['login'],
                            'password': None,
                            'error': 'Failed to decrypt password'
                        }
                db_logger.debug(f"No credentials found for vk_id {vk_id}")
                return None
        except Exception as e:
            db_logger.error(f"Error getting credentials for vk_id {vk_id}: {e}")
            return None
        finally:
            conn.close()

    def add_value(self, vk_id: int, value: int, date: str) -> bool:
        if value <= 0:
            db_logger.warning(f"Invalid value {value} for vk_id {vk_id}")
            return False
        
        user_id = self.get_user_id(vk_id)
        if not user_id:
            db_logger.warning(f"User not found for vk_id {vk_id}")
            return False
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_values (user_id, value, added_at) VALUES (%s, %s, %s)",
                    (user_id, value, date)
                )
            db_logger.info(f"Value added: vk_id={vk_id}, value={value}, date={date}")
            return True
        except Exception as e:
            db_logger.error(f"Error adding value for vk_id {vk_id}: {e}")
            return False
        finally:
            conn.close()

    def get_monthly_values(self, vk_id: int):
        user_id = self.get_user_id(vk_id)
        if not user_id:
            return {'values': [], 'total': 0}
        
        from datetime import datetime
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
                db_logger.debug(f"Monthly values for vk_id {vk_id}: {len(values)} records, total={total}")
                return {'values': values, 'total': total}
        except Exception as e:
            db_logger.error(f"Error getting monthly values for vk_id {vk_id}: {e}")
            return {'values': [], 'total': 0}
        finally:
            conn.close()

    def get_monthly_total(self, vk_id: int) -> int:
        user_id = self.get_user_id(vk_id)
        if not user_id:
            return 0
        
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
                total = result['total'] if result['total'] else 0
                db_logger.debug(f"Monthly total for vk_id {vk_id}: {total}")
                return total
        except Exception as e:
            db_logger.error(f"Error getting monthly total for vk_id {vk_id}: {e}")
            return 0
        finally:
            conn.close()