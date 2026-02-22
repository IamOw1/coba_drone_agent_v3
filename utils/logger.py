"""
Система логирования
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Настройка логгера.
    
    Args:
        name (str): Имя логгера.
        level (int): Уровень логирования.
        
    Returns:
        logging.Logger: Настроенный логгер.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Проверка на существующие обработчики
    if logger.handlers:
        return logger
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
