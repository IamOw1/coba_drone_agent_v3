"""
Logistics (Autrailistics) - Инструмент логистики и доставки
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from tools.base_tool import BaseTool, ToolStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PackageStatus(Enum):
    """Статус посылки"""
    PENDING = "pending"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class Package:
    """Посылка"""
    package_id: str
    weight: float  # кг
    dimensions: Dict[str, float]  # x, y, z в см
    pickup_location: Dict[str, float]
    delivery_location: Dict[str, float]
    priority: int = 1
    status: PackageStatus = PackageStatus.PENDING
    created_at: str = None
    delivered_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class LogisticsTool(BaseTool):
    """
    Инструмент логистики и доставки.
    Управляет доставкой посылок, оптимизирует маршруты,
    отслеживает статус доставок.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        super().__init__(config, agent)
        self.name = "logistics"
        self.description = "Логистика и доставка"
        self.version = "2.0.0"
        
        # Параметры логистики
        logistics_config = config.get('logistics', {})
        
        self.max_payload_weight = logistics_config.get('max_payload_weight', 2.0)  # кг
        self.max_payload_size = logistics_config.get('max_payload_size', 
                                                      {"x": 30, "y": 30, "z": 20})  # см
        self.delivery_speed = logistics_config.get('delivery_speed', 10.0)
        self.return_after_delivery = logistics_config.get('return_after_delivery', True)
        
        # Посылки
        self.packages: Dict[str, Package] = {}
        self.active_deliveries: Dict[str, Package] = {}
        self.delivery_history: List[Dict[str, Any]] = []
        
        # Статистика
        self.stats = {
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "total_distance": 0.0
        }
        
        logger.info("Logistics инициализирован")
    
    async def initialize(self):
        """Инициализация инструмента логистики"""
        self.status = ToolStatus.READY
        logger.info("Logistics готов к работе")
    
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение логистики.
        
        Args:
            data (Dict[str, Any]): Данные для логистики.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        operation = data.get("operation")
        
        if operation == "register_package":
            return await self.action_register_package(**data.get("params", {}))
        elif operation == "deliver":
            return await self.action_deliver_package(**data.get("params", {}))
        elif operation == "status":
            return await self.action_get_delivery_status(**data.get("params", {}))
        
        return {"success": False, "error": f"Неизвестная операция: {operation}"}
    
    async def action_register_package(self,
                                      package_id: str,
                                      weight: float,
                                      dimensions: Dict[str, float],
                                      pickup_location: Dict[str, float],
                                      delivery_location: Dict[str, float],
                                      priority: int = 1) -> Dict[str, Any]:
        """
        Регистрация посылки для доставки.
        
        Args:
            package_id (str): ID посылки.
            weight (float): Вес в кг.
            dimensions (Dict[str, float]): Размеры в см.
            pickup_location (Dict[str, float]): Точка забора.
            delivery_location (Dict[str, float]): Точка доставки.
            priority (int): Приоритет (1-10).
            
        Returns:
            Dict[str, Any]: Результат регистрации.
        """
        # Проверка веса
        if weight > self.max_payload_weight:
            return {
                "success": False,
                "error": f"Вес посылки ({weight}кг) превышает максимальный ({self.max_payload_weight}кг)"
            }
        
        # Проверка размеров
        for dim in ["x", "y", "z"]:
            if dimensions.get(dim, 0) > self.max_payload_size.get(dim, 0):
                return {
                    "success": False,
                    "error": f"Размер {dim} превышает допустимый"
                }
        
        package = Package(
            package_id=package_id,
            weight=weight,
            dimensions=dimensions,
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            priority=priority
        )
        
        self.packages[package_id] = package
        
        logger.info(f"Зарегистрирована посылка {package_id} ({weight}кг)")
        
        return {
            "success": True,
            "package_id": package_id,
            "estimated_time": self._estimate_delivery_time(package)
        }
    
    async def action_deliver_package(self, package_id: str) -> Dict[str, Any]:
        """
        Доставка посылки.
        
        Args:
            package_id (str): ID посылки.
            
        Returns:
            Dict[str, Any]: Результат доставки.
        """
        if package_id not in self.packages:
            return {
                "success": False,
                "error": f"Посылка {package_id} не найдена"
            }
        
        package = self.packages[package_id]
        
        # Проверка статуса
        if package.status != PackageStatus.PENDING:
            return {
                "success": False,
                "error": f"Посылка уже в статусе: {package.status.value}"
            }
        
        # Начало доставки
        package.status = PackageStatus.IN_TRANSIT
        self.active_deliveries[package_id] = package
        
        logger.info(f"Начата доставка посылки {package_id}")
        
        # Симуляция доставки
        await self._simulate_delivery(package)
        
        # Завершение доставки
        package.status = PackageStatus.DELIVERED
        package.delivered_at = datetime.now().isoformat()
        
        del self.active_deliveries[package_id]
        
        # Обновление статистики
        self.stats["total_deliveries"] += 1
        self.stats["successful_deliveries"] += 1
        
        self.delivery_history.append({
            "package_id": package_id,
            "pickup": package.pickup_location,
            "delivery": package.delivery_location,
            "delivered_at": package.delivered_at
        })
        
        logger.info(f"Посылка {package_id} доставлена")
        
        return {
            "success": True,
            "package_id": package_id,
            "status": "delivered",
            "delivered_at": package.delivered_at
        }
    
    async def _simulate_delivery(self, package: Package):
        """Симуляция процесса доставки"""
        # 1. Полет к точке забора
        logger.info(f"Полет к точке забора {package.pickup_location}")
        await asyncio.sleep(1)
        
        package.status = PackageStatus.PICKED_UP
        logger.info(f"Посылка {package.package_id} забрана")
        
        # 2. Полет к точке доставки
        logger.info(f"Полет к точке доставки {package.delivery_location}")
        await asyncio.sleep(2)
        
        # 3. Доставка
        logger.info(f"Доставка посылки {package.package_id}")
        await asyncio.sleep(0.5)
    
    def _estimate_delivery_time(self, package: Package) -> float:
        """Оценка времени доставки в минутах"""
        # Расчет расстояния
        dx = package.delivery_location["x"] - package.pickup_location["x"]
        dy = package.delivery_location["y"] - package.pickup_location["y"]
        distance = (dx**2 + dy**2) ** 0.5
        
        # Время полета (туда и обратно)
        flight_time = (distance / self.delivery_speed) * 2 / 60  # в минутах
        
        # Дополнительное время на погрузку/разгрузку
        handling_time = 2
        
        return flight_time + handling_time
    
    async def action_get_delivery_status(self, package_id: str) -> Dict[str, Any]:
        """
        Получение статуса доставки.
        
        Args:
            package_id (str): ID посылки.
            
        Returns:
            Dict[str, Any]: Статус доставки.
        """
        if package_id not in self.packages:
            return {
                "success": False,
                "error": f"Посылка {package_id} не найдена"
            }
        
        package = self.packages[package_id]
        
        return {
            "success": True,
            "package_id": package_id,
            "status": package.status.value,
            "created_at": package.created_at,
            "delivered_at": package.delivered_at,
            "pickup_location": package.pickup_location,
            "delivery_location": package.delivery_location
        }
    
    async def action_list_packages(self, status: str = None) -> Dict[str, Any]:
        """
        Список посылок.
        
        Args:
            status (str): Фильтр по статусу.
            
        Returns:
            Dict[str, Any]: Список посылок.
        """
        packages = self.packages.values()
        
        if status:
            packages = [p for p in packages if p.status.value == status]
        
        return {
            "success": True,
            "packages": [
                {
                    "package_id": p.package_id,
                    "status": p.status.value,
                    "weight": p.weight,
                    "priority": p.priority
                }
                for p in packages
            ]
        }
    
    async def action_optimize_route(self, package_ids: List[str]) -> Dict[str, Any]:
        """
        Оптимизация маршрута доставки нескольких посылок.
        
        Args:
            package_ids (List[str]): Список ID посылок.
            
        Returns:
            Dict[str, Any]: Оптимизированный маршрут.
        """
        # Простая сортировка по приоритету
        packages = [self.packages[pid] for pid in package_ids if pid in self.packages]
        packages.sort(key=lambda p: p.priority, reverse=True)
        
        route = []
        for p in packages:
            route.append({
                "type": "pickup",
                "location": p.pickup_location,
                "package_id": p.package_id
            })
            route.append({
                "type": "delivery",
                "location": p.delivery_location,
                "package_id": p.package_id
            })
        
        return {
            "success": True,
            "route": route,
            "stops": len(route)
        }
    
    async def action_get_statistics(self) -> Dict[str, Any]:
        """Получение статистики доставок"""
        return {
            "success": True,
            "statistics": self.stats,
            "active_deliveries": len(self.active_deliveries),
            "pending_packages": sum(1 for p in self.packages.values() 
                                   if p.status == PackageStatus.PENDING)
        }
    
    async def shutdown(self):
        """Завершение работы инструмента"""
        logger.info(f"Инструмент {self.name} завершает работу")
        self.status = ToolStatus.SHUTDOWN
