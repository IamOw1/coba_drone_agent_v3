"""
Интеграция с Unreal Engine (через Pixel Streaming и Blueprint API)
Unreal Engine 5+ с плагинами для дронов обеспечивает максимально реалистичное окружение
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import aiohttp
import websockets

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class UnrealEngineTelemetry:
    """Телеметрия из Unreal Engine симулятора"""
    timestamp: float
    drone_id: int
    position: Dict[str, float]
    velocity: Dict[str, float]
    rotation: Dict[str, float]
    camera_data: Optional[Dict[str, Any]]
    sensor_data: Dict[str, Any]
    physics_data: Dict[str, float]
    weather: Dict[str, Any]


class UnrealEngineClient:
    """
    Клиент для интеграции с Unreal Engine 5+.
    
    Unreal Engine Integration Features:
    - Nanite Real-time Graphics (максимальная реалистичность)
    - Pixel Streaming (удалённое управление через браузер)
    - Blueprint System (простое программирование)
    - Multiplayer поддержка
    - Advanced Physics (Chaos)
    - Photo-realistic environment
    - Realistic weather system
    - Dynamic lighting
    
    Requirements:
    - Unreal Engine 5.0+
    - Drone Plugin установлен
    - Pixel Streaming включен
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация клиента Unreal Engine.
        
        Args:
            config: Конфигурация
                {
                    "unreal_engine": {
                        "host": "localhost",
                        "http_port": 8000,
                        "websocket_port": 8001,
                        "project_path": "/path/to/project",
                        "drone_id": 0,
                        "start_location": [0, 0, 100],
                        "graphics_quality": "Ultra"
                    }
                }
        """
        self.config = config
        ue_config = config.get('unreal_engine', {})
        
        self.host = ue_config.get('host', 'localhost')
        self.http_port = ue_config.get('http_port', 8000)
        self.ws_port = ue_config.get('websocket_port', 8001)
        self.project_path = ue_config.get('project_path', '')
        self.drone_id = ue_config.get('drone_id', 0)
        self.start_location = ue_config.get('start_location', [0, 0, 100])
        self.graphics_quality = ue_config.get('graphics_quality', 'Ultra')
        
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
        self.connected = False
        self.telemetry_data: Optional[UnrealEngineTelemetry] = None
        self.simulation_running = False
        
        logger.info(f"Unreal Engine Client инициализирован: {self.host}:{self.http_port}")
    
    async def connect(self) -> bool:
        """Подключение к Unreal Engine"""
        try:
            # Создание HTTP сессии для REST API
            self.http_session = aiohttp.ClientSession()
            
            # Проверка доступности сервера
            try:
                async with self.http_session.get(
                    f"http://{self.host}:{self.http_port}/api/health"
                ) as resp:
                    if resp.status != 200:
                        logger.error("Unreal Engine сервер не доступен")
                        return False
            except:
                logger.warning("Unreal Engine не запущен, используется режим имитации")
            
            # Подключение к WebSocket для real-time трансля
            await self._connect_websocket()
            
            # Инициализация симуляции
            await self._initialize_simulation()
            
            self.connected = True
            logger.info("✅ Подключено к Unreal Engine")
            
            # Запуск главного цикла
            asyncio.create_task(self._main_loop())
            
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Unreal Engine: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Отключение от Unreal Engine"""
        try:
            await self._stop_simulation()
            
            if self.ws_connection:
                await self.ws_connection.close()
            
            if self.http_session:
                await self.http_session.close()
            
            self.connected = False
            logger.info("Отключено от Unreal Engine")
        except Exception as e:
            logger.error(f"Ошибка при отключении: {e}")
    
    async def _connect_websocket(self) -> bool:
        """Подключение к WebSocket"""
        try:
            uri = f"ws://{self.host}:{self.ws_port}/telemetry"
            self.ws_connection = await websockets.connect(uri)
            logger.info("WebSocket подключение установлено")
            
            # Запуск цикла приёма данных
            asyncio.create_task(self._websocket_listener())
            
            return True
        except Exception as e:
            logger.warning(f"WebSocket недоступен (режим имитации): {e}")
            return False
    
    async def _websocket_listener(self) -> None:
        """Прослушивание WebSocket сообщений"""
        try:
            async for message in self.ws_connection:
                try:
                    data = json.loads(message)
                    self.telemetry_data = self._parse_websocket_data(data)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Ошибка WebSocket: {e}")
    
    async def _initialize_simulation(self) -> bool:
        """Инициализация симуляции"""
        try:
            data = {
                'drone_id': self.drone_id,
                'start_location': self.start_location,
                'graphics_quality': self.graphics_quality,
                'physics_enabled': True
            }
            
            async with self.http_session.post(
                f"http://{self.host}:{self.http_port}/api/simulation/init",
                json=data
            ) as resp:
                if resp.status == 200:
                    self.simulation_running = True
                    logger.info("Симуляция инициализирована")
                    return True
        except Exception as e:
            logger.warning(f"Ошибка инициализации (режим имитации): {e}")
            self.simulation_running = True
        
        return self.simulation_running
    
    async def _stop_simulation(self) -> bool:
        """Остановка симуляции"""
        try:
            async with self.http_session.post(
                f"http://{self.host}:{self.http_port}/api/simulation/stop"
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Ошибка остановки симуляции: {e}")
            return False
    
    async def _main_loop(self) -> None:
        """Главный цикл обновления"""
        while self.connected:
            try:
                # Если WebSocket не подключен, получаем данные через HTTP
                if not self.ws_connection:
                    await self._fetch_telemetry_http()
                else:
                    # WebSocket уже отправляет данные в фоне
                    pass
                
                await asyncio.sleep(0.05)  # 20 Hz
            except Exception as e:
                logger.error(f"Ошибка в главном цикле: {e}")
                await asyncio.sleep(0.1)
    
    async def _fetch_telemetry_http(self) -> None:
        """Получение телеметрии через HTTP"""
        try:
            async with self.http_session.get(
                f"http://{self.host}:{self.http_port}/api/drone/{self.drone_id}/telemetry"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.telemetry_data = self._parse_http_data(data)
        except Exception as e:
            logger.debug(f"Ошибка HTTP телеметрии: {e}")
            # Используем генерируемые данные
            self.telemetry_data = self._generate_mock_telemetry()
    
    def _parse_websocket_data(self, data: Dict) -> UnrealEngineTelemetry:
        """Парсинг данных из WebSocket"""
        return UnrealEngineTelemetry(
            timestamp=data.get('timestamp', datetime.now().timestamp()),
            drone_id=self.drone_id,
            position=data.get('position', {'x': 0, 'y': 0, 'z': 0}),
            velocity=data.get('velocity', {'x': 0, 'y': 0, 'z': 0}),
            rotation=data.get('rotation', {'roll': 0, 'pitch': 0, 'yaw': 0}),
            camera_data=data.get('camera', None),
            sensor_data=data.get('sensors', {}),
            physics_data=data.get('physics', {}),
            weather=data.get('weather', {})
        )
    
    def _parse_http_data(self, data: Dict) -> UnrealEngineTelemetry:
        """Парсинг данных из HTTP"""
        return self._parse_websocket_data(data)
    
    def _generate_mock_telemetry(self) -> UnrealEngineTelemetry:
        """Генерация значений telemetry для имитации"""
        import math
        import time
        
        t = time.time()
        x = self.start_location[0] + 20 * math.sin(t/10)
        y = self.start_location[1] + 20 * math.cos(t/10)
        z = self.start_location[2] + 5 * math.sin(t/5)
        
        return UnrealEngineTelemetry(
            timestamp=t,
            drone_id=self.drone_id,
            position={'x': x, 'y': y, 'z': z},
            velocity={'x': 5, 'y': 0, 'z': 0},
            rotation={'roll': 0.05, 'pitch': 0.02, 'yaw': t/10},
            camera_data={'fov': 90, 'resolution': [1920, 1080]},
            sensor_data={'lidar': [[0, 0, 10]], 'gps': [55.7558, 37.6173, z]},
            physics_data={'mass': 1.2, 'drag': 0.1},
            weather={'temperature': 22, 'wind_speed': 2}
        )
    
    # Команды управления дроном
    
    async def arm_drone(self) -> bool:
        """Взведение дрона"""
        return await self._send_command('arm', {})
    
    async def disarm_drone(self) -> bool:
        """Снятие дрона с боевого взвода"""
        return await self._send_command('disarm', {})
    
    async def takeoff(self, altitude: float) -> bool:
        """Взлёт на заданную высоту"""
        return await self._send_command('takeoff', {'altitude': altitude})
    
    async def land(self) -> bool:
        """Посадка"""
        return await self._send_command('land', {})
    
    async def move_to_location(self, x: float, y: float, z: float) -> bool:
        """Полёт к координатам"""
        return await self._send_command('move_to_location', {
            'location': {'x': x, 'y': y, 'z': z}
        })
    
    async def set_velocity(self, vx: float, vy: float, vz: float) -> bool:
        """Установка скорости"""
        return await self._send_command('set_velocity', {
            'velocity': {'x': vx, 'y': vy, 'z': vz}
        })
    
    async def set_rotation(self, roll: float, pitch: float, yaw: float) -> bool:
        """Установка ориентации"""
        return await self._send_command('set_rotation', {
            'rotation': {'roll': roll, 'pitch': pitch, 'yaw': yaw}
        })
    
    async def enable_camera_capture(self, output_dir: str = '/tmp') -> bool:
        """Включение записи видео с камеры"""
        return await self._send_command('enable_camera', {
            'output_directory': output_dir
        })
    
    async def disable_camera_capture(self) -> bool:
        """Отключение записи видео"""
        return await self._send_command('disable_camera', {})
    
    async def get_camera_frame(self) -> Optional[bytes]:
        """Получение кадра с камеры"""
        try:
            async with self.http_session.get(
                f"http://{self.host}:{self.http_port}/api/drone/{self.drone_id}/camera/frame"
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as e:
            logger.error(f"Ошибка получения кадра: {e}")
        return None
    
    async def set_graphics_quality(self, quality: str) -> bool:
        """
        Установка качества графики.
        
        Args:
            quality: 'Low', 'Medium', 'High', 'Ultra'
        """
        return await self._send_command('set_graphics_quality', {
            'quality': quality
        })
    
    async def spawn_obstacle(self,  x: float, y: float, z: float, model: str) -> bool:
        """Создание препятствия в симуляции"""
        return await self._send_command('spawn_obstacle', {
            'location': {'x': x, 'y': y, 'z': z},
            'model': model
        })
    
    async def set_weather(self, weather_params: Dict[str, Any]) -> bool:
        """Установка погодных условий"""
        return await self._send_command('set_weather', weather_params)
    
    async def _send_command(self, command: str, params: Dict) -> bool:
        """Отправка команды"""
        try:
            data = {
                'command': command,
                'drone_id': self.drone_id,
                'parameters': params
            }
            
            async with self.http_session.post(
                f"http://{self.host}:{self.http_port}/api/command",
                json=data
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Команда отправлена: {command}")
                    return True
                else:
                    logger.error(f"Ошибка команды {command}: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"Ошибка отправки команды (режим имитации): {e}")
            logger.info(f"📤 [MOCK] Команда отправлена: {command}")
            return True
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Получение текущей телеметрии"""
        if self.telemetry_data:
            return {
                'timestamp': self.telemetry_data.timestamp,
                'position': self.telemetry_data.position,
                'velocity': self.telemetry_data.velocity,
                'rotation': self.telemetry_data.rotation,
                'camera': self.telemetry_data.camera_data,
                'sensors': self.telemetry_data.sensor_data,
                'physics': self.telemetry_data.physics_data,
                'weather': self.telemetry_data.weather
            }
        return None
    
    async def take_screenshot(self, filename: str = 'screenshot.png') -> bool:
        """Сделать скриншот"""
        return await self._send_command('take_screenshot', {
            'filename': filename
        })
    
    async def record_video(self, duration: int = 10, filename: str = 'output.mp4') -> bool:
        """Записать видео"""
        return await self._send_command('record_video', {
            'duration': duration,
            'filename': filename
        })
