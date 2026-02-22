"""
MissionPlanner - Инструмент планировщика миссий
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import math

from tools.base_tool import BaseTool, ToolStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class MissionWaypoint:
    """Точка миссии"""
    x: float
    y: float
    z: float
    speed: float = 5.0
    action: str = None
    action_params: Dict[str, Any] = field(default_factory=dict)
    hover_time: float = 0.0


@dataclass
class Mission:
    """Миссия"""
    mission_id: str
    name: str
    description: str
    waypoints: List[MissionWaypoint]
    mission_type: str = "generic"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    parameters: Dict[str, Any] = field(default_factory=dict)


class MissionPlannerTool(BaseTool):
    """
    Инструмент планировщика миссий.
    Создает, редактирует и управляет миссиями дрона.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        super().__init__(config, agent)
        self.name = "mission_planner"
        self.description = "Планировщик миссий"
        self.version = "2.0.0"
        
        # Шаблоны миссий
        self.templates = {
            "survey": self._create_survey_mission,
            "patrol": self._create_patrol_mission,
            "inspection": self._create_inspection_mission,
            "search": self._create_search_mission,
            "delivery": self._create_delivery_mission,
            "photography": self._create_photography_mission,
        }
        
        # Хранилище миссий
        self.missions: Dict[str, Mission] = {}
        self.current_mission: Optional[Mission] = None
        
        # Путь сохранения
        self.missions_path = Path("data/missions")
        self.missions_path.mkdir(parents=True, exist_ok=True)
        
        # Загрузка существующих миссий
        self._load_missions()
        
        logger.info("MissionPlanner инициализирован")
    
    async def initialize(self):
        """Инициализация планировщика"""
        self.status = ToolStatus.READY
        logger.info("MissionPlanner готов к работе")
    
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение планировщика.
        
        Args:
            data (Dict[str, Any]): Данные для планирования.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        operation = data.get("operation")
        
        if operation == "create":
            return await self.action_create_mission(**data.get("params", {}))
        elif operation == "load":
            return await self.action_load_mission(**data.get("params", {}))
        elif operation == "save":
            return await self.action_save_mission(**data.get("params", {}))
        
        return {"success": False, "error": f"Неизвестная операция: {operation}"}
    
    async def action_create_mission(self, 
                                    name: str,
                                    mission_type: str,
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создание миссии из шаблона.
        
        Args:
            name (str): Название миссии.
            mission_type (str): Тип миссии.
            params (Dict[str, Any]): Параметры миссии.
            
        Returns:
            Dict[str, Any]: Созданная миссия.
        """
        if mission_type not in self.templates:
            return {
                "success": False,
                "error": f"Неизвестный тип миссии: {mission_type}",
                "available_types": list(self.templates.keys())
            }
        
        # Создание миссии из шаблона
        creator = self.templates[mission_type]
        mission = creator(name, params)
        
        # Сохранение миссии
        self.missions[mission.mission_id] = mission
        
        logger.info(f"Создана миссия '{name}' типа '{mission_type}'")
        
        return {
            "success": True,
            "mission": {
                "mission_id": mission.mission_id,
                "name": mission.name,
                "type": mission.mission_type,
                "waypoints_count": len(mission.waypoints)
            }
        }
    
    def _create_survey_mission(self, name: str, params: Dict[str, Any]) -> Mission:
        """Создание миссии обследования территории"""
        area = params.get("area", {"x": 0, "y": 0, "width": 100, "height": 100})
        altitude = params.get("altitude", 30)
        speed = params.get("speed", 5)
        overlap = params.get("overlap", 0.7)
        
        # Расчет точек маршрута (змейка)
        waypoints = []
        x_start = area["x"]
        y_start = area["y"]
        width = area["width"]
        height = area["height"]
        
        strip_width = altitude * 0.5 * (1 - overlap)
        strips = int(height / strip_width)
        
        for i in range(strips):
            y = y_start + i * strip_width
            
            if i % 2 == 0:
                waypoints.append(MissionWaypoint(x_start, y, altitude, speed, "take_photo"))
                waypoints.append(MissionWaypoint(x_start + width, y, altitude, speed, "take_photo"))
            else:
                waypoints.append(MissionWaypoint(x_start + width, y, altitude, speed, "take_photo"))
                waypoints.append(MissionWaypoint(x_start, y, altitude, speed, "take_photo"))
        
        return Mission(
            mission_id=f"survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            description=f"Обследование территории {width}x{height}м",
            waypoints=waypoints,
            mission_type="survey",
            parameters={"area": area, "altitude": altitude, "overlap": overlap}
        )
    
    def _create_patrol_mission(self, name: str, params: Dict[str, Any]) -> Mission:
        """Создание миссии патрулирования"""
        points = params.get("points", [])
        altitude = params.get("altitude", 30)
        speed = params.get("speed", 8)
        loops = params.get("loops", 1)
        
        waypoints = []
        
        for _ in range(loops):
            for point in points:
                waypoints.append(MissionWaypoint(
                    point.get("x", 0),
                    point.get("y", 0),
                    altitude,
                    speed,
                    hover_time=point.get("hover_time", 5)
                ))
        
        return Mission(
            mission_id=f"patrol_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            description=f"Патрулирование по {len(points)} точкам",
            waypoints=waypoints,
            mission_type="patrol",
            parameters={"loops": loops}
        )
    
    def _create_inspection_mission(self, name: str, params: Dict[str, Any]) -> Mission:
        """Создание миссии инспекции объекта"""
        target = params.get("target", {"x": 0, "y": 0, "z": 0})
        altitude = params.get("altitude", 20)
        radius = params.get("radius", 10)
        photo_count = params.get("photo_count", 8)
        
        waypoints = []
        
        # Орбитальный облет
        for i in range(photo_count):
            angle = 2 * math.pi * i / photo_count
            x = target["x"] + radius * math.cos(angle)
            y = target["y"] + radius * math.sin(angle)
            
            waypoints.append(MissionWaypoint(
                x, y, altitude, 3, "take_photo",
                action_params={"gimbal_pitch": -45, "target": target}
            ))
        
        return Mission(
            mission_id=f"inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            description=f"Инспекция объекта с {photo_count} ракурсов",
            waypoints=waypoints,
            mission_type="inspection",
            parameters={"target": target, "radius": radius}
        )
    
    def _create_search_mission(self, name: str, params: Dict[str, Any]) -> Mission:
        """Создание миссии поиска"""
        area = params.get("area", {"x": 0, "y": 0, "width": 200, "height": 200})
        altitude = params.get("altitude", 40)
        speed = params.get("speed", 6)
        search_pattern = params.get("search_pattern", "grid")
        
        waypoints = []
        
        if search_pattern == "grid":
            # Сетчатый поиск
            waypoints = self._create_grid_pattern(area, altitude, speed)
        elif search_pattern == "spiral":
            # Спиральный поиск
            waypoints = self._create_spiral_pattern(area, altitude, speed)
        
        return Mission(
            mission_id=f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            description=f"Поиск в области {area['width']}x{area['height']}м",
            waypoints=waypoints,
            mission_type="search",
            parameters={"area": area, "search_pattern": search_pattern}
        )
    
    def _create_grid_pattern(self, area: Dict, altitude: float, 
                            speed: float) -> List[MissionWaypoint]:
        """Создание сетчатого шаблона поиска"""
        waypoints = []
        x_start = area["x"]
        y_start = area["y"]
        width = area["width"]
        height = area["height"]
        
        step = 20  # шаг сетки
        
        for y in range(int(y_start), int(y_start + height) + 1, step):
            if (y // step) % 2 == 0:
                waypoints.append(MissionWaypoint(x_start, y, altitude, speed))
                waypoints.append(MissionWaypoint(x_start + width, y, altitude, speed))
            else:
                waypoints.append(MissionWaypoint(x_start + width, y, altitude, speed))
                waypoints.append(MissionWaypoint(x_start, y, altitude, speed))
        
        return waypoints
    
    def _create_spiral_pattern(self, area: Dict, altitude: float, 
                              speed: float) -> List[MissionWaypoint]:
        """Создание спирального шаблона поиска"""
        waypoints = []
        center_x = area["x"] + area["width"] / 2
        center_y = area["y"] + area["height"] / 2
        
        max_radius = min(area["width"], area["height"]) / 2
        step = 10
        
        radius = step
        while radius <= max_radius:
            circumference = 2 * math.pi * radius
            segments = max(8, int(circumference / step))
            
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                waypoints.append(MissionWaypoint(x, y, altitude, speed))
            
            radius += step
        
        return waypoints
    
    def _create_delivery_mission(self, name: str, params: Dict[str, Any]) -> Mission:
        """Создание миссии доставки"""
        pickup = params.get("pickup", {"x": 0, "y": 0})
        dropoff = params.get("dropoff", {"x": 100, "y": 100})
        altitude = params.get("altitude", 30)
        speed = params.get("speed", 10)
        
        waypoints = [
            MissionWaypoint(pickup["x"], pickup["y"], altitude, speed, "pickup_package"),
            MissionWaypoint(dropoff["x"], dropoff["y"], altitude, speed, "drop_package")
        ]
        
        return Mission(
            mission_id=f"delivery_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            description=f"Доставка из ({pickup['x']}, {pickup['y']}) в ({dropoff['x']}, {dropoff['y']})",
            waypoints=waypoints,
            mission_type="delivery",
            parameters={"pickup": pickup, "dropoff": dropoff}
        )
    
    def _create_photography_mission(self, name: str, params: Dict[str, Any]) -> Mission:
        """Создание миссии аэрофотосъемки"""
        subjects = params.get("subjects", [])
        altitude = params.get("altitude", 50)
        
        waypoints = []
        
        for subject in subjects:
            # Точка съемки
            waypoints.append(MissionWaypoint(
                subject.get("x", 0),
                subject.get("y", 0),
                altitude,
                3,
                "take_photo",
                action_params={
                    "gimbal_pitch": subject.get("gimbal_pitch", -90),
                    "heading": subject.get("heading", 0)
                },
                hover_time=subject.get("hover_time", 3)
            ))
        
        return Mission(
            mission_id=f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            description=f"Аэрофотосъемка {len(subjects)} объектов",
            waypoints=waypoints,
            mission_type="photography",
            parameters={"subjects_count": len(subjects)}
        )
    
    async def action_load_mission(self, mission_id: str) -> Dict[str, Any]:
        """Загрузка миссии"""
        if mission_id not in self.missions:
            return {
                "success": False,
                "error": f"Миссия {mission_id} не найдена"
            }
        
        self.current_mission = self.missions[mission_id]
        
        return {
            "success": True,
            "mission": {
                "mission_id": self.current_mission.mission_id,
                "name": self.current_mission.name,
                "waypoints_count": len(self.current_mission.waypoints)
            }
        }
    
    async def action_save_mission(self, mission_id: str = None) -> Dict[str, Any]:
        """Сохранение миссии в файл"""
        mission = self.missions.get(mission_id) if mission_id else self.current_mission
        
        if not mission:
            return {
                "success": False,
                "error": "Миссия не выбрана"
            }
        
        filename = f"{mission.mission_id}.json"
        filepath = self.missions_path / filename
        
        data = {
            "mission_id": mission.mission_id,
            "name": mission.name,
            "description": mission.description,
            "type": mission.mission_type,
            "created": mission.created,
            "parameters": mission.parameters,
            "waypoints": [
                {
                    "x": wp.x,
                    "y": wp.y,
                    "z": wp.z,
                    "speed": wp.speed,
                    "action": wp.action,
                    "hover_time": wp.hover_time
                }
                for wp in mission.waypoints
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "filepath": str(filepath)
        }
    
    def _load_missions(self):
        """Загрузка миссий из файлов"""
        if not self.missions_path.exists():
            return
        
        for filepath in self.missions_path.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                mission = Mission(
                    mission_id=data["mission_id"],
                    name=data["name"],
                    description=data.get("description", ""),
                    waypoints=[
                        MissionWaypoint(
                            wp["x"], wp["y"], wp["z"],
                            wp.get("speed", 5),
                            wp.get("action"),
                            wp.get("action_params", {}),
                            wp.get("hover_time", 0)
                        )
                        for wp in data.get("waypoints", [])
                    ],
                    mission_type=data.get("type", "generic"),
                    created=data.get("created", datetime.now().isoformat()),
                    parameters=data.get("parameters", {})
                )
                
                self.missions[mission.mission_id] = mission
                
            except Exception as e:
                logger.error(f"Ошибка загрузки миссии {filepath}: {e}")
    
    async def action_list_missions(self) -> Dict[str, Any]:
        """Список всех миссий"""
        return {
            "success": True,
            "missions": [
                {
                    "mission_id": m.mission_id,
                    "name": m.name,
                    "type": m.mission_type,
                    "waypoints_count": len(m.waypoints)
                }
                for m in self.missions.values()
            ]
        }
    
    async def action_delete_mission(self, mission_id: str) -> Dict[str, Any]:
        """Удаление миссии"""
        if mission_id not in self.missions:
            return {
                "success": False,
                "error": f"Миссия {mission_id} не найдена"
            }
        
        del self.missions[mission_id]
        
        # Удаление файла
        filepath = self.missions_path / f"{mission_id}.json"
        if filepath.exists():
            filepath.unlink()
        
        return {
            "success": True,
            "message": f"Миссия {mission_id} удалена"
        }
    
    async def shutdown(self):
        """Завершение работы инструмента"""
        # Сохранение текущей миссии
        if self.current_mission:
            await self.action_save_mission(self.current_mission.mission_id)
        
        logger.info(f"Инструмент {self.name} завершает работу")
        self.status = ToolStatus.SHUTDOWN
