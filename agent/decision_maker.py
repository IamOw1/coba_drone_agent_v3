"""
Модуль принятия решений агента
"""
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from utils.logger import setup_logger

logger = setup_logger(__name__)


class DecisionType(Enum):
    """Типы решений"""
    NAVIGATION = "navigation"
    SAFETY = "safety"
    MISSION = "mission"
    EMERGENCY = "emergency"
    LEARNING = "learning"


class DecisionMaker:
    """
    Движок принятия решений для ИИ-агента дрона.
    Использует комбинацию правил, деревьев поведения и ИИ.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация движка принятия решений.
        
        Args:
            config (Dict[str, Any]): Конфигурация агента.
        """
        self.config = config
        
        # Параметры принятия решений
        self.safety_threshold = config.get('safety', {}).get('threshold', 0.8)
        self.confidence_threshold = config.get('decision', {}).get('confidence_threshold', 0.7)
        
        # Иерархия решений
        self.decision_layers = {
            "reactive": 0,    # Мгновенные реакции
            "tactical": 1,    # Тактические решения
            "strategic": 2,   # Стратегические решения
            "learning": 3     # Обучение и адаптация
        }
        
        # Правила безопасности
        self.safety_rules = self._init_safety_rules()
        
        # Дерево поведения
        self.behavior_tree = self._build_behavior_tree()
        
        logger.info("Движок принятия решений инициализирован")
    
    def _init_safety_rules(self) -> List[Dict[str, Any]]:
        """Инициализация правил безопасности."""
        return [
            {
                "name": "low_battery",
                "condition": lambda telemetry: telemetry.get("battery", 100) < 20,
                "action": {"command": "RTL", "reason": "Низкий заряд батареи", "priority": "critical"},
                "priority": 100
            },
            {
                "name": "critical_battery",
                "condition": lambda telemetry: telemetry.get("battery", 100) < 10,
                "action": {"command": "LAND", "reason": "Критический заряд батареи", "priority": "critical"},
                "priority": 200
            },
            {
                "name": "signal_lost",
                "condition": lambda telemetry: telemetry.get("signal_strength", 100) < 20,
                "action": {"command": "RTL", "reason": "Потеря сигнала", "priority": "high"},
                "priority": 90
            },
            {
                "name": "high_wind",
                "condition": lambda telemetry: telemetry.get("wind_speed", 0) > 15,
                "action": {"command": "LAND", "reason": "Сильный ветер", "priority": "high"},
                "priority": 80
            },
            {
                "name": "obstacle_detected",
                "condition": lambda telemetry: telemetry.get("obstacle_distance", 100) < 5,
                "action": {"command": "HOVER", "reason": "Обнаружено препятствие", "priority": "high"},
                "priority": 85
            }
        ]
    
    def _build_behavior_tree(self) -> Dict[str, Any]:
        """Построение дерева поведения."""
        return {
            "root": {
                "type": "selector",
                "children": [
                    {
                        "type": "sequence",
                        "name": "emergency_check",
                        "children": [
                            {"type": "condition", "check": "is_emergency"},
                            {"type": "action", "name": "handle_emergency"}
                        ]
                    },
                    {
                        "type": "sequence",
                        "name": "mission_execution",
                        "children": [
                            {"type": "condition", "check": "has_active_mission"},
                            {"type": "action", "name": "execute_mission_step"}
                        ]
                    },
                    {
                        "type": "action",
                        "name": "idle_behavior"
                    }
                ]
            }
        }
    
    async def decide_mission(self, perception: Dict[str, Any], 
                            mission: Any) -> Dict[str, Any]:
        """
        Принятие решения в контексте миссии.
        
        Args:
            perception (Dict[str, Any]): Данные восприятия.
            mission (Any): Текущая миссия.
            
        Returns:
            Dict[str, Any]: Решение.
        """
        telemetry = perception.get("telemetry", {})
        
        # 1. Проверка правил безопасности (высший приоритет)
        safety_decision = self._check_safety_rules(telemetry)
        if safety_decision:
            logger.warning(f"Сработало правило безопасности: {safety_decision['reason']}")
            return safety_decision
        
        # 2. Проверка на препятствия
        if "obstacles" in perception:
            obstacle_decision = self._handle_obstacles(perception["obstacles"])
            if obstacle_decision:
                return obstacle_decision
        
        # 3. Навигация по миссии
        navigation_decision = await self._navigate_mission(perception, mission)
        if navigation_decision:
            return navigation_decision
        
        # 4. Резервное решение
        return {"command": "HOVER", "reason": "Ожидание команд", "priority": "low"}
    
    async def decide_free(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Принятие решения в режиме свободного полета.
        
        Args:
            perception (Dict[str, Any]): Данные восприятия.
            
        Returns:
            Dict[str, Any]: Решение.
        """
        telemetry = perception.get("telemetry", {})
        
        # Проверка правил безопасности
        safety_decision = self._check_safety_rules(telemetry)
        if safety_decision:
            return safety_decision
        
        # В режиме свободного полета - зависание
        return {"command": "HOVER", "reason": "Свободный полет", "priority": "low"}
    
    def _check_safety_rules(self, telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Проверка правил безопасности.
        
        Args:
            telemetry (Dict[str, Any]): Телеметрия.
            
        Returns:
            Optional[Dict[str, Any]]: Решение если сработало правило.
        """
        # Сортируем правила по приоритету
        sorted_rules = sorted(self.safety_rules, key=lambda r: r["priority"], reverse=True)
        
        for rule in sorted_rules:
            try:
                if rule["condition"](telemetry):
                    return rule["action"]
            except Exception as e:
                logger.error(f"Ошибка проверки правила {rule['name']}: {e}")
        
        return None
    
    def _handle_obstacles(self, obstacles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Обработка препятствий.
        
        Args:
            obstacles (List[Dict[str, Any]]): Список препятствий.
            
        Returns:
            Optional[Dict[str, Any]]: Решение по избеганию.
        """
        if not obstacles:
            return None
        
        # Находим ближайшее препятствие
        closest = min(obstacles, key=lambda o: o.get("distance", float('inf')))
        distance = closest.get("distance", 100)
        
        if distance < 3:  # Критическая дистанция
            return {
                "command": "LAND",
                "reason": f"Критически близкое препятствие на {distance}м",
                "priority": "critical"
            }
        elif distance < 10:  # Опасная дистанция
            # Вычисляем направление уклонения
            direction = self._calculate_avoidance_direction(closest)
            return {
                "command": "AVOID",
                "params": {
                    "direction": direction,
                    "distance": 15
                },
                "reason": f"Препятствие на {distance}м",
                "priority": "high"
            }
        
        return None
    
    def _calculate_avoidance_direction(self, obstacle: Dict[str, Any]) -> Dict[str, float]:
        """
        Вычисление направления уклонения от препятствия.
        
        Args:
            obstacle (Dict[str, Any]): Препятствие.
            
        Returns:
            Dict[str, float]: Направление уклонения.
        """
        obs_x = obstacle.get("x", 0)
        obs_y = obstacle.get("y", 0)
        obs_z = obstacle.get("z", 0)
        
        # Вектор от препятствия (противоположное направление)
        distance = (obs_x**2 + obs_y**2 + obs_z**2) ** 0.5
        
        if distance > 0:
            return {
                "x": -obs_x / distance,
                "y": -obs_y / distance,
                "z": 0  # Сохраняем высоту
            }
        
        return {"x": 1, "y": 0, "z": 0}
    
    async def _navigate_mission(self, perception: Dict[str, Any], 
                                mission: Any) -> Dict[str, Any]:
        """
        Навигация по миссии.
        
        Args:
            perception (Dict[str, Any]): Данные восприятия.
            mission (Any): Миссия.
            
        Returns:
            Dict[str, Any]: Навигационное решение.
        """
        telemetry = perception.get("telemetry", {})
        current_pos = telemetry.get("position", {"x": 0, "y": 0, "z": 0})
        
        # Получаем текущую целевую точку
        waypoints = mission.waypoints if hasattr(mission, 'waypoints') else mission.get("waypoints", [])
        
        if not waypoints:
            return {"command": "HOVER", "reason": "Нет точек маршрута", "priority": "low"}
        
        # Находим ближайшую невыполненную точку
        target = self._find_next_waypoint(current_pos, waypoints)
        
        if target is None:
            # Все точки выполнены
            return {"command": "RTL", "reason": "Миссия завершена", "priority": "medium"}
        
        # Вычисляем расстояние до цели
        distance = self._calculate_distance(current_pos, target)
        
        if distance < 2.0:  # Достигли точки
            return {
                "command": "WAYPOINT_REACHED",
                "params": {"waypoint": target},
                "reason": f"Достигнута точка {target}",
                "priority": "medium"
            }
        
        # Движение к точке
        speed = target.get("speed", 5.0)
        return {
            "command": "GOTO",
            "params": {
                "x": target.get("x", 0),
                "y": target.get("y", 0),
                "z": target.get("z", 10),
                "speed": speed
            },
            "reason": f"Движение к точке маршрута (расстояние: {distance:.1f}м)",
            "priority": "medium"
        }
    
    def _find_next_waypoint(self, current_pos: Dict[str, float], 
                           waypoints: List[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """
        Поиск следующей точки маршрута.
        
        Args:
            current_pos (Dict[str, float]): Текущая позиция.
            waypoints (List[Dict[str, float]]): Точки маршрута.
            
        Returns:
            Optional[Dict[str, float]]: Следующая точка или None.
        """
        for wp in waypoints:
            distance = self._calculate_distance(current_pos, wp)
            if distance > 2.0:  # Точка еще не достигнута
                return wp
        return None
    
    def _calculate_distance(self, pos1: Dict[str, float], 
                           pos2: Dict[str, float]) -> float:
        """
        Вычисление расстояния между точками.
        
        Args:
            pos1 (Dict[str, float]): Первая точка.
            pos2 (Dict[str, float]): Вторая точка.
            
        Returns:
            float: Расстояние в метрах.
        """
        dx = pos1.get("x", 0) - pos2.get("x", 0)
        dy = pos1.get("y", 0) - pos2.get("y", 0)
        dz = pos1.get("z", 0) - pos2.get("z", 0)
        return (dx**2 + dy**2 + dz**2) ** 0.5
    
    async def evaluate_decision(self, decision: Dict[str, Any], 
                                context: Dict[str, Any]) -> float:
        """
        Оценка качества решения.
        
        Args:
            decision (Dict[str, Any]): Решение.
            context (Dict[str, Any]): Контекст.
            
        Returns:
            float: Оценка качества (0-1).
        """
        score = 0.5  # Базовая оценка
        
        # Проверка безопасности
        if decision.get("priority") == "critical":
            score += 0.3
        elif decision.get("priority") == "high":
            score += 0.2
        
        # Проверка обоснования
        if decision.get("reason"):
            score += 0.1
        
        # Проверка параметров
        if decision.get("params"):
            score += 0.1
        
        return min(score, 1.0)
    
    def update_rules(self, new_rules: List[Dict[str, Any]]):
        """
        Обновление правил принятия решений.
        
        Args:
            new_rules (List[Dict[str, Any]]): Новые правила.
        """
        self.safety_rules.extend(new_rules)
        logger.info(f"Добавлено {len(new_rules)} новых правил")
    
    def get_decision_history(self) -> List[Dict[str, Any]]:
        """
        Получение истории решений.
        
        Returns:
            List[Dict[str, Any]]: История решений.
        """
        # В реальной реализации здесь был бы доступ к истории
        return []
