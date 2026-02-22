"""
Slom - Инструмент безопасности и отказоустойчивости
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from tools.base_tool import BaseTool, ToolStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SafetyLevel(Enum):
    """Уровни безопасности"""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SlomTool(BaseTool):
    """
    Инструмент безопасности и отказоустойчивости (Safety & Loss Of Mission).
    Мониторит критические параметры и обеспечивает безопасность полета.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        super().__init__(config, agent)
        self.name = "slom"
        self.description = "Безопасность и отказоустойчивость"
        self.version = "2.0.0"
        
        # Параметры безопасности
        safety_config = config.get('safety', {})
        
        # Пороговые значения
        self.thresholds = {
            "battery_critical": safety_config.get('battery_critical', 15),
            "battery_low": safety_config.get('battery_low', 25),
            "signal_critical": safety_config.get('signal_critical', 20),
            "signal_low": safety_config.get('signal_low', 40),
            "wind_max": safety_config.get('wind_max', 15),
            "temperature_max": safety_config.get('temperature_max', 60),
            "temperature_min": safety_config.get('temperature_min', -10),
            "obstacle_distance": safety_config.get('obstacle_distance', 5),
            "max_altitude": safety_config.get('max_altitude', 120),
            "max_distance": safety_config.get('max_distance', 1000),
        }
        
        # Текущий уровень безопасности
        self.safety_level = SafetyLevel.NORMAL
        
        # История уровней безопасности
        self.safety_history = []
        
        # Аварийные протоколы
        self.emergency_protocols = {
            "low_battery": self._handle_low_battery,
            "signal_lost": self._handle_signal_lost,
            "obstacle_detected": self._handle_obstacle,
            "high_wind": self._handle_high_wind,
            "extreme_temperature": self._handle_extreme_temp,
            "system_failure": self._handle_system_failure,
            "geofence_breach": self._handle_geofence_breach,
        }
        
        # Геозона (ограничение зоны полета)
        self.geofence = safety_config.get('geofence', {
            "enabled": True,
            "center": {"x": 0, "y": 0, "z": 0},
            "radius": 500,
            "max_altitude": 120
        })
        
        logger.info("Slom инициализирован")
    
    async def initialize(self):
        """Инициализация инструмента безопасности"""
        self.status = ToolStatus.READY
        logger.info("Slom готов к работе")
    
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение проверок безопасности.
        
        Args:
            data (Dict[str, Any]): Данные телеметрии.
            
        Returns:
            Dict[str, Any]: Результат проверки безопасности.
        """
        result = await self.check_emergency(data)
        
        return {
            "safe": result is None,
            "emergency": result,
            "safety_level": self.safety_level.value
        }
    
    async def check_emergency(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Проверка на аварийные ситуации.
        
        Args:
            data (Dict[str, Any]): Данные телеметрии.
            
        Returns:
            Optional[Dict[str, Any]]: Информация об аварийной ситуации или None.
        """
        telemetry = data.get("telemetry", data)
        
        # Проверка батареи
        battery = telemetry.get("battery", 100)
        if battery < self.thresholds["battery_critical"]:
            self.safety_level = SafetyLevel.EMERGENCY
            return {
                "type": "low_battery",
                "severity": "critical",
                "message": f"Критический заряд батареи: {battery}%",
                "action": "LAND",
                "params": {}
            }
        elif battery < self.thresholds["battery_low"]:
            self.safety_level = SafetyLevel.WARNING
            return {
                "type": "low_battery",
                "severity": "warning",
                "message": f"Низкий заряд батареи: {battery}%",
                "action": "RTL",
                "params": {}
            }
        
        # Проверка сигнала
        signal = telemetry.get("signal_strength", 100)
        if signal < self.thresholds["signal_critical"]:
            self.safety_level = SafetyLevel.CRITICAL
            return {
                "type": "signal_lost",
                "severity": "critical",
                "message": f"Критический уровень сигнала: {signal}%",
                "action": "RTL",
                "params": {}
            }
        elif signal < self.thresholds["signal_low"]:
            self.safety_level = SafetyLevel.CAUTION
        
        # Проверка препятствий
        obstacle_distance = telemetry.get("obstacle_distance", 100)
        if obstacle_distance < self.thresholds["obstacle_distance"]:
            self.safety_level = SafetyLevel.WARNING
            return {
                "type": "obstacle_detected",
                "severity": "warning",
                "message": f"Обнаружено препятствие на расстоянии {obstacle_distance}м",
                "action": "HOVER",
                "params": {}
            }
        
        # Проверка геозоны
        if self.geofence["enabled"]:
            position = telemetry.get("position", {"x": 0, "y": 0, "z": 0})
            geofence_result = self._check_geofence(position)
            if geofence_result:
                return geofence_result
        
        # Проверка температуры
        temperature = telemetry.get("temperature", 25)
        if temperature > self.thresholds["temperature_max"]:
            self.safety_level = SafetyLevel.WARNING
            return {
                "type": "extreme_temperature",
                "severity": "warning",
                "message": f"Высокая температура: {temperature}C",
                "action": "LAND",
                "params": {}
            }
        elif temperature < self.thresholds["temperature_min"]:
            self.safety_level = SafetyLevel.WARNING
            return {
                "type": "extreme_temperature",
                "severity": "warning",
                "message": f"Низкая температура: {temperature}C",
                "action": "LAND",
                "params": {}
            }
        
        # Если все проверки пройдены - нормальный уровень
        self.safety_level = SafetyLevel.NORMAL
        return None
    
    def _check_geofence(self, position: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Проверка геозоны"""
        center = self.geofence["center"]
        radius = self.geofence["radius"]
        max_altitude = self.geofence["max_altitude"]
        
        # Проверка радиуса
        dx = position.get("x", 0) - center["x"]
        dy = position.get("y", 0) - center["y"]
        distance = (dx**2 + dy**2) ** 0.5
        
        if distance > radius:
            self.safety_level = SafetyLevel.WARNING
            return {
                "type": "geofence_breach",
                "severity": "warning",
                "message": f"Выход за пределы геозоны: {distance:.1f}м от центра",
                "action": "RTL",
                "params": {}
            }
        
        # Проверка высоты
        altitude = position.get("z", 0)
        if altitude > max_altitude:
            self.safety_level = SafetyLevel.WARNING
            return {
                "type": "geofence_breach",
                "severity": "warning",
                "message": f"Превышение максимальной высоты: {altitude}м",
                "action": "DESCEND",
                "params": {"altitude": max_altitude - 10}
            }
        
        return None
    
    async def _handle_low_battery(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка низкого заряда батареи"""
        battery = data.get("battery", 0)
        
        if battery < self.thresholds["battery_critical"]:
            return {
                "action": "LAND",
                "reason": f"Критический заряд батареи: {battery}%",
                "priority": "critical"
            }
        else:
            return {
                "action": "RTL",
                "reason": f"Низкий заряд батареи: {battery}%",
                "priority": "high"
            }
    
    async def _handle_signal_lost(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка потери сигнала"""
        return {
            "action": "RTL",
            "reason": "Потеря сигнала связи",
            "priority": "critical"
        }
    
    async def _handle_obstacle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка обнаружения препятствия"""
        return {
            "action": "HOVER",
            "reason": f"Препятствие на расстоянии {data.get('distance', 'unknown')}м",
            "priority": "high"
        }
    
    async def _handle_high_wind(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка сильного ветра"""
        return {
            "action": "LAND",
            "reason": f"Сильный ветер: {data.get('wind_speed', 'unknown')} м/с",
            "priority": "high"
        }
    
    async def _handle_extreme_temp(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка экстремальной температуры"""
        return {
            "action": "LAND",
            "reason": f"Экстремальная температура: {data.get('temperature', 'unknown')}C",
            "priority": "high"
        }
    
    async def _handle_system_failure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка отказа системы"""
        return {
            "action": "LAND",
            "reason": f"Отказ системы: {data.get('failure_type', 'unknown')}",
            "priority": "critical"
        }
    
    async def _handle_geofence_breach(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка выхода за геозону"""
        return {
            "action": "RTL",
            "reason": "Выход за пределы разрешенной зоны полета",
            "priority": "high"
        }
    
    async def action_set_geofence(self, center: Dict[str, float], 
                                   radius: float, 
                                   max_altitude: float) -> Dict[str, Any]:
        """Установка геозоны"""
        self.geofence = {
            "enabled": True,
            "center": center,
            "radius": radius,
            "max_altitude": max_altitude
        }
        
        logger.info(f"Установлена геозона: центр={center}, радиус={radius}м, высота={max_altitude}м")
        
        return {
            "success": True,
            "geofence": self.geofence
        }
    
    async def action_disable_geofence(self) -> Dict[str, Any]:
        """Отключение геозоны"""
        self.geofence["enabled"] = False
        logger.info("Геозона отключена")
        
        return {
            "success": True,
            "message": "Геозона отключена"
        }
    
    async def action_set_threshold(self, parameter: str, value: float) -> Dict[str, Any]:
        """Установка порогового значения"""
        if parameter not in self.thresholds:
            return {
                "success": False,
                "error": f"Неизвестный параметр: {parameter}"
            }
        
        self.thresholds[parameter] = value
        logger.info(f"Установлен порог {parameter} = {value}")
        
        return {
            "success": True,
            "thresholds": self.thresholds
        }
    
    async def action_get_safety_status(self) -> Dict[str, Any]:
        """Получение статуса безопасности"""
        return {
            "success": True,
            "safety_level": self.safety_level.value,
            "thresholds": self.thresholds,
            "geofence": self.geofence,
            "emergency_protocols": list(self.emergency_protocols.keys())
        }
    
    async def action_simulate_emergency(self, emergency_type: str) -> Dict[str, Any]:
        """Симуляция аварийной ситуации (для тестирования)"""
        if emergency_type not in self.emergency_protocols:
            return {
                "success": False,
                "error": f"Неизвестный тип аварии: {emergency_type}"
            }
        
        handler = self.emergency_protocols[emergency_type]
        result = await handler({})
        
        return {
            "success": True,
            "simulated": True,
            "emergency_type": emergency_type,
            "result": result
        }
    
    async def shutdown(self):
        """Завершение работы инструмента"""
        logger.info(f"Инструмент {self.name} завершает работу")
        self.status = ToolStatus.SHUTDOWN
