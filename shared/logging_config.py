# shared/logging_config.py
"""
Конфигурация структурированного логирования (JSON формат)

Модуль настраивает логирование в JSON формате для:
- Улучшенной обработки логов системами мониторинга (ELK, Splunk, etc.)
- Структурированного формата для анализа
- Логирования ошибок в файл с детальной информацией

Автор: Кочнева Арина
Год: 2025
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Попытка импортировать python-json-logger
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False
    jsonlogger = None


if JSON_LOGGER_AVAILABLE:
    class CustomJSONFormatter(jsonlogger.JsonFormatter):
        """Кастомный JSON форматтер для логирования"""
        
        def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
            """Добавляет дополнительные поля в JSON лог"""
            super().add_fields(log_record, record, message_dict)
            
            # Добавляем timestamp в ISO формате
            log_record['timestamp'] = datetime.utcnow().isoformat()
            
            # Добавляем уровень логирования
            log_record['level'] = record.levelname
            
            # Добавляем имя модуля и функции
            log_record['module'] = record.module
            log_record['function'] = record.funcName
            
            # Добавляем номер строки
            log_record['line'] = record.lineno
            
            # Добавляем процесс и поток
            log_record['process_id'] = record.process
            log_record['thread_id'] = record.thread
            
            # Если есть исключение, добавляем traceback
            if record.exc_info:
                log_record['exception'] = self.formatException(record.exc_info)
else:
    # Fallback класс если pythonjsonlogger не установлен
    class CustomJSONFormatter(logging.Formatter):
        """Fallback форматтер"""
        pass


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    use_json: bool = True,
    console_output: bool = True
) -> logging.Logger:
    """
    Настраивает структурированное логирование
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу для записи логов (опционально)
        use_json: Использовать JSON формат (True) или обычный формат (False)
        console_output: Выводить логи в консоль
    
    Returns:
        Настроенный logger
    """
    # Создаем root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Удаляем существующие handlers
    logger.handlers.clear()
    
    # Форматтер для JSON
    if use_json and JSON_LOGGER_AVAILABLE:
        formatter = CustomJSONFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
        )
    
    # Handler для консоли
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Handler для файла (если указан)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Handler для ошибок (отдельный файл)
    if log_file:
        error_log_file = str(Path(log_file).parent / f"errors_{Path(log_file).name}")
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger с указанным именем
    
    Args:
        name: Имя logger (обычно __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

