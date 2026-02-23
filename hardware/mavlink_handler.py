"""
Обработчик MAVLink протокола для управления реальным дроном
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Попытка импорта MAVLink
try:
    from dronekit import connect, VehicleMode, LocationGlobalRelative
    from dronekit_sitl import SITL
    DRONEKIT_AVAILABLE = True
except ImportError:
    DRONEKIT_AVAILABLE = False
    logger.warning("DroneKit не установлен")


class FlightMode(Enum):
    """Режимы полета"""
    STABILIZE = "STABILIZE"
    ACRO = "ACRO"
    ALTHOLD = "ALTHOLD"
    AUTO = "AUTO"
    GUIDED = "GUIDED"
    LOITER = "LOITER"
    RTL = "RTL"
    CIRCLE = "CIRCLE"
    LAND = "LAND"


class MAVLinkHandler:
    """
    Обработчик MAVLink протокола для управления дроном через DroneKit.
    Предоставляет интерфейс для работы с реальным дроном.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация обработчика MAVLink.
        
        Args:
            config (Dict[str, Any]): Конфигурация подключения.
        """
        self.config = config
        
        # Параметры подключения
        mavlink_config = config.get('mavlink', {})
        self.connection_string = mavlink_config.get('connection_string', 'tcp:127.0.0.1:5760')
        self.baud_rate = mavlink_config.get('baud_rate', 921600)
        
        # DroneKit транспортное средство
        self.vehicle = None
        self.connected = False
        
        # Телеметрия
        self.telemetry = {
            "position": {"x": 0, "y": 0, "z": 0},
            "velocity": {"vx": 0, "vy": 0, "vz": 0},
            "attitude": {"roll": 0, "pitch": 0, "yaw": 0},
            "battery": 100.0,
            "gps": {"lat": 0, "lon": 0, "alt": 0},
            "mode": "UNKNOWN",
            "armed": False,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"MAVLinkHandler инициализирован ({self.connection_string})")
    
    async def connect(self) -> bool:
        """
        Подключение к дрону через MAVLink.
        
        Returns:
            bool: True если подключение успешно.
        """
        if not DRONEKIT_AVAILABLE:
            logger.error("DroneKit не установлен. Используйте: pip install dronekit dronekit-sitl")
            return False
        
        try:
            # Подключение к дрону
            self.vehicle = connect(self.connection_string, baud=self.baud_rate, wait_ready=True)
            
            # Проверка подключения
            if self.vehicle is None:
                logger.error("Не удалось подключиться к дрону")
                return False
            
            self.connected = True
            logger.info(f"Подключение к дрону установлено")
            logger.info(f"Версия ПО: {self.vehicle.version}")
            logger.info(f"Режим полета: {self.vehicle.mode.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к дрону: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от дрона"""
        if self.vehicle:
            try:
                self.vehicle.close()
            except Exception as e:
                logger.error(f"Ошибка отключения от дрона: {e}")
        
        self.connected = False
        logger.info("Отключение от дрона выполнено")
    
    async def is_connected(self) -> bool:
        """
        Проверка подключения.
        
        Returns:
            bool: True если подключено.
        """
        if self.vehicle is None:
            return False
        return self.connected
    
    async def get_telemetry(self) -> Dict[str, Any]:
        """
        Получение телеметрии от дрона.
        
        Returns:
            Dict[str, Any]: Данные телеметрии.
        """
        if not self.vehicle:
            return self.telemetry
        
        try:
            # Позиция
            location = self.vehicle.location.global_frame
            
            # Скорость
            velocity = self.vehicle.velocity
            
            # Ориентация
            attitude = self.vehicle.attitude
            
            # Батарея
            battery = self.vehicle.battery
            
            self.telemetry = {
                "position": {
                    "x": location.lat,
                    "y": location.lon,
                    "z": location.alt
                },
                "velocity": {
                    "vx": velocity[0] if velocity else 0,
                    "vy": velocity[1] if velocity else 0,
                    "vz": velocity[2] if velocity else 0
                },
                "attitude": {
                    "roll": attitude.roll if attitude else 0,
                    "pitch": attitude.pitch if attitude else 0,
                    "yaw": attitude.yaw if attitude else 0
                },
                "battery": {
                    "voltage": battery.voltage if battery else 0,
                    "current": battery.current if battery else 0,
                    "level": battery.level if battery else 0
                },
                "gps": {
                    "lat": location.lat,
                    "lon": location.lon,
                    "alt": location.alt
                },
                "mode": self.vehicle.mode.name,
                "armed": self.vehicle.armed,
                "timestamp": datetime.now().isoformat()
            }
            
            return self.telemetry
            
        except Exception as e:
            logger.error(f"Ошибка получения телеметрии: {e}")
            return self.telemetry
    
    async def arm_and_takeoff(self, target_altitude: float) -> bool:
        """
        Вооружение дрона и взлет на указанную высоту.
        
        Args:
            target_altitude (float): Целевая высота в метрах.
            
        Returns:
            bool: True если успешно.
        """
        if not self.vehicle:
            logger.error("Дрон не подключен")
            return False
        
        try:
            # Ожидание инициализации домашней позиции
            while not self.vehicle.home_location:
                logger.info("Ожидание установления домашней позиции...")
                await asyncio.sleep(1)
            
            logger.info(f"Домашняя позиция установлена: {self.vehicle.home_location}")
            
            # Установка режима полета
            self.vehicle.mode = VehicleMode("GUIDED")
            
            # Вооружение
            logger.info("Вооружение дрона...")
            self.vehicle.armed = True
            
            # Ожидание вооружения
            while not self.vehicle.armed:
                logger.info("Ожидание вооружения...")
                await asyncio.sleep(1)
            
            logger.info("Дрон вооружен")
            
            # Взлет
            logger.info(f"Взлет на высоту {target_altitude} м")
            self.vehicle.simple_takeoff(target_altitude)
            
            # Мониторинг взлета
            while True:
                await asyncio.sleep(1)
                
                altitude = self.vehicle.location.global_frame.alt
                logger.info(f"Текущая высота: {altitude:.1f} м")
                
                if altitude >= target_altitude * 0.95:
                    logger.info("Достигнута целевая высота")
                    break
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка взлета: {e}")
            return False
    
    async def send_command(self, command: str, **params) -> Dict[str, Any]:
        """
        Отправка команды дрону.
        
        Args:
            command (str): Команда.
            **params: Параметры команды.
            
        Returns:
            Dict[str, Any]: Результат выполнения.
        """
        if not self.vehicle:
            return {"success": False, "error": "Дрон не подключен"}
        
        try:
            if command == "TAKEOFF":
                altitude = params.get("altitude", 10)
                success = await self.arm_and_takeoff(altitude)
                return {"success": success, "command": command}
            
            elif command == "LAND":
                self.vehicle.mode = VehicleMode("LAND")
                return {"success": True, "command": command}
            
            elif command == "RTL":
                self.vehicle.mode = VehicleMode("RTL")
                return {"success": True, "command": command}
            
            elif command == "GOTO":
                x = params.get("x", 0)  # широта
                y = params.get("y", 0)  # долгота
                z = params.get("z", 10) # высота
                
                location = LocationGlobalRelative(x, y, z)
                self.vehicle.simple_goto(location)
                return {"success": True, "command": command}
            
            elif command == "HOVER":
                self.vehicle.mode = VehicleMode("LOITER")
                return {"success": True, "command": command}
            
            elif command == "set_velocity":
                # Для установки скорости требуется более сложная команда
                logger.warning("Команда set_velocity требует более сложной реализации")
                return {"success": False, "error": "Не поддерживается в текущей версии"}
            
            else:
                return {"success": False, "error": f"Неизвестная команда: {command}"}
            
        except Exception as e:
            logger.error(f"Ошибка выполнения команды {command}: {e}")
            return {"success": False, "error": str(e)}
    
    async def emergency_stop(self):
        """Аварийная остановка"""
        if self.vehicle:
            try:
                # Отключение управления
                self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
            except Exception as e:
                logger.error(f"Ошибка аварийной остановки: {e}")
        
        logger.warning("Аварийная остановка выполнена")
    
    async def set_flight_mode(self, mode: str) -> Dict[str, Any]:
        """
        Установка режима полета.
        
        Args:
            mode (str): Режим полета.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        if not self.vehicle:
            return {"success": False, "error": "Дрон не подключен"}
        
        try:
            mode_upper = mode.upper()
            
            # Проверка валидности режима
            valid_modes = [m.name for m in FlightMode]
            
            if mode_upper in valid_modes:
                self.vehicle.mode = VehicleMode(mode_upper)
                return {"success": True, "mode": mode_upper}
            else:
                return {"success": False, "error": f"Недопустимый режим: {mode}"}
            
        except Exception as e:
            logger.error(f"Ошибка установки режима полета: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_battery_status(self) -> Dict[str, Any]:
        """Получение статуса батареи"""
        if not self.vehicle:
            return {"success": False}
        
        try:
            battery = self.vehicle.battery
            return {
                "success": True,
                "voltage": battery.voltage,
                "current": battery.current,
                "level": battery.level,
                "remaining": battery.remaining_time
            }
        except Exception as e:
            logger.error(f"Ошибка получения статуса батареи: {e}")
            return {"success": False, "error": str(e)}
