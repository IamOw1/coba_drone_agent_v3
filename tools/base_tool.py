"""
Базовый класс для инструментов системы
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ToolStatus(Enum):
    """Статусы инструмента"""
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    SHUTDOWN = "shutdown"


class BaseTool(ABC):
    """
    Базовый класс для всех инструментов системы.
    Все инструменты должны наследоваться от этого класса.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        """
        Инициализация инструмента.
        
        Args:
            config (Dict[str, Any]): Конфигурация инструмента.
            agent: Ссылка на основной агент.
        """
        self.config = config
        self.agent = agent
        self.name = self.__class__.__name__.replace('Tool', '').lower()
        self.description = "Базовый инструмент"
        self.version = "1.0.0"
        self.status = ToolStatus.INITIALIZING
        self.enabled = True
        
        # Метрики
        self.metrics = {
            "calls": 0,
            "errors": 0,
            "last_call": None,
            "total_execution_time": 0.0
        }
        
        # История операций
        self.operation_history = []
        
        logger.info(f"Инструмент {self.name} создан")
    
    @abstractmethod
    async def initialize(self):
        """
        Инициализация инструмента.
        Вызывается перед началом работы.
        """
        pass
    
    @abstractmethod
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение инструмента к данным.
        
        Args:
            data (Dict[str, Any]): Входные данные.
            
        Returns:
            Dict[str, Any]: Результат применения инструмента.
        """
        pass
    
    @abstractmethod
    async def shutdown(self):
        """
        Завершение работы инструмента.
        Вызывается при остановке системы.
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Проверка работоспособности инструмента.
        
        Returns:
            bool: True если инструмент работает корректно.
        """
        return self.status in [ToolStatus.READY, ToolStatus.ACTIVE]
    
    async def perceive(self) -> Dict[str, Any]:
        """
        Сбор данных инструментом.
        
        Returns:
            Dict[str, Any]: Данные от инструмента.
        """
        return {
            "status": self.status.value,
            "metrics": self.metrics,
            "enabled": self.enabled
        }
    
    async def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполнение действия инструментом.
        
        Args:
            action (str): Название действия.
            params (Dict[str, Any]): Параметры действия.
            
        Returns:
            Dict[str, Any]: Результат выполнения.
        """
        params = params or {}
        start_time = datetime.now()
        
        try:
            self.metrics["calls"] += 1
            self.metrics["last_call"] = datetime.now().isoformat()
            
            # Поиск метода действия
            method_name = f"action_{action}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                result = await method(**params)
            else:
                result = {"success": False, "error": f"Действие {action} не поддерживается"}
            
            # Логирование
            execution_time = (datetime.now() - start_time).total_seconds()
            self.metrics["total_execution_time"] += execution_time
            
            self.operation_history.append({
                "action": action,
                "params": params,
                "result": result,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Ошибка выполнения действия {action} в инструменте {self.name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса инструмента.
        
        Returns:
            Dict[str, Any]: Статус инструмента.
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "enabled": self.enabled,
            "metrics": self.metrics
        }
    
    def enable(self):
        """Включение инструмента"""
        self.enabled = True
        logger.info(f"Инструмент {self.name} включен")
    
    def disable(self):
        """Отключение инструмента"""
        self.enabled = False
        logger.info(f"Инструмент {self.name} отключен")
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение истории операций.
        
        Args:
            limit (int): Максимальное количество записей.
            
        Returns:
            List[Dict[str, Any]]: История операций.
        """
        return self.operation_history[-limit:]
    
    def clear_history(self):
        """Очистка истории операций"""
        self.operation_history.clear()
        logger.info(f"История операций инструмента {self.name} очищена")
    
    def reset_metrics(self):
        """Сброс метрик"""
        self.metrics = {
            "calls": 0,
            "errors": 0,
            "last_call": None,
            "total_execution_time": 0.0
        }
        logger.info(f"Метрики инструмента {self.name} сброшены")
