"""
Менеджер симуляторов - объединяет все интеграции с различными симуляторами
Позволяет легко переключаться между 5 различными платформами моделирования
"""
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Union

from utils.logger import setup_logger

logger = setup_logger(__name__)


class SimulatorType(Enum):
    """Типы поддерживаемых симуляторов"""
    AIRSIM = "airsim"
    GRID = "grid"
    SIMNET = "simnet"
    SKYROVER = "skyrover"
    UNREAL_ENGINE = "unreal_engine"


class SimulatorManager:
    """
    Менеджер симуляторов с поддержкой 5 различных платформ.
    
    Поддерживаемые симуляторы:
    1. AirSim - быстрый, с интеграцией UE
    2. Grid - российский, высокое качество физики
    3. SIMNET - облачная платформа
    4. SkyRover - гибридный (наземный + воздушный)
    5. Unreal Engine 5+ - максимальная реалистичность
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация менеджера симуляторов.
        
        Args:
            config: Конфигурация со всеми параметрами симуляторов
        """
        self.config = config
        self.active_simulator: Optional[SimulatorType] = None
        self.clients = {}
        self._init_flag = False
        
        logger.info("SimulatorManager инициализирован")
    
    async def initialize(self, simulator: SimulatorType) -> bool:
        """
        Инициализация выбранного симулятора.
        
        Args:
            simulator: Тип симулятора для подключения
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            # Импорт нужного клиента
            if simulator == SimulatorType.AIRSIM:
                from sim.airsim_client import AirSimClient
                client = AirSimClient(self.config)
            
            elif simulator == SimulatorType.GRID:
                from sim.grid_simulator import GridSimulatorClient
                client = GridSimulatorClient(self.config)
            
            elif simulator == SimulatorType.SIMNET:
                from sim.simnet_client import SimnetClient
                client = SimnetClient(self.config)
            
            elif simulator == SimulatorType.SKYROVER:
                from sim.skyrover_client import SkyRoverClient
                client = SkyRoverClient(self.config)
            
            elif simulator == SimulatorType.UNREAL_ENGINE:
                from sim.unreal_engine_client import UnrealEngineClient
                client = UnrealEngineClient(self.config)
            
            else:
                logger.error(f"Неизвестный симулятор: {simulator}")
                return False
            
            # Подключение к симулятору
            connected = await client.connect()
            
            if connected:
                self.clients[simulator] = client
                self.active_simulator = simulator
                self._init_flag = True
                
                logger.info(f"✅ Инициализирован симулятор {simulator.value}")
                return True
            else:
                logger.error(f"❌ Неудалось подключиться к {simulator.value}")
                return False
        
        except ImportError as e:
            logger.error(f"Ошибка импорта клиента симулятора: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка инициализации симулятора: {e}")
            return False
    
    async def switch_simulator(self, new_simulator: SimulatorType) -> bool:
        """
        Переключение на другой симулятор.
        
        Args:
            new_simulator: Тип нового симулятора
        
        Returns:
            bool: True если переключение успешно
        """
        try:
            # Отключение текущего симулятора
            if self.active_simulator:
                await self.disconnect()
            
            # Подключение к новому
            return await self.initialize(new_simulator)
        
        except Exception as e:
            logger.error(f"Ошибка переключения симулятора: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Отключение от активного симулятора"""
        try:
            if self.active_simulator and self.active_simulator in self.clients:
                client = self.clients[self.active_simulator]
                await client.disconnect()
                
                logger.info(f"Отключено от {self.active_simulator.value}")
            
            self.active_simulator = None
            self._init_flag = False
        
        except Exception as e:
            logger.error(f"Ошибка отключения: {e}")
    
    # Команды управления дроном (работают с любым активным симулятором)
    
    async def arm_drone(self) -> bool:
        """Взведение дрона"""
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            return await client.arm_drone()
        except AttributeError:
            logger.error(f"Симулятор {self.active_simulator.value} не поддерживает взведение")
            return False
    
    async def disarm_drone(self) -> bool:
        """Снятие дрона с боевого взвода"""
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            return await client.disarm_drone()
        except AttributeError:
            logger.error(f"Симулятор {self.active_simulator.value} не поддерживает снятие с взвода")
            return False
    
    async def takeoff(self, altitude: float) -> bool:
        """
        Взлёт на заданную высоту.
        
        Args:
            altitude: Высота взлёта в метрах
        """
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            return await client.takeoff(altitude)
        except AttributeError:
            logger.error(f"Симулятор {self.active_simulator.value} не поддерживает взлёт")
            return False
    
    async def land(self) -> bool:
        """Посадка дрона"""
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            return await client.land()
        except AttributeError:
            logger.error(f"Симулятор {self.active_simulator.value} не поддерживает посадку")
            return False
    
    async def move_to(self, x: float, y: float, z: float, speed: float = 5.0) -> bool:
        """
        Полёт к координатам.
        
        Args:
            x, y, z: Координаты назначения
            speed: Скорость полёта в м/с
        """
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            
            # Адаптация метода в зависимости от симулятора
            if self.active_simulator == SimulatorType.UNREAL_ENGINE:
                return await client.move_to_location(x, y, z)
            else:
                return await client.move_to(x, y, z, speed)
        
        except AttributeError:
            logger.error(f"Симулятор {self.active_simulator.value} не поддерживает навигацию")
            return False
    
    async def set_velocity(self, vx: float, vy: float, vz: float) -> bool:
        """Установка вектора скорости"""
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            return await client.set_velocity(vx, vy, vz)
        except AttributeError:
            logger.error(f"Симулятор {self.active_simulator.value} не поддерживает установку скорости")
            return False
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Получение телеметрии от активного симулятора"""
        if not self._check_connection():
            return None
        
        try:
            client = self.clients[self.active_simulator]
            return client.get_telemetry()
        except Exception as e:
            logger.error(f"Ошибка получения телеметрии: {e}")
            return None
    
    async def get_system_status(self) -> Optional[Dict[str, Any]]:
        """Получение статуса системы"""
        if not self._check_connection():
            return None
        
        try:
            client = self.clients[self.active_simulator]
            
            if hasattr(client, 'get_system_status'):
                return await client.get_system_status()
            else:
                return self.get_telemetry()
        
        except Exception as e:
            logger.error(f"Ошибка получения статуса: {e}")
            return None
    
    def get_available_simulators(self) -> List[str]:
        """Получение списка доступных симуляторов"""
        return [s.value for s in SimulatorType]
    
    def get_active_simulator(self) -> Optional[str]:
        """Получение активного симулятора"""
        return self.active_simulator.value if self.active_simulator else None
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self._init_flag and self.active_simulator is not None
    
    def _check_connection(self) -> bool:
        """Проверка наличия активного подключения"""
        if not self.is_connected():
            logger.error("Не подключено к симулятору. Сначала вызовите initialize()")
            return False
        return True
    
    # Симулятор-специфичные методы
    
    async def reset_simulation(self) -> bool:
        """Перезагрузка текущей симуляции"""
        if not self._check_connection():
            return False
        
        try:
            client = self.clients[self.active_simulator]
            
            if hasattr(client, 'reset_simulation'):
                return await client.reset_simulation()
            elif hasattr(client, 'reset'):
                return await client.reset()
            else:
                logger.warning(f"Симулятор {self.active_simulator.value} не поддерживает перезагрузку")
                return False
        
        except Exception as e:
            logger.error(f"Ошибка перезагрузки: {e}")
            return False
    
    # Grid-специфичные методы
    
    async def grid_set_yaw(self, yaw: float) -> bool:
        """Grid: установка курса"""
        if self.active_simulator != SimulatorType.GRID:
            logger.error("Метод доступен только для Grid")
            return False
        
        client = self.clients[SimulatorType.GRID]
        return await client.set_yaw(yaw)
    
    # SIMNET-специфичные методы
    
    async def simnet_set_weather(self, weather: Dict[str, Any]) -> bool:
        """SIMNET: установка погодных условий"""
        if self.active_simulator != SimulatorType.SIMNET:
            logger.error("Метод доступен только для SIMNET")
            return False
        
        client = self.clients[SimulatorType.SIMNET]
        return await client.set_weather(weather)
    
    async def simnet_get_scenarios(self) -> List[str]:
        """SIMNET: получение доступных сценариев"""
        if self.active_simulator != SimulatorType.SIMNET:
            logger.error("Метод доступен только для SIMNET")
            return []
        
        client = self.clients[SimulatorType.SIMNET]
        return await client.get_available_scenarios()
    
    # SkyRover-специфичные методы
    
    async def skyrover_set_mode(self, mode: str) -> bool:
        """SkyRover: смена режима (ground/air/hover)"""
        if self.active_simulator != SimulatorType.SKYROVER:
            logger.error("Метод доступен только для SkyRover")
            return False
        
        client = self.clients[SimulatorType.SKYROVER]
        return await client.set_mode(mode)
    
    async def skyrover_move_forward(self, distance: float, speed: float = 1.0) -> bool:
        """SkyRover: движение вперёд в ground_mode"""
        if self.active_simulator != SimulatorType.SKYROVER:
            logger.error("Метод доступен только для SkyRover")
            return False
        
        client = self.clients[SimulatorType.SKYROVER]
        return await client.move_forward(distance, speed)
    
    # Unreal Engine-специфичные методы
    
    async def ue_set_graphics_quality(self, quality: str) -> bool:
        """Unreal Engine: установка качества графики"""
        if self.active_simulator != SimulatorType.UNREAL_ENGINE:
            logger.error("Метод доступен только для Unreal Engine")
            return False
        
        client = self.clients[SimulatorType.UNREAL_ENGINE]
        return await client.set_graphics_quality(quality)
    
    async def ue_capture_camera(self) -> Optional[bytes]:
        """Unreal Engine: захват кадра с камеры"""
        if self.active_simulator != SimulatorType.UNREAL_ENGINE:
            logger.error("Метод доступен только для Unreal Engine")
            return None
        
        client = self.clients[SimulatorType.UNREAL_ENGINE]
        return await client.get_camera_frame()
    
    async def ue_take_screenshot(self, filename: str = 'screenshot.png') -> bool:
        """Unreal Engine: скриншот"""
        if self.active_simulator != SimulatorType.UNREAL_ENGINE:
            logger.error("Метод доступен только для Unreal Engine")
            return False
        
        client = self.clients[SimulatorType.UNREAL_ENGINE]
        return await client.take_screenshot(filename)
    
    # Статистика и информация
    
    def get_simulator_info(self, simulator: Optional[SimulatorType] = None) -> Dict[str, Any]:
        """Получение информации о симуляторе"""
        if simulator is None:
            simulator = self.active_simulator
        
        if not simulator:
            return {}
        
        info = {
            'name': simulator.value,
            'connected': simulator in self.clients,
        }
        
        if simulator == SimulatorType.AIRSIM:
            info['description'] = 'High-speed simulator with UE integration'
            info['features'] = ['Fast', 'Realistic physics', 'UE5 graphics']
        
        elif simulator == SimulatorType.GRID:
            info['description'] = 'Russian high-accuracy simulator'
            info['features'] = ['High physics accuracy', 'MAVLink support', 'Multi-drone']
        
        elif simulator == SimulatorType.SIMNET:
            info['description'] = 'Cloud-based simulation platform'
            info['features'] = ['Cloud-based', 'Weather simulation', 'Scenarios']
        
        elif simulator == SimulatorType.SKYROVER:
            info['description'] = 'Hybrid ground/air platform'
            info['features'] = ['Hybrid mode', 'Serial interface', 'Real hardware support']
        
        elif simulator == SimulatorType.UNREAL_ENGINE:
            info['description'] = 'Photo-realistic simulation with UE5'
            info['features'] = ['Ultra-realistic', 'Nanite graphics', 'Pixel Streaming']
        
        return info
    
    async def print_simulator_status(self) -> None:
        """Вывод статуса всех симуляторов"""
        logger.info("=" * 60)
        logger.info("СТАТУС СИМУЛЯТОРОВ")
        logger.info("=" * 60)
        
        for sim_type in SimulatorType:
            info = self.get_simulator_info(sim_type)
            status = "✅ ПОДКЛЮЧЕН" if info.get('connected') else "❌ не подключен"
            logger.info(f"{info['name']:<20} {status}")
        
        if self.active_simulator:
            logger.info(f"\nАктивный: {self.active_simulator.value}")
        
        logger.info("=" * 60)
