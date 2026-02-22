"""
GeoMap - Инструмент геопространственного картографирования
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

try:
    import folium
    from folium.plugins import Draw, MarkerCluster
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from tools.base_tool import BaseTool, ToolStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class MapPoint:
    """Точка на карте"""
    lat: float
    lon: float
    altitude: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MapArea:
    """Область на карте"""
    name: str
    points: List[MapPoint]
    area_type: str = "generic"  # survey, no_fly, interest, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


class GeoMapTool(BaseTool):
    """
    Инструмент геопространственного картографирования.
    Создает карты местности, планирует маршруты обследования,
    управляет геозонами.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        super().__init__(config, agent)
        self.name = "geomap"
        self.description = "Геопространственное картографирование"
        self.version = "2.0.0"
        
        # Параметры картирования
        map_config = config.get('mapping', {})
        
        self.default_altitude = map_config.get('default_altitude', 50)
        self.overlap = map_config.get('overlap', 0.7)  # перекрытие снимков
        self.resolution = map_config.get('resolution', 0.01)  # м/пиксель
        
        # Хранилище данных
        self.map_points: List[MapPoint] = []
        self.map_areas: Dict[str, MapArea] = {}
        self.current_map = None
        
        # Путь сохранения карт
        self.maps_path = Path("data/maps")
        self.maps_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("GeoMap инициализирован")
    
    async def initialize(self):
        """Инициализация инструмента картирования"""
        self.status = ToolStatus.READY
        logger.info("GeoMap готов к работе")
    
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение картографирования.
        
        Args:
            data (Dict[str, Any]): Данные для картирования.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        operation = data.get("operation")
        
        if operation == "add_point":
            return await self.action_add_point(**data.get("params", {}))
        elif operation == "create_survey":
            return await self.action_create_survey_mission(**data.get("params", {}))
        elif operation == "save_map":
            return await self.action_save_map(**data.get("params", {}))
        
        return {"success": False, "error": f"Неизвестная операция: {operation}"}
    
    async def action_add_point(self, lat: float, lon: float, 
                               altitude: float = None,
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Добавление точки на карту.
        
        Args:
            lat (float): Широта.
            lon (float): Долгота.
            altitude (float): Высота.
            metadata (Dict[str, Any]): Метаданные точки.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        point = MapPoint(
            lat=lat,
            lon=lon,
            altitude=altitude or self.default_altitude,
            metadata=metadata or {}
        )
        
        self.map_points.append(point)
        
        return {
            "success": True,
            "point": {
                "lat": lat,
                "lon": lon,
                "altitude": point.altitude
            },
            "total_points": len(self.map_points)
        }
    
    async def action_create_survey_mission(self, 
                                           area_name: str,
                                           bounds: Dict[str, float],
                                           altitude: float = None,
                                           speed: float = 5.0,
                                           gimbal_pitch: float = -90) -> Dict[str, Any]:
        """
        Создание миссии для обследования области.
        
        Args:
            area_name (str): Название области.
            bounds (Dict[str, float]): Границы области (north, south, east, west).
            altitude (float): Высота полета.
            speed (float): Скорость.
            gimbal_pitch (float): Угол наклона камеры.
            
        Returns:
            Dict[str, Any]: Миссия обследования.
        """
        altitude = altitude or self.default_altitude
        
        # Расчет точек маршрута (змейка)
        north = bounds.get("north", 0)
        south = bounds.get("south", 0)
        east = bounds.get("east", 0)
        west = bounds.get("west", 0)
        
        # Шаг между полосами (зависит от разрешения и перекрытия)
        strip_width = altitude * 0.5 * (1 - self.overlap)  # примерная ширина полосы
        
        waypoints = []
        lat = south
        direction = 1  # 1 - восток, -1 - запад
        
        while lat <= north:
            if direction == 1:
                waypoints.append({
                    "lat": lat,
                    "lon": west,
                    "altitude": altitude,
                    "speed": speed,
                    "gimbal_pitch": gimbal_pitch,
                    "action": "take_photo"
                })
                waypoints.append({
                    "lat": lat,
                    "lon": east,
                    "altitude": altitude,
                    "speed": speed,
                    "gimbal_pitch": gimbal_pitch,
                    "action": "take_photo"
                })
            else:
                waypoints.append({
                    "lat": lat,
                    "lon": east,
                    "altitude": altitude,
                    "speed": speed,
                    "gimbal_pitch": gimbal_pitch,
                    "action": "take_photo"
                })
                waypoints.append({
                    "lat": lat,
                    "lon": west,
                    "altitude": altitude,
                    "speed": speed,
                    "gimbal_pitch": gimbal_pitch,
                    "action": "take_photo"
                })
            
            lat += strip_width
            direction *= -1
        
        # Создание области
        area_points = [
            MapPoint(lat=north, lon=west),
            MapPoint(lat=north, lon=east),
            MapPoint(lat=south, lon=east),
            MapPoint(lat=south, lon=west)
        ]
        
        self.map_areas[area_name] = MapArea(
            name=area_name,
            points=area_points,
            area_type="survey",
            metadata={
                "altitude": altitude,
                "speed": speed,
                "waypoints_count": len(waypoints)
            }
        )
        
        logger.info(f"Создана миссия обследования '{area_name}' с {len(waypoints)} точками")
        
        return {
            "success": True,
            "area_name": area_name,
            "waypoints": waypoints,
            "estimated_time": len(waypoints) * 10,  # примерно
            "coverage": {
                "width": abs(east - west),
                "height": abs(north - south)
            }
        }
    
    async def action_create_3d_model_mission(self,
                                             area_name: str,
                                             center: Dict[str, float],
                                             radius: float,
                                             altitude: float = None,
                                             photo_count: int = 50) -> Dict[str, Any]:
        """
        Создание миссии для 3D моделирования (орбитальный полет).
        
        Args:
            area_name (str): Название области.
            center (Dict[str, float]): Центр области.
            radius (float): Радиус орбиты.
            altitude (float): Высота полета.
            photo_count (int): Количество фотографий.
            
        Returns:
            Dict[str, Any]: Миссия 3D моделирования.
        """
        altitude = altitude or self.default_altitude
        
        center_lat = center.get("lat", 0)
        center_lon = center.get("lon", 0)
        
        # Создание точек по кругу
        waypoints = []
        for i in range(photo_count):
            angle = 2 * np.pi * i / photo_count
            
            # Приближенный расчет смещения
            lat_offset = radius * np.cos(angle) / 111000
            lon_offset = radius * np.sin(angle) / (111000 * np.cos(np.radians(center_lat)))
            
            waypoints.append({
                "lat": center_lat + lat_offset,
                "lon": center_lon + lon_offset,
                "altitude": altitude,
                "speed": 3.0,
                "gimbal_pitch": -45,
                "action": "take_photo"
            })
        
        logger.info(f"Создана миссия 3D моделирования '{area_name}' с {len(waypoints)} точками")
        
        return {
            "success": True,
            "area_name": area_name,
            "waypoints": waypoints,
            "type": "3d_model",
            "center": center,
            "radius": radius
        }
    
    async def action_save_map(self, filename: str = None) -> Dict[str, Any]:
        """
        Сохранение карты.
        
        Args:
            filename (str): Имя файла.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        if not FOLIUM_AVAILABLE:
            # Сохранение в JSON
            filename = filename or f"map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.maps_path / filename
            
            data = {
                "points": [
                    {"lat": p.lat, "lon": p.lon, "altitude": p.altitude}
                    for p in self.map_points
                ],
                "areas": {
                    name: {
                        "type": area.area_type,
                        "points": [{"lat": p.lat, "lon": p.lon} for p in area.points]
                    }
                    for name, area in self.map_areas.items()
                },
                "created": datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "filepath": str(filepath),
                "points_count": len(self.map_points),
                "areas_count": len(self.map_areas)
            }
        
        # Создание интерактивной карты с folium
        filename = filename or f"map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.maps_path / filename
        
        if self.map_points:
            center = [self.map_points[0].lat, self.map_points[0].lon]
        else:
            center = [0, 0]
        
        m = folium.Map(location=center, zoom_start=15)
        
        # Добавление точек
        for point in self.map_points:
            folium.Marker(
                [point.lat, point.lon],
                popup=f"Alt: {point.altitude}m"
            ).add_to(m)
        
        # Добавление областей
        for name, area in self.map_areas.items():
            points = [[p.lat, p.lon] for p in area.points]
            folium.Polygon(
                points,
                popup=name,
                color="blue" if area.area_type == "survey" else "red",
                fill=True
            ).add_to(m)
        
        m.save(str(filepath))
        
        return {
            "success": True,
            "filepath": str(filepath),
            "points_count": len(self.map_points),
            "areas_count": len(self.map_areas)
        }
    
    async def action_load_map(self, filename: str) -> Dict[str, Any]:
        """
        Загрузка карты.
        
        Args:
            filename (str): Имя файла.
            
        Returns:
            Dict[str, Any]: Результат.
        """
        filepath = self.maps_path / filename
        
        if not filepath.exists():
            return {
                "success": False,
                "error": f"Файл не найден: {filename}"
            }
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Загрузка точек
        self.map_points = [
            MapPoint(
                lat=p["lat"],
                lon=p["lon"],
                altitude=p.get("altitude", 0)
            )
            for p in data.get("points", [])
        ]
        
        return {
            "success": True,
            "points_count": len(self.map_points),
            "message": f"Загружено {len(self.map_points)} точек"
        }
    
    async def action_get_map_data(self) -> Dict[str, Any]:
        """Получение данных карты"""
        return {
            "success": True,
            "points": [
                {"lat": p.lat, "lon": p.lon, "altitude": p.altitude}
                for p in self.map_points
            ],
            "areas": {
                name: {
                    "type": area.area_type,
                    "points_count": len(area.points)
                }
                for name, area in self.map_areas.items()
            }
        }
    
    async def action_clear_map(self) -> Dict[str, Any]:
        """Очистка карты"""
        self.map_points.clear()
        self.map_areas.clear()
        
        return {
            "success": True,
            "message": "Карта очищена"
        }
    
    async def shutdown(self):
        """Завершение работы инструмента"""
        # Автосохранение
        if self.map_points:
            await self.action_save_map("autosave.json")
        
        logger.info(f"Инструмент {self.name} завершает работу")
        self.status = ToolStatus.SHUTDOWN
