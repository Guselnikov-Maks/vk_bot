import os
import time
from pathlib import Path
from logger import setup_logger

# Настройка логгера
cleaner_logger = setup_logger('cleaner', 'cleaner.log')

def cleanup_old_reports(days=7, excel_dir='excel_reports'):
    """
    Удаляет Excel отчеты старше указанного количества дней
    
    Args:
        days: количество дней хранения
        excel_dir: директория с отчетами
    """
    cleaner_logger.info(f"Starting cleanup of reports older than {days} days")
    
    excel_path = Path(excel_dir)
    if not excel_path.exists():
        cleaner_logger.warning(f"Directory {excel_dir} does not exist")
        return
    
    now = time.time()
    deleted_count = 0
    
    for file in excel_path.glob("*.xlsx"):
        file_age = now - file.stat().st_mtime
        days_old = file_age / 86400  # 86400 секунд в дне
        
        if days_old > days:
            try:
                file.unlink()
                deleted_count += 1
                cleaner_logger.info(f"Deleted old report: {file.name} (age: {days_old:.1f} days)")
            except Exception as e:
                cleaner_logger.error(f"Failed to delete {file.name}: {e}")
    
    cleaner_logger.info(f"Cleanup completed. Deleted {deleted_count} files.")

if __name__ == "__main__":
    # Удаляем отчеты старше 7 дней
    cleanup_old_reports(days=7)