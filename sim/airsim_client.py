"""
Клиент для интеграции с симулятором AirSim
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Попытка импорта AirSim
try:
    import airsim
    AIRSIM_AVAILABLE = True
except ImportError:
    AIRSIM_AVAILABLE = False
    logger.warning("AirSim не установлен. Используется режим симуляции.")


class AirSimClient:
    """
    Клиент для взаимодействия с симулятором AirSim.
    Предоставляет интерфейс для получения телеметрии и отправки команд.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация клиента AirSim.
        
        Args:
            config (Dict[str, Any]): Конфигурация подключения.
        """
        self.config = config
        
        # Параметры подключения
        airsim_config = config.get('airsim', {})
        self.host = airsim_config.get('host', 'localhost')
        self.port = airsim_config.get('port', 41451)
        self.vehicle_name = airsim_config.get('vehicle_name', 'Drone1')
        
        # Клиент AirSim
        self.client = None
        self.connected = False
        
        # Текущее состояние
        self.telemetry = {
            "position": {"x": 0, "y": 0, "z": 0},
            "velocity": {"vx": 0, "vy": 0, "vz": 0},
            "attitude": {"roll": 0, "pitch": 0, "yaw": 0},
            "battery": 100.0,
            "gps": {"lat": 0, "lon": 0, "alt": 0},
            "timestamp": datetime.now().isoformat()
        }
        
        # Режим симуляции (если AirSim недоступен)
        self.simulation_mode = not AIRSIM_AVAILABLE
        
        logger.info(f"AirSimClient инициализирован ({self.host}:{self.port})")
    
    async def connect(self) -> bool:
        """
        Подключение к симулятору AirSim.
        
        Returns:
            bool: True если подключение успешно.
        """
        if self.simulation_mode:
            logger.info("Режим симуляции (AirSim недоступен)")
            self.connected = True
            return True
        
        try:
            self.client = airsim.MultirotorClient(ip=self.host, port=self.port)
            self.client.confirmConnection()
            self.client.enableApiControl(True, self.vehicle_name)
            self.client.armDisarm(True, self.vehicle_name)
            
            self.connected = True
            logger.info("Подключение к AirSim установлено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к AirSim: {e}")
            logger.info("Переключение в режим симуляции")
            self.simulation_mode = True
            self.connected = True
            return True
    
    async def disconnect(self):
        """Отключение от симулятора"""
        if self.client and not self.simulation_mode:
            try:
                self.client.armDisarm(False, self.vehicle_name)
                self.client.enableApiControl(False, self.vehicle_name)
            except Exception as e:
                logger.error(f"Ошибка отключения от AirSim: {e}")
        
        self.connected = False
        logger.info("Отключение от AirSim выполнено")
    
    async def is_connected(self) -> bool:
        """
        Проверка подключения.
        
        Returns:
            bool: True если подключено.
        """
        return self.connected
    
    async def get_telemetry(self) -> Dict[str, Any]:
        """
        Получение телеметрии от дрона.
        
        Returns:
            Dict[str, Any]: Данные телеметрии.
        """
        if self.simulation_mode:
            # Симуляция телеметрии
            return self._simulate_telemetry()
        
        try:
            # Получение данных от AirSim
            state = self.client.getMultirotorState(vehicle_name=self.vehicle_name)
            
            # Позиция
            position = state.kinematics_estimated.position
            
            # Скорость
            velocity = state.kinematics_estimated.linear_velocity
            
            # Ориентация
            orientation = state.kinematics_estimated.orientation
            
            self.telemetry = {
                "position": {
                    "x": position.x_val,
                    "y": position.y_val,
                    "z": -position.z_val  # AirSim использует NED координаты
                },
                "velocity": {
                    "vx": velocity.x_val,
                    "vy": velocity.y_val,
                    "vz": -velocity.z_val
                },
                "attitude": {
                    "roll": orientation.x_val,
                    "pitch": orientation.y_val,
                    "yaw": orientation.z_val
                },
                "battery": 100.0,  # AirSim не предоставляет данные о батарее
                "gps": {
                    "lat": state.gps_location.latitude,
                    "lon": state.gps_location.longitude,
                    "alt": state.gps_location.altitude
                },
                "timestamp": datetime.now().isoformat(),
                "collision": state.collision.has_collided
            }
            
            return self.telemetry
            
        except Exception as e:
            logger.error(f"Ошибка получения телеметрии: {e}")
            return self._simulate_telemetry()
    
    def _simulate_telemetry(self) -> Dict[str, Any]:
        """Симуляция телеметрии"""
        import random
        
        # Небольшие изменения для реалистичности
        self.telemetry["position"]["x"] += random.uniform(-0.1, 0.1)
        self.telemetry["position"]["y"] += random.uniform(-0.1, 0.1)
        
        # Постепенное снижение батареи
        self.telemetry["battery"] = max(0, self.telemetry["battery"] - 0.01)
        
        self.telemetry["timestamp"] = datetime.now().isoformat()
        
        return self.telemetry
    
    async def send_command(self, command: str, **params) -> Dict[str, Any]:
        """
        Отправка команды дрону.
        
        Args:
            command (str): Команда.
            **params: Параметры команды.
            
        Returns:
            Dict[str, Any]: Результат выполнения.
        """
        if self.simulation_mode:
            return self._simulate_command(command, **params)
        
        try:
            if command == "TAKEOFF":
                altitude = params.get("altitude", 10)
                self.client.takeoffAsync(vehicle_name=self.vehicle_name).join()
                return {"success": True, "command": command, "altitude": altitude}
            
            elif command == "LAND":
                self.client.landAsync(vehicle_name=self.vehicle_name).join()
                return {"success": True, "command": command}
            
            elif command == "GOTO":
                x = params.get("x", 0)
                y = params.get("y", 0)
                z = -params.get("z", 10)  # AirSim использует NED
                speed = params.get("speed", 5)
                
                self.client.moveToPositionAsync(
                    x, y, z, speed, 
                    vehicle_name=self.vehicle_name
                ).join()
                
                return {"success": True, "command": command, "position": {"x": x, "y": y, "z": -z}}
            
            elif command == "HOVER":
                self.client.hoverAsync(vehicle_name=self.vehicle_name).join()
                return {"success": True, "command": command}
            
            elif command == "RTL":
                self.client.goHomeAsync(vehicle_name=self.vehicle_name).join()
                return {"success": True, "command": command}
            
            elif command == "set_velocity":
                vx = params.get("vx", 0)
                vy = params.get("vy", 0)
                vz = -params.get("vz", 0)  # AirSim использует NED
                duration = params.get("duration", 1)
                
                self.client.moveByVelocityAsync(
                    vx, vy, vz, duration,
                    vehicle_name=self.vehicle_name
                ).join()
                
                return {"success": True, "command": command, "velocity": {"vx": vx, "vy": vy, "vz": -vz}}
            
            else:
                return {"success": False, "error": f"Неизвестная команда: {command}"}
            
        except Exception as e:
            logger.error(f"Ошибка выполнения команды {command}: {e}")
            return {"success": False, "error": str(e)}
    
    def _simulate_command(self, command: str, **params) -> Dict[str, Any]:
        """Симуляция выполнения команды"""
        if command == "TAKEOFF":
            altitude = params.get("altitude", 10)
            self.telemetry["position"]["z"] = altitude
            return {"success": True, "command": command, "simulated": True}
        
        elif command == "LAND":
            self.telemetry["position"]["z"] = 0
            return {"success": True, "command": command, "simulated": True}
        
        elif command == "GOTO":
            self.telemetry["position"]["x"] = params.get("x", 0)
            self.telemetry["position"]["y"] = params.get("y", 0)
            self.telemetry["position"]["z"] = params.get("z", 10)
            return {"success": True, "command": command, "simulated": True}
        
        elif command == "HOVER":
            return {"success": True, "command": command, "simulated": True}
        
        elif command == "RTL":
            self.telemetry["position"]["x"] = 0
            self.telemetry["position"]["y"] = 0
            return {"success": True, "command": command, "simulated": True}
        
        return {"success": False, "error": f"Неизвестная команда: {command}"}
    
    async def take_photo(self) -> Dict[str, Any]:
        """
        Сделать фото с камеры.
        
        Returns:
            Dict[str, Any]: Результат.
        """
        if self.simulation_mode:
            return {"success": True, "simulated": True, "image": None}
        
        try:
            responses = self.client.simGetImages([
                airsim.ImageRequest("0", airsim.ImageType.Scene)
            ], vehicle_name=self.vehicle_name)
            
            return {"success": True, "images": len(responses)}
            
        except Exception as e:
            logger.error(f"Ошибка получения изображения: {e}")
            return {"success": False, "error": str(e)}
    
    async def emergency_stop(self):
        """Аварийная остановка"""
        if not self.simulation_mode and self.client:
            try:
                self.client.reset()
            except Exception as e:
                logger.error(f"Ошибка аварийной остановки: {e}")
        
        logger.warning("Аварийная остановка выполнена")
    
    async def set_weather(self, weather: str) -> Dict[str, Any]:
        """
        Установка погодных условий.
        
        Args:
            weather (str): Тип погоды (clear, rain, snow, fog).
            
        Returns:
            Dict[str, Any]: Результат.
        """
        if self.simulation_mode:
            return {"success": True, "simulated": True, "weather": weather}
        
        try:
            weather_map = {
                "clear": airsim.WeatherParameter.Clear,
                "rain": airsim.WeatherParameter.Rain,
                "snow": airsim.WeatherParameter.Snow,
                "fog": airsim.WeatherParameter.Fog
            }
            
            if weather in weather_map:
                self.client.simSetWeatherParameter(weather_map[weather], 1.0)
                return {"success": True, "weather": weather}
            else:
                return {"success": False, "error": f"Неизвестная погода: {weather}"}
            
        except Exception as e:
            logger.error(f"Ошибка установки погоды: {e}")
            return {"success": False, "error": str(e)}
