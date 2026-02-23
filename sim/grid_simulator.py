"""
Интеграция с симулятором Grid
Российский высокопроизводительный симулятор беспилотных летательных аппаратов
"""
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import socket
import struct

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Попытка импорта Grid SDK
try:
    import grid_sdk
    GRID_AVAILABLE = True
except ImportError:
    GRID_AVAILABLE = False
    logger.warning("Grid SDK не установлен. Используется режим симуляции.")


@dataclass
class GridTelemetry:
    """Телеметрия от Grid симулятора"""
    timestamp: float
    position: Dict[str, float]  # x, y, z
    velocity: Dict[str, float]  # vx, vy, vz
    attitude: Dict[str, float]  # roll, pitch, yaw
    battery_voltage: float
    battery_current: float
    gps: Optional[Dict[str, float]] = None  # lat, lon, alt
    temperature: float = 0.0
    gps_signal: int = 0


class GridSimulatorClient:
    """
    Клиент для интеграции с симулятором Grid.
    Позволяет управлять дроном в Grid и получать данные телеметрии.
    
    Grid Simulator:
    - Поддержка системы MAVLink
    - Высокая точность физического моделирования
    - Поддержка множественных дронов
    - Реалистичные модели датчиков
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация клиента Grid.
        
        Args:
            config: Конфигурация подключения к Grid
                {
                    "grid": {
                        "host": "localhost",
                        "port": 4446,
                        "vehicle_name": "Drone1",
                        "mavlink_port": 14550,
                        "protocol": "mavlink"
                    }
                }
        """
        self.config = config
        grid_config = config.get('grid', {})
        
        self.host = grid_config.get('host', 'localhost')
        self.port = grid_config.get('port', 4446)
        self.vehicle_name = grid_config.get('vehicle_name', 'Drone1')
        self.mavlink_port = grid_config.get('mavlink_port', 14550)
        self.protocol = grid_config.get('protocol', 'mavlink')
        
        self.client = None
        self.connected = False
        self.telemetry_data: Optional[GridTelemetry] = None
        
        logger.info(f"Grid Simulator Client инициализирован: {self.host}:{self.port}")
    
    async def connect(self) -> bool:
        """
        Подключение к Grid симулятору.
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            if GRID_AVAILABLE:
                # Использование Grid SDK
                self.client = grid_sdk.SimulatorClient(
                    host=self.host,
                    port=self.port,
                    protocol=self.protocol
                )
                self.connected = await self.client.connect()
            else:
                # Режим симуляции - создаём mock подключение
                self.connected = await self._mock_connect()
            
            if self.connected:
                logger.info("✅ Подключено к Grid Simulator")
                await self._start_telemetry_stream()
            else:
                logger.error("❌ Не удалось подключиться к Grid Simulator")
            
            return self.connected
        except Exception as e:
            logger.error(f"Ошибка подключения к Grid: {e}")
            return False
    
    async def _mock_connect(self) -> bool:
        """Имитация подключения для тестирования"""
        await asyncio.sleep(0.5)
        return True
    
    async def disconnect(self) -> None:
        """Отключение от Grid симулятора"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            logger.info("Отключено от Grid Simulator")
    
    async def _start_telemetry_stream(self) -> None:
        """Запуск потока телеметрии"""
        asyncio.create_task(self._telemetry_loop())
    
    async def _telemetry_loop(self) -> None:
        """Главный цикл получения телеметрии"""
        while self.connected:
            try:
                if GRID_AVAILABLE and self.client:
                    # Получение настоящей телеметрии
                    state = await self.client.get_state()
                    self.telemetry_data = self._parse_telemetry(state)
                else:
                    # Генерация тестовой телеметрии
                    self.telemetry_data = self._generate_mock_telemetry()
                
                await asyncio.sleep(0.05)  # 20 Hz
            except Exception as e:
                logger.error(f"Ошибка получения телеметрии из Grid: {e}")
                await asyncio.sleep(0.1)
    
    def _parse_telemetry(self, state: Any) -> GridTelemetry:
        """Парсинг телеметрии из Grid"""
        return GridTelemetry(
            timestamp=datetime.now().timestamp(),
            position={
                'x': float(getattr(state, 'position_x', 0)),
                'y': float(getattr(state, 'position_y', 0)),
                'z': float(getattr(state, 'position_z', 0))
            },
            velocity={
                'vx': float(getattr(state, 'velocity_x', 0)),
                'vy': float(getattr(state, 'velocity_y', 0)),
                'vz': float(getattr(state, 'velocity_z', 0))
            },
            attitude={
                'roll': float(getattr(state, 'roll', 0)),
                'pitch': float(getattr(state, 'pitch', 0)),
                'yaw': float(getattr(state, 'yaw', 0))
            },
            battery_voltage=float(getattr(state, 'battery_voltage', 12.0)),
            battery_current=float(getattr(state, 'battery_current', 0)),
            gps={'lat': 0, 'lon': 0, 'alt': 0} if hasattr(state, 'gps_lat') else None,
            temperature=float(getattr(state, 'temperature', 25.0)),
            gps_signal=int(getattr(state, 'gps_signal', 0))
        )
    
    def _generate_mock_telemetry(self) -> GridTelemetry:
        """Генерация тестовой телеметрии"""
        import math
        import time
        
        t = time.time()
        return GridTelemetry(
            timestamp=t,
            position={
                'x': 10 * math.sin(t),
                'y': 0,
                'z': 5 + 2 * math.sin(t/2)
            },
            velocity={'vx': 10, 'vy': 0, 'vz': 1},
            attitude={'roll': 0.1, 'pitch': 0.05, 'yaw': t/10},
            battery_voltage=12.6,
            battery_current=5.2,
            gps={'lat': 55.7558, 'lon': 37.6173, 'alt': 100},
            temperature=25.0,
            gps_signal=100
        )
    
    async def arm_drone(self) -> bool:
        """Взведение дрона"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.arm(self.vehicle_name)
            else:
                logger.info("🔒 [MOCK] Дрон взведён")
                return True
        except Exception as e:
            logger.error(f"Ошибка взведения дрона: {e}")
            return False
    
    async def disarm_drone(self) -> bool:
        """Снятие дрона с боевого взвода"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.disarm(self.vehicle_name)
            else:
                logger.info("🔓 [MOCK] Дрон снят с боевого взвода")
                return True
        except Exception as e:
            logger.error(f"Ошибка снятия дрона с боевого взвода: {e}")
            return False
    
    async def takeoff(self, altitude: float) -> bool:
        """Взлёт на заданную высоту"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.takeoff(self.vehicle_name, altitude)
            else:
                logger.info(f"✈️ [MOCK] Взлёт на высоту {altitude} м")
                await asyncio.sleep(1)
                return True
        except Exception as e:
            logger.error(f"Ошибка взлёта: {e}")
            return False
    
    async def land(self) -> bool:
        """Посадка дрона"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.land(self.vehicle_name)
            else:
                logger.info("🛬 [MOCK] Посадка инициирована")
                await asyncio.sleep(1)
                return True
        except Exception as e:
            logger.error(f"Ошибка посадки: {e}")
            return False
    
    async def move_to(self, x: float, y: float, z: float, speed: float = 10.0) -> bool:
        """
        Полёт к координатам.
        
        Args:
            x, y, z: Координаты в метрах (локальные или GPS)
            speed: Скорость в м/с
        """
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.move_to(
                    self.vehicle_name, x, y, z, speed
                )
            else:
                logger.info(f"🎯 [MOCK] Полёт к ({x}, {y}, {z}) со скоростью {speed} м/с")
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.error(f"Ошибка навигации: {e}")
            return False
    
    async def set_velocity(self, vx: float, vy: float, vz: float) -> bool:
        """Установка вектора скорости"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.set_velocity(
                    self.vehicle_name, vx, vy, vz
                )
            else:
                logger.info(f"⚡ [MOCK] Скорость установлена на ({vx}, {vy}, {vz})")
                return True
        except Exception as e:
            logger.error(f"Ошибка установки скорости: {e}")
            return False
    
    async def set_yaw(self, yaw: float) -> bool:
        """Установка yaw (курса)"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.set_yaw(self.vehicle_name, yaw)
            else:
                logger.info(f"🧭 [MOCK] Курс установлен на {yaw}°")
                return True
        except Exception as e:
            logger.error(f"Ошибка установки курса: {e}")
            return False
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Получение текущей телеметрии"""
        if self.telemetry_data:
            return {
                'timestamp': self.telemetry_data.timestamp,
                'position': self.telemetry_data.position,
                'velocity': self.telemetry_data.velocity,
                'attitude': self.telemetry_data.attitude,
                'battery': {
                    'voltage': self.telemetry_data.battery_voltage,
                    'current': self.telemetry_data.battery_current,
                    'remaining_percent': 95
                },
                'gps': self.telemetry_data.gps,
                'system': {
                    'temperature': self.telemetry_data.temperature,
                    'gps_signal': self.telemetry_data.gps_signal
                }
            }
        return None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Получение статуса системы"""
        return {
            'is_armed': True,
            'is_flying': True,
            'battery_percent': 95,
            'gps_status': 'OK',
            'sensor_status': 'OK',
            'wind_speed': 0.5,
            'wind_direction': 45,
            'simulation_running': True
        }
    
    async def reset_simulation(self) -> bool:
        """Перезагрузка симуляции"""
        try:
            if GRID_AVAILABLE and self.client:
                return await self.client.reset()
            else:
                logger.info("🔄 [MOCK] Симуляция перезагружена")
                return True
        except Exception as e:
            logger.error(f"Ошибка перезагрузки симуляции: {e}")
            return False
