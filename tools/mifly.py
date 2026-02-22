"""
MiFly - Инструмент базового управления полетом
"""
import asyncio
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from tools.base_tool import BaseTool, ToolStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Waypoint:
    """Точка маршрута"""
    x: float
    y: float
    z: float
    speed: float = 5.0
    hover_time: float = 0.0
    action: str = None


class MiFlyTool(BaseTool):
    """
    Инструмент базового управления полетом.
    Предоставляет команды взлета, посадки, навигации и зависания.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        super().__init__(config, agent)
        self.name = "mifly"
        self.description = "Базовое управление полетом"
        self.version = "2.0.0"
        
        # Параметры полета
        flight_config = config.get('flight', {})
        
        self.default_speed = flight_config.get('default_speed', 5.0)
        self.max_speed = flight_config.get('max_speed', 15.0)
        self.max_altitude = flight_config.get('max_altitude', 120.0)
        self.takeoff_altitude = flight_config.get('takeoff_altitude', 10.0)
        self.landing_speed = flight_config.get('landing_speed', 1.0)
        
        # Текущее состояние
        self.current_position = {"x": 0, "y": 0, "z": 0}
        self.current_velocity = {"vx": 0, "vy": 0, "vz": 0}
        self.current_attitude = {"roll": 0, "pitch": 0, "yaw": 0}
        self.is_flying = False
        self.is_landing = False
        
        # Текущий маршрут
        self.current_path: List[Waypoint] = []
        self.current_waypoint_index = 0
        
        # Базовая позиция (точка взлета)
        self.home_position = {"x": 0, "y": 0, "z": 0}
        
        logger.info("MiFly инициализирован")
    
    async def initialize(self):
        """Инициализация инструмента управления"""
        self.status = ToolStatus.READY
        logger.info("MiFly готов к работе")
    
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение команды управления.
        
        Args:
            data (Dict[str, Any]): Данные команды.
            
        Returns:
            Dict[str, Any]: Результат выполнения.
        """
        command = data.get("command")
        params = data.get("params", {})
        
        if command == "takeoff":
            return await self.action_takeoff(**params)
        elif command == "land":
            return await self.action_land(**params)
        elif command == "goto":
            return await self.action_goto(**params)
        elif command == "hover":
            return await self.action_hover()
        elif command == "rtl":
            return await self.action_return_to_launch()
        elif command == "set_velocity":
            return await self.action_set_velocity(**params)
        elif command == "follow_path":
            return await self.action_follow_path(**params)
        
        return {"success": False, "error": f"Неизвестная команда: {command}"}
    
    async def action_takeoff(self, altitude: float = None, 
                            speed: float = None) -> Dict[str, Any]:
        """
        Взлет на заданную высоту.
        
        Args:
            altitude (float): Целевая высота (м).
            speed (float): Скорость взлета (м/с).
            
        Returns:
            Dict[str, Any]: Результат взлета.
        """
        if self.is_flying:
            return {"success": False, "error": "Дрон уже в полете"}
        
        altitude = altitude or self.takeoff_altitude
        speed = speed or self.default_speed
        
        # Ограничение высоты
        altitude = min(altitude, self.max_altitude)
        
        logger.info(f"Взлет на высоту {altitude}м со скоростью {speed}м/с")
        
        # Симуляция взлета
        self.current_position["z"] = altitude
        self.is_flying = True
        self.is_landing = False
        
        # Сохраняем домашнюю позицию
        self.home_position = {
            "x": self.current_position["x"],
            "y": self.current_position["y"],
            "z": 0
        }
        
        self.status = ToolStatus.ACTIVE
        
        return {
            "success": True,
            "action": "takeoff",
            "altitude": altitude,
            "position": self.current_position.copy()
        }
    
    async def action_land(self, speed: float = None) -> Dict[str, Any]:
        """
        Посадка.
        
        Args:
            speed (float): Скорость снижения (м/с).
            
        Returns:
            Dict[str, Any]: Результат посадки.
        """
        if not self.is_flying:
            return {"success": False, "error": "Дрон не в полете"}
        
        speed = speed or self.landing_speed
        
        logger.info(f"Посадка со скоростью {speed}м/с")
        
        # Симуляция посадки
        self.current_position["z"] = 0
        self.is_flying = False
        self.is_landing = False
        self.current_velocity = {"vx": 0, "vy": 0, "vz": 0}
        
        self.status = ToolStatus.READY
        
        return {
            "success": True,
            "action": "land",
            "position": self.current_position.copy()
        }
    
    async def action_goto(self, x: float, y: float, z: float, 
                         speed: float = None) -> Dict[str, Any]:
        """
        Перемещение в точку.
        
        Args:
            x (float): Координата X.
            y (float): Координата Y.
            z (float): Координата Z (высота).
            speed (float): Скорость перемещения (м/с).
            
        Returns:
            Dict[str, Any]: Результат перемещения.
        """
        if not self.is_flying:
            return {"success": False, "error": "Дрон не в полете"}
        
        speed = speed or self.default_speed
        speed = min(speed, self.max_speed)
        
        # Ограничение высоты
        z = min(z, self.max_altitude)
        
        logger.info(f"Перемещение в точку ({x}, {y}, {z}) со скоростью {speed}м/с")
        
        # Расчет расстояния
        dx = x - self.current_position["x"]
        dy = y - self.current_position["y"]
        dz = z - self.current_position["z"]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # Симуляция перемещения
        self.current_position = {"x": x, "y": y, "z": z}
        
        # Расчет времени полета (для симуляции)
        flight_time = distance / speed if speed > 0 else 0
        
        return {
            "success": True,
            "action": "goto",
            "position": self.current_position.copy(),
            "distance": distance,
            "estimated_time": flight_time
        }
    
    async def action_hover(self) -> Dict[str, Any]:
        """
        Зависание на месте.
        
        Returns:
            Dict[str, Any]: Результат.
        """
        if not self.is_flying:
            return {"success": False, "error": "Дрон не в полете"}
        
        logger.info("Зависание на месте")
        
        # Остановка
        self.current_velocity = {"vx": 0, "vy": 0, "vz": 0}
        
        return {
            "success": True,
            "action": "hover",
            "position": self.current_position.copy()
        }
    
    async def action_return_to_launch(self) -> Dict[str, Any]:
        """
        Возврат на точку взлета (RTL).
        
        Returns:
            Dict[str, Any]: Результат.
        """
        if not self.is_flying:
            return {"success": False, "error": "Дрон не в полете"}
        
        logger.info("Возврат на точку взлета")
        
        # Перемещение к домашней позиции
        result = await self.action_goto(
            self.home_position["x"],
            self.home_position["y"],
            self.current_position["z"],  # Сохраняем текущую высоту
            speed=self.default_speed
        )
        
        # Затем посадка
        if result["success"]:
            await self.action_land()
        
        return {
            "success": True,
            "action": "rtl",
            "message": "Возврат на точку взлета выполнен"
        }
    
    async def action_set_velocity(self, vx: float, vy: float, vz: float) -> Dict[str, Any]:
        """
        Установка скорости.
        
        Args:
            vx (float): Скорость по X.
            vy (float): Скорость по Y.
            vz (float): Скорость по Z.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        if not self.is_flying:
            return {"success": False, "error": "Дрон не в полете"}
        
        # Ограничение скорости
        speed = math.sqrt(vx**2 + vy**2 + vz**2)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            vx *= scale
            vy *= scale
            vz *= scale
        
        self.current_velocity = {"vx": vx, "vy": vy, "vz": vz}
        
        # Обновление позиции (для симуляции)
        self.current_position["x"] += vx * 0.1
        self.current_position["y"] += vy * 0.1
        self.current_position["z"] += vz * 0.1
        
        return {
            "success": True,
            "action": "set_velocity",
            "velocity": self.current_velocity.copy()
        }
    
    async def action_follow_path(self, waypoints: List[Dict[str, Any]], 
                                 loop: bool = False) -> Dict[str, Any]:
        """
        Следование по маршруту.
        
        Args:
            waypoints (List[Dict[str, Any]]): Список точек маршрута.
            loop (bool): Зациклить маршрут.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        if not self.is_flying:
            return {"success": False, "error": "Дрон не в полете"}
        
        # Конвертация точек
        self.current_path = [
            Waypoint(
                x=wp.get("x", 0),
                y=wp.get("y", 0),
                z=wp.get("z", 10),
                speed=wp.get("speed", self.default_speed),
                hover_time=wp.get("hover_time", 0),
                action=wp.get("action")
            )
            for wp in waypoints
        ]
        
        self.current_waypoint_index = 0
        
        logger.info(f"Начато следование по маршруту из {len(self.current_path)} точек")
        
        return {
            "success": True,
            "action": "follow_path",
            "waypoints_count": len(self.current_path)
        }
    
    async def action_get_position(self) -> Dict[str, Any]:
        """Получение текущей позиции"""
        return {
            "success": True,
            "position": self.current_position.copy(),
            "velocity": self.current_velocity.copy(),
            "attitude": self.current_attitude.copy(),
            "is_flying": self.is_flying
        }
    
    async def action_set_home_position(self, x: float, y: float, z: float = 0) -> Dict[str, Any]:
        """Установка домашней позиции"""
        self.home_position = {"x": x, "y": y, "z": z}
        
        return {
            "success": True,
            "home_position": self.home_position.copy()
        }
    
    async def action_calculate_distance(self, x: float, y: float, z: float) -> Dict[str, Any]:
        """Расчет расстояния до точки"""
        dx = x - self.current_position["x"]
        dy = y - self.current_position["y"]
        dz = z - self.current_position["z"]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        return {
            "success": True,
            "distance": distance,
            "from": self.current_position.copy(),
            "to": {"x": x, "y": y, "z": z}
        }
    
    async def shutdown(self):
        """Завершение работы инструмента"""
        if self.is_flying:
            logger.warning("Дрон в полете при выключении! Выполняю посадку...")
            await self.action_land()
        
        logger.info(f"Инструмент {self.name} завершает работу")
        self.status = ToolStatus.SHUTDOWN
