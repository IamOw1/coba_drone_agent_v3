"""
Система памяти агента
"""
import json
import sqlite3
import pickle
from typing import Dict, List, Any, Optional
from collections import deque
from datetime import datetime
from pathlib import Path
import numpy as np

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ShortTermMemory:
    """
    Краткосрочная память агента (рабочая память).
    Хранит последние N записей для быстрого доступа.
    """
    
    def __init__(self, capacity: int = 1000):
        """
        Инициализация краткосрочной памяти.
        
        Args:
            capacity (int): Максимальное количество записей.
        """
        self.capacity = capacity
        self.memory = deque(maxlen=capacity)
        self.timestamps = deque(maxlen=capacity)
        logger.info(f"Краткосрочная память инициализирована (емкость: {capacity})")
    
    def add(self, data: Dict[str, Any]):
        """
        Добавление записи в память.
        
        Args:
            data (Dict[str, Any]): Данные для сохранения.
        """
        self.memory.append(data)
        self.timestamps.append(datetime.now())
    
    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Получение последних N записей.
        
        Args:
            n (int): Количество записей.
            
        Returns:
            List[Dict[str, Any]]: Список последних записей.
        """
        return list(self.memory)[-n:]
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Получение всех записей.
        
        Returns:
            List[Dict[str, Any]]: Все записи в памяти.
        """
        return list(self.memory)
    
    def clear(self):
        """Очистка памяти."""
        self.memory.clear()
        self.timestamps.clear()
        logger.info("Краткосрочная память очищена")
    
    def search(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """
        Поиск записей по ключу и значению.
        
        Args:
            key (str): Ключ для поиска.
            value (Any): Значение для поиска.
            
        Returns:
            List[Dict[str, Any]]: Найденные записи.
        """
        results = []
        for record in self.memory:
            if key in record and record[key] == value:
                results.append(record)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики памяти.
        
        Returns:
            Dict[str, Any]: Статистика.
        """
        return {
            "capacity": self.capacity,
            "current_size": len(self.memory),
            "utilization": len(self.memory) / self.capacity * 100,
            "oldest_record": self.timestamps[0] if self.timestamps else None,
            "newest_record": self.timestamps[-1] if self.timestamps else None
        }


class LongTermMemory:
    """
    Долгосрочная память агента.
    Хранит опыт, знания и историю миссий в SQLite базе данных.
    """
    
    def __init__(self, storage_path: str = "data/memory/knowledge_base.db"):
        """
        Инициализация долгосрочной памяти.
        
        Args:
            storage_path (str): Путь к файлу базы данных.
        """
        self.storage_path = storage_path
        Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db = sqlite3.connect(storage_path, check_same_thread=False)
        self._init_tables()
        logger.info(f"Долгосрочная память инициализирована ({storage_path})")
    
    def _init_tables(self):
        """Создание таблиц базы данных."""
        cursor = self.db.cursor()
        
        # Таблица опыта (для RL)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                state TEXT,
                action TEXT,
                reward REAL,
                next_state TEXT,
                mission_id TEXT,
                metadata TEXT
            )
        """)
        
        # Таблица знаний
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT,
                confidence REAL DEFAULT 1.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT
            )
        """)
        
        # Таблица миссий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                parameters TEXT,
                result TEXT,
                duration REAL,
                data_collected TEXT,
                lessons_learned TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица событий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                description TEXT,
                severity TEXT,
                mission_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица паттернов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern_data TEXT,
                frequency INTEGER DEFAULT 1,
                confidence REAL DEFAULT 1.0,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.commit()
    
    def store_experience(self, experience: Dict[str, Any]):
        """
        Сохранение опыта для обучения.
        
        Args:
            experience (Dict[str, Any]): Опыт (state, action, reward, next_state).
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO experience (state, action, reward, next_state, mission_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            json.dumps(experience.get("state")),
            json.dumps(experience.get("action")),
            experience.get("reward", 0.0),
            json.dumps(experience.get("next_state")),
            experience.get("mission_id"),
            json.dumps(experience.get("metadata", {}))
        ))
        self.db.commit()
    
    def get_experiences(self, limit: int = 1000, mission_id: str = None) -> List[Dict[str, Any]]:
        """
        Получение опыта из памяти.
        
        Args:
            limit (int): Максимальное количество записей.
            mission_id (str): Фильтр по ID миссии.
            
        Returns:
            List[Dict[str, Any]]: Список опыта.
        """
        cursor = self.db.cursor()
        
        if mission_id:
            cursor.execute("""
                SELECT * FROM experience WHERE mission_id = ? ORDER BY timestamp DESC LIMIT ?
            """, (mission_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM experience ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        experiences = []
        
        for row in rows:
            experiences.append({
                "id": row[0],
                "timestamp": row[1],
                "state": json.loads(row[2]) if row[2] else None,
                "action": json.loads(row[3]) if row[3] else None,
                "reward": row[4],
                "next_state": json.loads(row[5]) if row[5] else None,
                "mission_id": row[6],
                "metadata": json.loads(row[7]) if row[7] else {}
            })
        
        return experiences
    
    def store_knowledge(self, key: str, value: Any, category: str = "general", 
                        confidence: float = 1.0, source: str = "agent"):
        """
        Сохранение знания.
        
        Args:
            key (str): Ключ знания.
            value (Any): Значение.
            category (str): Категория знания.
            confidence (float): Уверенность в знании (0-1).
            source (str): Источник знания.
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge (key, value, category, confidence, last_updated, source)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (key, json.dumps(value), category, confidence, source))
        self.db.commit()
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """
        Получение знания по ключу.
        
        Args:
            key (str): Ключ знания.
            
        Returns:
            Optional[Any]: Значение или None.
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT value FROM knowledge WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row[0])
        return None
    
    def search_knowledge(self, category: str = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        Поиск знаний.
        
        Args:
            category (str): Категория для фильтрации.
            min_confidence (float): Минимальная уверенность.
            
        Returns:
            List[Dict[str, Any]]: Список знаний.
        """
        cursor = self.db.cursor()
        
        if category:
            cursor.execute("""
                SELECT * FROM knowledge WHERE category = ? AND confidence >= ?
                ORDER BY last_updated DESC
            """, (category, min_confidence))
        else:
            cursor.execute("""
                SELECT * FROM knowledge WHERE confidence >= ?
                ORDER BY last_updated DESC
            """, (min_confidence,))
        
        rows = cursor.fetchall()
        knowledge = []
        
        for row in rows:
            knowledge.append({
                "id": row[0],
                "key": row[1],
                "value": json.loads(row[2]),
                "category": row[3],
                "confidence": row[4],
                "last_updated": row[5],
                "source": row[6]
            })
        
        return knowledge
    
    def store_mission(self, mission_id: str, name: str, mission_type: str,
                      parameters: Dict[str, Any], result: Dict[str, Any],
                      duration: float, data_collected: List[Any],
                      lessons_learned: List[str]):
        """
        Сохранение информации о миссии.
        
        Args:
            mission_id (str): ID миссии.
            name (str): Название миссии.
            mission_type (str): Тип миссии.
            parameters (Dict[str, Any]): Параметры миссии.
            result (Dict[str, Any]): Результат миссии.
            duration (float): Длительность в секундах.
            data_collected (List[Any]): Собранные данные.
            lessons_learned (List[str]): Извлеченные уроки.
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO missions 
            (mission_id, name, type, parameters, result, duration, data_collected, lessons_learned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mission_id, name, mission_type,
            json.dumps(parameters), json.dumps(result),
            duration, json.dumps(data_collected), json.dumps(lessons_learned)
        ))
        self.db.commit()
    
    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о миссии.
        
        Args:
            mission_id (str): ID миссии.
            
        Returns:
            Optional[Dict[str, Any]]: Информация о миссии.
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "mission_id": row[0],
                "name": row[1],
                "type": row[2],
                "parameters": json.loads(row[3]) if row[3] else {},
                "result": json.loads(row[4]) if row[4] else {},
                "duration": row[5],
                "data_collected": json.loads(row[6]) if row[6] else [],
                "lessons_learned": json.loads(row[7]) if row[7] else [],
                "timestamp": row[8]
            }
        return None
    
    def get_all_missions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение списка всех миссий.
        
        Args:
            limit (int): Максимальное количество.
            
        Returns:
            List[Dict[str, Any]]: Список миссий.
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT * FROM missions ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        missions = []
        
        for row in rows:
            missions.append({
                "mission_id": row[0],
                "name": row[1],
                "type": row[2],
                "parameters": json.loads(row[3]) if row[3] else {},
                "result": json.loads(row[4]) if row[4] else {},
                "duration": row[5],
                "timestamp": row[8]
            })
        
        return missions
    
    def log_event(self, event_type: str, description: str, 
                  severity: str = "info", mission_id: str = None):
        """
        Логирование события.
        
        Args:
            event_type (str): Тип события.
            description (str): Описание.
            severity (str): Уровень важности (info, warning, error, critical).
            mission_id (str): ID миссии (опционально).
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO events (event_type, description, severity, mission_id)
            VALUES (?, ?, ?, ?)
        """, (event_type, description, severity, mission_id))
        self.db.commit()
    
    def get_events(self, event_type: str = None, severity: str = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение событий.
        
        Args:
            event_type (str): Фильтр по типу.
            severity (str): Фильтр по важности.
            limit (int): Максимальное количество.
            
        Returns:
            List[Dict[str, Any]]: Список событий.
        """
        cursor = self.db.cursor()
        
        if event_type and severity:
            cursor.execute("""
                SELECT * FROM events WHERE event_type = ? AND severity = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (event_type, severity, limit))
        elif event_type:
            cursor.execute("""
                SELECT * FROM events WHERE event_type = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (event_type, limit))
        elif severity:
            cursor.execute("""
                SELECT * FROM events WHERE severity = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (severity, limit))
        else:
            cursor.execute("""
                SELECT * FROM events ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        events = []
        
        for row in rows:
            events.append({
                "id": row[0],
                "event_type": row[1],
                "description": row[2],
                "severity": row[3],
                "mission_id": row[4],
                "timestamp": row[5]
            })
        
        return events
    
    def store_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]):
        """
        Сохранение паттерна.
        
        Args:
            pattern_type (str): Тип паттерна.
            pattern_data (Dict[str, Any]): Данные паттерна.
        """
        cursor = self.db.cursor()
        
        # Проверяем существование похожего паттерна
        cursor.execute("""
            SELECT id, frequency FROM patterns 
            WHERE pattern_type = ? AND pattern_data = ?
        """, (pattern_type, json.dumps(pattern_data)))
        
        row = cursor.fetchone()
        
        if row:
            # Обновляем существующий паттерн
            cursor.execute("""
                UPDATE patterns 
                SET frequency = ?, last_seen = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (row[1] + 1, row[0]))
        else:
            # Создаем новый паттерн
            cursor.execute("""
                INSERT INTO patterns (pattern_type, pattern_data)
                VALUES (?, ?)
            """, (pattern_type, json.dumps(pattern_data)))
        
        self.db.commit()
    
    def get_patterns(self, pattern_type: str = None, min_frequency: int = 1) -> List[Dict[str, Any]]:
        """
        Получение паттернов.
        
        Args:
            pattern_type (str): Фильтр по типу.
            min_frequency (int): Минимальная частота.
            
        Returns:
            List[Dict[str, Any]]: Список паттернов.
        """
        cursor = self.db.cursor()
        
        if pattern_type:
            cursor.execute("""
                SELECT * FROM patterns 
                WHERE pattern_type = ? AND frequency >= ?
                ORDER BY frequency DESC
            """, (pattern_type, min_frequency))
        else:
            cursor.execute("""
                SELECT * FROM patterns 
                WHERE frequency >= ?
                ORDER BY frequency DESC
            """, (min_frequency,))
        
        rows = cursor.fetchall()
        patterns = []
        
        for row in rows:
            patterns.append({
                "id": row[0],
                "pattern_type": row[1],
                "pattern_data": json.loads(row[2]),
                "frequency": row[3],
                "confidence": row[4],
                "first_seen": row[5],
                "last_seen": row[6]
            })
        
        return patterns
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики памяти.
        
        Returns:
            Dict[str, Any]: Статистика.
        """
        cursor = self.db.cursor()
        
        stats = {}
        
        # Количество записей в каждой таблице
        for table in ["experience", "knowledge", "missions", "events", "patterns"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Размер базы данных
        cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()
        stats["database_size_bytes"] = db_size[0] if db_size else 0
        
        return stats
    
    def backup(self, backup_path: str):
        """
        Создание резервной копии базы данных.
        
        Args:
            backup_path (str): Путь для сохранения бэкапа.
        """
        import shutil
        shutil.copy2(self.storage_path, backup_path)
        logger.info(f"Резервная копия создана: {backup_path}")
    
    def close(self):
        """Закрытие соединения с базой данных."""
        self.db.close()
        logger.info("Соединение с базой данных закрыто")
