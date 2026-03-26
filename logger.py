import logging
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def setup_logger(name: str, log_file: str = None): # type: ignore
    """
    Настройка логгера
    
    Args:
        name: имя логгера
        log_file: имя файла лога (если None, то имя берется из name)
    """
    # Получаем директорию для логов из .env
    log_dir = os.getenv('LOG_DIR', '.')
    
    # Создаем директорию если её нет
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Имя файла лога
    if log_file is None:
        log_file = f"{name}.log"
    
    # Полный путь к файлу лога
    log_path = os.path.join(log_dir, log_file)
    
    # Создаем логгер
    logger = logging.getLogger(name)
    
    # Уровень логирования
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level))
    
    # Очищаем существующие обработчики, чтобы не дублировать
    if logger.handlers:
        logger.handlers.clear()
    
    # Форматирование логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для записи в файл
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger