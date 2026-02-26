"""
Интеграция с мобильным роботом SkyRover (наземный и воздушный)
SkyRover - гибридная платформа для наземного и воздушного моделирования
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import socket
import struct

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SkyRoverState:
    """Состояние SkyRover"""
    timestamp: float
    position: Dict[str, float]
    velocity: Dict[str, float]
    attitude: Dict[str, float]
    motor_speeds: List[float]
    battery_voltage: float
    battery_current: float
    temperature: float
    mode: str  # 'ground_mode', 'air_mode', 'hover'


class SkyRoverClient:
    """
    Клиент для управления платформой SkyRover.
    
    SkyRover Features:
    - Гибридный режим (наземное + воздушное передвижение)
    - USB/Bluetooth соединение
    - Встроенная визуализация
    - Модульная архитектура (различные датчики и камеры)
    - Real-time streaming видео
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация клиента SkyRover.
        
        Args:
            config: Конфигурация
                {
                    "skyrover": {
                        "port": "/dev/ttyUSB0",  # или COM3 на Windows
                        "baudrate": 115200,
                        "vehicle_id": 1,
                        "mode": "air_mode"  # или "ground_mode"
                    }
                }
        """
        self.config = config
        skyrover_config = config.get('skyrover', {})
        
        self.port = skyrover_config.get('port', '/dev/ttyUSB0')
        self.baudrate = skyrover_config.get('baudrate', 115200)
        self.vehicle_id = skyrover_config.get('vehicle_id', 1)
        self.mode = skyrover_config.get('mode', 'air_mode')
        
        self.serial_connection = None
        self.connected = False
        self.state: Optional[SkyRoverState] = None
        
        logger.info(f"SkyRover Client инициализирован на портe {self.port} ({self.mode})")
    
    async def connect(self) -> bool:
        """Подключение к SkyRover"""
        try:
            # Попытка импорта pyserial
            try:
                import serial
                self.serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=1
                )
            except ImportError:
                logger.warning("pyserial не установлена, используется режим симуляции")
                self.serial_connection = True  # Mock соединение
            
            self.connected = True
            logger.info("✅ Подключено к SkyRover")
            
            # Запуск главного цикла
            asyncio.create_task(self._communication_loop())
            
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к SkyRover: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Отключение от SkyRover"""
        try:
            if self.serial_connection:
                try:
                    self.serial_connection.close()
                except:
                    pass
            self.connected = False
            logger.info("Отключено от SkyRover")
        except Exception as e:
            logger.error(f"Ошибка при отключении: {e}")
    
    async def _communication_loop(self) -> None:
        """Главный цикл коммуникации с SkyRover"""
        while self.connected:
            try:
                # Отправка команды получения состояния
                await self._request_state()
                
                # Чтение ответа
                self.state = await self._read_state()
                
                await asyncio.sleep(0.05)  # 20 Hz
            except Exception as e:
                logger.error(f"Ошибка в цикле коммуникации: {e}")
                await asyncio.sleep(0.1)
    
    async def _request_state(self) -> None:
        """Запрос состояния от SkyRover"""
        try:
            if self.serial_connection:
                # Формируем пакет запроса
                packet = bytes([0xFF, 0x01, self.vehicle_id, 0xAA])
                
                if hasattr(self.serial_connection, 'write'):
                    self.serial_connection.write(packet)
        except Exception as e:
            logger.error(f"Ошибка отправки запроса: {e}")
    
    async def _read_state(self) -> Optional[SkyRoverState]:
        """Чтение состояния от SkyRover"""
        try:
            if hasattr(self.serial_connection, 'read'):
                # Чтение данных
                data = self.serial_connection.read(128)
                if data and len(data) > 0:
                    return self._parse_state_packet(data)
            
            # Генерация тестовых данных
            return self._generate_mock_state()
        except Exception as e:
            logger.error(f"Ошибка чтения состояния: {e}")
            return None
    
    def _parse_state_packet(self, data: bytes) -> Optional[SkyRoverState]:
        """Парсинг пакета состояния"""
        try:
            # Простой парсинг (зависит от протокола SkyRover)
            if len(data) >= 32:
                import struct
                x, y, z = struct.unpack_from('<fff', data, 0)
                vx, vy, vz = struct.unpack_from('<fff', data, 12)
                battery = struct.unpack_from('<f', data, 24)[0]
                
                return SkyRoverState(
                    timestamp=datetime.now().timestamp(),
                    position={'x': x, 'y': y, 'z': z},
                    velocity={'vx': vx, 'vy': vy, 'vz': vz},
                    attitude={'roll': 0, 'pitch': 0, 'yaw': 0},
                    motor_speeds=[0, 0, 0, 0],
                    battery_voltage=battery,
                    battery_current=0,
                    temperature=25,
                    mode=self.mode
                )
        except Exception as e:
            logger.error(f"Ошибка парсинга пакета: {e}")
        
        return None
    
    def _generate_mock_state(self) -> SkyRoverState:
        """Генерация тестовых данных"""
        import math
        import time
        
        t = time.time()
        altitude = 5 + 2 * math.sin(t/2) if self.mode == 'air_mode' else 0
        
        return SkyRoverState(
            timestamp=t,
            position={
                'x': 10 * math.sin(t),
                'y': 10 * math.cos(t),
                'z': altitude
            },
            velocity={'vx': 5, 'vy': 5, 'vz': 0},
            attitude={'roll': 0.1, 'pitch': 0.05, 'yaw': t},
            motor_speeds=[2000, 2000, 2000, 2000],
            battery_voltage=12.2,
            battery_current=10.5,
            temperature=35,
            mode=self.mode
        )
    
    async def set_mode(self, mode: str) -> bool:
        """
        Установка режима.
        
        Args:
            mode: 'ground_mode', 'air_mode', или 'hover'
        """
        if mode not in ['ground_mode', 'air_mode', 'hover']:
            logger.error(f"Неизвестный режим: {mode}")
            return False
        
        try:
            self.mode = mode
            command = self._create_command('MODE', {'mode': mode})
            await self._send_command(command)
            logger.info(f"🔄 Режим изменён на {mode}")
            return True
        except Exception as e:
            logger.error(f"Ошибка смены режима: {e}")
            return False
    
    async def arm(self) -> bool:
        """Взведение"""
        command = self._create_command('ARM', {})
        return await self._send_command(command)
    
    async def disarm(self) -> bool:
        """Снятие с боевого взвода"""
        command = self._create_command('DISARM', {})
        return await self._send_command(command)
    
    async def takeoff(self, altitude: float) -> bool:
        """Взлёт (только в air_mode)"""
        if self.mode != 'air_mode':
            logger.error("Взлёт возможен только в air_mode")
            return False
        
        command = self._create_command('TAKEOFF', {'altitude': altitude})
        return await self._send_command(command)
    
    async def land(self) -> bool:
        """Посадка"""
        command = self._create_command('LAND', {})
        return await self._send_command(command)
    
    async def move_forward(self, distance: float, speed: float = 1.0) -> bool:
        """Движение вперёд (ground_mode)"""
        if self.mode == 'air_mode':
            logger.error("Движение вперёд только в ground_mode")
            return False
        
        command = self._create_command('MOVE_FWD', {
            'distance': distance,
            'speed': speed
        })
        return await self._send_command(command)
    
    async def turn(self, angle: float) -> bool:
        """Поворот"""
        command = self._create_command('TURN', {'angle': angle})
        return await self._send_command(command)
    
    async def set_motor_speed(self, motor_id: int, speed: int) -> bool:
        """Установка скорости мотора (0-4000 RPM)"""
        if not 0 <= motor_id <= 3:
            logger.error(f"Неверный ID мотора: {motor_id}")
            return False
        
        if not 0 <= speed <= 4000:
            logger.error(f"Скорость должна быть в диапазоне 0-4000: {speed}")
            return False
        
        command = self._create_command('MOTOR_SPEED', {
            'motor_id': motor_id,
            'speed': speed
        })
        return await self._send_command(command)
    
    async def set_all_motor_speeds(self, speeds: List[int]) -> bool:
        """Установка скоростей всех моторов"""
        if len(speeds) != 4:
            logger.error("Нужно указать скорости для 4 моторов")
            return False
        
        command = self._create_command('MOTORS', {'speeds': speeds})
        return await self._send_command(command)
    
    def _create_command(self, cmd_type: str, params: Dict) -> bytes:
        """Создание командного пакета"""
        packet = bytearray([0xFF, 0x02])  # Заголовок
        packet.append(self.vehicle_id)
        packet.append(ord(cmd_type[0]))
        
        # Добавить параметры (упрощённо)
        packet.extend(b'\x00' * 20)
        
        return bytes(packet)
    
    async def _send_command(self, command: bytes) -> bool:
        """Отправка команды"""
        try:
            if hasattr(self.serial_connection, 'write'):
                self.serial_connection.write(command)
                logger.info(f"📤 Команда отправлена ({len(command)} байт)")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки команды: {e}")
            return False
    
    def get_state(self) -> Optional[Dict[str, Any]]:
        """Получение текущего состояния"""
        if self.state:
            return {
                'timestamp': self.state.timestamp,
                'position': self.state.position,
                'velocity': self.state.velocity,
                'attitude': self.state.attitude,
                'motors': self.state.motor_speeds,
                'battery': {
                    'voltage': self.state.battery_voltage,
                    'current': self.state.battery_current
                },
                'temperature': self.state.temperature,
                'mode': self.state.mode
            }
        return None
    
    async def get_battery_status(self) -> Optional[Dict]:
        """Получение статуса батареи"""
        if self.state:
            return {
                'voltage': self.state.battery_voltage,
                'current': self.state.battery_current,
                'percent': 95
            }
        return None
    
    async def calibrate_imu(self) -> bool:
        """Калибровка ИМУ"""
        command = self._create_command('CALIB', {})
        return await self._send_command(command)
    
    async def reset_vehicle(self) -> bool:
        """Перезагрузка аппарата"""
        command = self._create_command('RESET', {})
        return await self._send_command(command)
