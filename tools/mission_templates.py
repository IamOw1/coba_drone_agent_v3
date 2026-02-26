"""
Расширенные шаблоны миссий для COBA AI Drone Agent
10+ готовых шаблонов для различных сценариев использования
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class MissionDifficulty(Enum):
    """Уровень сложности миссии"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass
class MissionTemplate:
    """Шаблон миссии"""
    template_id: str
    name: str
    description: str
    difficulty: MissionDifficulty
    estimated_duration_minutes: int
    required_battery_percent: float
    min_gps_satellites: int
    min_wind_speed_tolerance: float  # м/с
    objectives: List[str]
    default_parameters: Dict[str, Any]
    required_tools: List[str]
    safety_protocols: List[str]
    post_mission_actions: List[str]


class MissionTemplateLibrary:
    """Библиотека готовых шаблонов миссий"""
    
    def __init__(self):
        self.templates: Dict[str, MissionTemplate] = {}
        self._initialize_templates()
    
    def _initialize_templates(self) -> None:
        """Инициализировать все встроенные шаблоны"""
        
        # Шаблон 1: Простое зависание
        self.templates['simple_hover'] = MissionTemplate(
            template_id='simple_hover',
            name='Простое зависание',
            description='Базовая миссия: взлёт, зависание и посадка',
            difficulty=MissionDifficulty.EASY,
            estimated_duration_minutes=5,
            required_battery_percent=20,
            min_gps_satellites=6,
            min_wind_speed_tolerance=8.0,
            objectives=['hover', 'maintain_position'],
            default_parameters={
                'altitude': 10.0,
                'hover_duration_seconds': 180,
                'speed': 1.0
            },
            required_tools=['mifly'],
            safety_protocols=['geofence_enabled', 'low_battery_check', 'gps_validity'],
            post_mission_actions=['safe_landing', 'log_flight_data']
        )
        
        # Шаблон 2: Патруль территории
        self.templates['area_patrol'] = MissionTemplate(
            template_id='area_patrol',
            name='Патруль территории',
            description='Обход периметра территории с фотографированием',
            difficulty=MissionDifficulty.MEDIUM,
            estimated_duration_minutes=20,
            required_battery_percent=40,
            min_gps_satellites=10,
            min_wind_speed_tolerance=6.0,
            objectives=['patrol_area', 'capture_photos', 'monitor_perimeter'],
            default_parameters={
                'altitude': 30.0,
                'speed': 8.0,
                'photo_interval_seconds': 10,
                'overlap_percent': 30,
                'area_size': '500x500'  # метры
            },
            required_tools=['mifly', 'object_detection', 'geomap'],
            safety_protocols=['geofence_enabled', 'obstacle_avoidance', 'rth_on_signal_loss'],
            post_mission_actions=['generate_map', 'analyze_detections', 'create_report']
        )
        
        # Шаблон 3: Картографирование местности
        self.templates['terrain_mapping'] = MissionTemplate(
            template_id='terrain_mapping',
            name='Картографирование местности',
            description='Детальное картографирование заданной области',
            difficulty=MissionDifficulty.HARD,
            estimated_duration_minutes=45,
            required_battery_percent=60,
            min_gps_satellites=12,
            min_wind_speed_tolerance=5.0,
            objectives=['create_orthomosaic', 'generate_dem', 'map_terrain'],
            default_parameters={
                'altitude': 50.0,
                'speed': 10.0,
                'photo_interval_gps_distance': 5.0,  # метры
                'camer_overlap_forward': 80,
                'camera_overlap_side': 60,
                'grid_pattern': 'lawnmower'
            },
            required_tools=['geomap', 'mifly', 'mission_planner'],
            safety_protocols=['continuous_gps_check', 'wind_monitoring', 'altitude_keepout'],
            post_mission_actions=['process_orthomosaic', 'generate_elevation_model', 'quality_check']
        )
        
        # Шаблон 4: Поиск объектов
        self.templates['object_search'] = MissionTemplate(
            template_id='object_search',
            name='Поиск объектов',
            description='Обнаружение и классификация объектов в зоне поиска',
            difficulty=MissionDifficulty.HARD,
            estimated_duration_minutes=30,
            required_battery_percent=50,
            min_gps_satellites=10,
            min_wind_speed_tolerance=5.0,
            objectives=['search_objects', 'classify_objects', 'locate_targets'],
            default_parameters={
                'altitude': 40.0,
                'speed': 5.0,
                'search_pattern': 'spiral',
                'object_types': ['vehicle', 'person', 'structure'],
                'confidence_threshold': 0.85
            },
            required_tools=['object_detection', 'geomap', 'slom'],
            safety_protocols=['no_fly_zone_check', 'privacy_compliance', 'collision_avoidance'],
            post_mission_actions=['compile_detections', 'create_heatmap', 'generate_summary']
        )
        
        # Шаблон 5: Инспекция инфраструктуры
        self.templates['infrastructure_inspection'] = MissionTemplate(
            template_id='infrastructure_inspection',
            name='Инспекция инфраструктуры',
            description='Видеоинспекция мостов, линий электропередачи, антенн и т.д.',
            difficulty=MissionDifficulty.HARD,
            estimated_duration_minutes=40,
            required_battery_percent=55,
            min_gps_satellites=10,
            min_wind_speed_tolerance=4.0,  # Требует меньше ветра
            objectives=['video_inspection', 'close_range_imaging', 'damage_assessment'],
            default_parameters={
                'altitude': 30.0,  # Ближе для деталей
                'speed': 3.0,  # Медленнее
                'gimbal_control': 'active',
                'thermal_imaging': True,
                'video_resolution': '4k'
            },
            required_tools=['mifly', 'object_detection', 'precision_landing'],
            safety_protocols=['distance_keepout', 'manual_control_ready', 'emergency_return'],
            post_mission_actions=['extract_thermal_data', 'mark_anomalies', 'create_video']
        )
        
        # Шаблон 6: Точная посадка
        self.templates['precision_landing'] = MissionTemplate(
            template_id='precision_landing',
            name='Точная посадка',
            description='Посадка с использованием визуальных маркеров (ArUco)',
            difficulty=MissionDifficulty.HARD,
            estimated_duration_minutes=10,
            required_battery_percent=25,
            min_gps_satellites=8,
            min_wind_speed_tolerance=3.0,
            objectives=['visual_landing', 'precision_docking', 'autonomous_landing'],
            default_parameters={
                'approach_altitude': 15.0,
                'marker_type': 'aruco',
                'marker_size_cm': 50,
                'landing_precision_cm': 30
            },
            required_tools=['precision_landing', 'mifly', 'object_detection'],
            safety_protocols=['marker_detection_check', 'low_altitude_landing', 'manual_override'],
            post_mission_actions=['log_landing_precision', 'dock_if_available']
        )
        
        # Шаблон 7: Доставка грузов
        self.templates['cargo_delivery'] = MissionTemplate(
            template_id='cargo_delivery',
            name='Доставка грузов',
            description='Автономная доставка посылки от точки A к точке B',
            difficulty=MissionDifficulty.EXPERT,
            estimated_duration_minutes=25,
            required_battery_percent=55,
            min_gps_satellites=12,
            min_wind_speed_tolerance=5.0,
            objectives=['load_cargo', 'navigate_to_destination', 'deliver_cargo'],
            default_parameters={
                'altitude': 30.0,
                'speed': 12.0,
                'payload_weight_kg': 0.5,
                'delivery_point_precision_meters': 20,
                'return_route': 'optimized'
            },
            required_tools=['logistics', 'mifly', 'geomap', 'autonomous_flight'],
            safety_protocols=['weight_check', 'route_safety', 'low_battery_rth'],
            post_mission_actions=['confirm_delivery', 'log_location', 'return_home']
        )
        
        # Шаблон 8: Роевые операции
        self.templates['swarm_mission'] = MissionTemplate(
            template_id='swarm_mission',
            name='Роевая операция',
            description='Координированная операция несколько дронов',
            difficulty=MissionDifficulty.EXPERT,
            estimated_duration_minutes=30,
            required_battery_percent=60,
            min_gps_satellites=12,
            min_wind_speed_tolerance=4.0,
            objectives=['swarm_coordination', 'distributed_task', 'formation_flight'],
            default_parameters={
                'swarm_size': 5,
                'formation': 'v_shape',
                'altitude': 40.0,
                'speed': 10.0,
                'inter_drone_distance_meters': 20,
                'communication_latency_ms': 100
            },
            required_tools=['amorfus', 'mifly', 'deployment_manager'],
            safety_protocols=['swarm_safety', 'collision_avoidance', 'leader_election'],
            post_mission_actions=['disband_formation', 'verify_all_safe', 'sync_logs']
        )
        
        # Шаблон 9: Мониторинг отдельных мест
        self.templates['spottarget_monitoring'] = MissionTemplate(
            template_id='target_monitoring',
            name='Мониторинг целевой точки',
            description='Повторяемое наблюдение за целевой точкой',
            difficulty=MissionDifficulty.MEDIUM,
            estimated_duration_minutes=15,
            required_battery_percent=35,
            min_gps_satellites=10,
            min_wind_speed_tolerance=6.0,
            objectives=['monitor_target', 'track_changes', 'collect_data'],
            default_parameters={
                'altitude': 25.0,
                'orbit_radius_meters': 50,
                'orbit_speed': 5.0,
                'monitoring_duration_minutes': 10,
                'camera_gimbal': 'downward'
            },
            required_tools=['object_detection', 'autonomous_flight'],
            safety_protocols=['target_in_range', 'radius_keepout', 'emergency_exit'],
            post_mission_actions=['analyze_changes', 'flag_anomalies', 'store_baseline']
        )
        
        # Шаблон 10: Ночные операции
        self.templates['night_operations'] = MissionTemplate(
            template_id='night_operations',
            name='Ночные операции',
            description='Ночной полёт с использованием тепловизора',
            difficulty=MissionDifficulty.EXPERT,
            estimated_duration_minutes=20,
            required_battery_percent=50,
            min_gps_satellites=10,
            min_wind_speed_tolerance=4.0,
            objectives=['thermal_imaging', 'night_navigation', 'detect_heat_sources'],
            default_parameters={
                'altitude': 30.0,
                'speed': 8.0,
                'camera_mode': 'thermal',
                'led_brightness': 'low',
                'navigation_mode': 'gps_inertial'
            },
            required_tools=['object_detection', 'mifly', 'autonomous_flight'],
            safety_protocols=['no_visible_light', 'gps_integrity', 'battery_critical'],
            post_mission_actions=['analyze_thermal', 'generate_heatmap', 'log_environment']
        )
        
        # Шаблон 11: Видеомониторинг события
        self.templates['event_video_coverage'] = MissionTemplate(
            template_id='event_video_coverage',
            name='Видеомониторинг события',
            description='Видеозапись события с несколькими ракурсами',
            difficulty=MissionDifficulty.MEDIUM,
            estimated_duration_minutes=35,
            required_battery_percent=50,
            min_gps_satellites=10,
            min_wind_speed_tolerance=6.0,
            objectives=['record_event', 'multi_angle_coverage', 'live_feed'],
            default_parameters={
                'altitude': 30.0,
                'loiter_points': 4,
                'video_resolution': '4k',
                'bitrate_mbps': 25,
                'live_streaming': True,
                'recording_format': 'h265'
            },
            required_tools=['mifly', 'mission_planner'],
            safety_protocols=['bandwidth_check', 'storage_check', 'weather_monitoring'],
            post_mission_actions=['upload_footage', 'create_edit_list', 'generate_highlights']
        )
        
        logger.info(f"Инициализировано {len(self.templates)} шаблонов миссий")
    
    def get_template(self, template_id: str) -> Optional[MissionTemplate]:
        """Получить шаблон по ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_difficulty(self, difficulty: MissionDifficulty) -> List[MissionTemplate]:
        """Получить шаблоны по уровню сложности"""
        return [t for t in self.templates.values() if t.difficulty == difficulty]
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Получить список всех доступных шаблонов"""
        return [
            {
                'template_id': t.template_id,
                'name': t.name,
                'description': t.description,
                'difficulty': t.difficulty.value,
                'estimated_duration_minutes': t.estimated_duration_minutes,
                'required_tools': t.required_tools,
                'objectives': t.objectives
            }
            for t in self.templates.values()
        ]
    
    def create_mission_from_template(self, template_id: str, 
                                    custom_parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Создать миссию на основе шаблона"""
        
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Шаблон '{template_id}' не найден")
        
        # Создать миссию
        mission = {
            'mission_id': f"{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'mission_name': template.name,
            'mission_type': template_id,
            'difficulty': template.difficulty.value,
            'objectives': template.objectives,
            'estimated_duration_minutes': template.estimated_duration_minutes,
            'required_battery_percent': template.required_battery_percent,
            'parameters': template.default_parameters.copy(),
            'required_tools': template.required_tools,
            'safety_protocols': template.safety_protocols,
            'post_mission_actions': template.post_mission_actions
        }
        
        # Применить собственные параметры если предоставлены
        if custom_parameters:
            mission['parameters'].update(custom_parameters)
        
        return mission
