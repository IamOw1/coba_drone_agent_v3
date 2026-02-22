"""
Amorfus - Инструмент роевого интеллекта для управления группой дронов
"""
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from tools.base_tool import BaseTool, ToolStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DroneState:
    """Состояние дрона в рое"""
    drone_id: int
    position: np.ndarray
    velocity: np.ndarray
    heading: float
    connected: bool = True
    battery: float = 100.0


class AmorfusTool(BaseTool):
    """
    Инструмент роевого интеллекта для координации группы дронов.
    Реализует алгоритмы роевого поведения: Вичека, Boids, консенсус.
    """
    
    def __init__(self, config: Dict[str, Any], agent=None):
        super().__init__(config, agent)
        self.name = "amorfus"
        self.description = "Роевой интеллект для координации группы дронов"
        self.version = "2.0.0"
        
        # Параметры роя
        swarm_config = config.get('swarm', {})
        self.swarm_size = swarm_config.get('size', 5)
        self.consensus_algorithm = swarm_config.get('consensus_algorithm', 'vicsek')
        self.communication_range = swarm_config.get('communication_range', 50.0)
        
        # Параметры поведения
        self.separation_weight = swarm_config.get('separation_weight', 1.5)
        self.alignment_weight = swarm_config.get('alignment_weight', 1.0)
        self.cohesion_weight = swarm_config.get('cohesion_weight', 1.0)
        
        # Состояние роя
        self.swarm_state: Dict[int, DroneState] = {}
        self.formation = "line"  # line, circle, pyramid, v_shape
        self.leader_id = 0
        
        # Цель роя
        self.swarm_target = None
        
        logger.info(f"Amorfus инициализирован. Размер роя: {self.swarm_size}")
    
    async def initialize(self):
        """Инициализация роя"""
        for i in range(self.swarm_size):
            self.swarm_state[i] = DroneState(
                drone_id=i,
                position=np.array([i * 5.0, 0.0, 10.0]),
                velocity=np.array([0.0, 0.0, 0.0]),
                heading=0.0,
                connected=True,
                battery=100.0
            )
        
        self.status = ToolStatus.READY
        logger.info(f"Роевой интеллект инициализирован для {self.swarm_size} дронов")
    
    async def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применение роевого интеллекта.
        
        Args:
            data (Dict[str, Any]): Данные телеметрии от дронов.
            
        Returns:
            Dict[str, Any]: Команды для дронов.
        """
        # Обновление состояния роя
        self._update_swarm_state(data)
        
        # Применение алгоритма консенсуса
        if self.consensus_algorithm == 'vicsek':
            commands = await self._vicsek_model()
        elif self.consensus_algorithm == 'boids':
            commands = await self._boids_model()
        else:
            commands = await self._basic_consensus()
        
        # Применение строя
        if self.formation != "free":
            formation_commands = await self._apply_formation(self.formation)
            commands = self._merge_commands(commands, formation_commands)
        
        # Обход препятствий
        if 'obstacles' in data:
            avoidance_commands = await self._collective_obstacle_avoidance(data['obstacles'])
            commands = self._merge_commands(commands, avoidance_commands)
        
        return commands
    
    def _update_swarm_state(self, data: Dict[str, Any]):
        """Обновление состояния роя"""
        swarm_telemetry = data.get('swarm_telemetry', {})
        
        for drone_id, telemetry in swarm_telemetry.items():
            drone_id = int(drone_id)
            if drone_id in self.swarm_state:
                state = self.swarm_state[drone_id]
                state.position = np.array([
                    telemetry.get('x', 0.0),
                    telemetry.get('y', 0.0),
                    telemetry.get('z', 0.0)
                ])
                state.velocity = np.array([
                    telemetry.get('vx', 0.0),
                    telemetry.get('vy', 0.0),
                    telemetry.get('vz', 0.0)
                ])
                state.battery = telemetry.get('battery', 100.0)
                state.connected = telemetry.get('connected', True)
    
    async def _vicsek_model(self) -> Dict[int, Dict[str, Any]]:
        """
        Модель Вичека для роевого интеллекта.
        Дроны выравнивают свою скорость со средней скоростью соседей.
        
        Returns:
            Dict[int, Dict[str, Any]]: Команды для каждого дрона.
        """
        commands = {}
        
        for drone_id, state in self.swarm_state.items():
            if not state.connected:
                continue
            
            # Находим соседей в радиусе связи
            neighbors = self._get_neighbors(drone_id)
            
            if neighbors:
                # Средняя скорость соседей
                avg_velocity = np.mean([n.velocity for n in neighbors], axis=0)
                
                # Добавляем небольшой шум для реалистичности
                noise = np.random.normal(0, 0.1, 3)
                new_velocity = avg_velocity + noise
                
                # Нормализация скорости
                speed = np.linalg.norm(new_velocity)
                if speed > 0:
                    max_speed = 5.0  # максимальная скорость 5 м/с
                    new_velocity = (new_velocity / speed) * min(speed, max_speed)
            else:
                # Если соседей нет, сохраняем текущую скорость
                new_velocity = state.velocity
            
            commands[drone_id] = {
                "command": "set_velocity",
                "params": {
                    "vx": float(new_velocity[0]),
                    "vy": float(new_velocity[1]),
                    "vz": float(new_velocity[2])
                }
            }
        
        return commands
    
    async def _boids_model(self) -> Dict[int, Dict[str, Any]]:
        """
        Модель Boids (separation, alignment, cohesion).
        
        Returns:
            Dict[int, Dict[str, Any]]: Команды для каждого дрона.
        """
        commands = {}
        
        for drone_id, state in self.swarm_state.items():
            if not state.connected:
                continue
            
            neighbors = self._get_neighbors(drone_id)
            
            if not neighbors:
                continue
            
            # Separation (избегание столкновений)
            separation = self._calculate_separation(state, neighbors)
            
            # Alignment (выравнивание скорости)
            alignment = self._calculate_alignment(state, neighbors)
            
            # Cohesion (стремление к центру группы)
            cohesion = self._calculate_cohesion(state, neighbors)
            
            # Комбинирование правил
            new_velocity = (
                self.separation_weight * separation +
                self.alignment_weight * alignment +
                self.cohesion_weight * cohesion
            )
            
            # Нормализация
            speed = np.linalg.norm(new_velocity)
            if speed > 0:
                max_speed = 5.0
                new_velocity = (new_velocity / speed) * min(speed, max_speed)
            
            commands[drone_id] = {
                "command": "set_velocity",
                "params": {
                    "vx": float(new_velocity[0]),
                    "vy": float(new_velocity[1]),
                    "vz": float(new_velocity[2])
                }
            }
        
        return commands
    
    def _get_neighbors(self, drone_id: int) -> List[DroneState]:
        """Получение соседей дрона в радиусе связи"""
        state = self.swarm_state[drone_id]
        neighbors = []
        
        for other_id, other_state in self.swarm_state.items():
            if other_id != drone_id and other_state.connected:
                distance = np.linalg.norm(state.position - other_state.position)
                if distance <= self.communication_range:
                    neighbors.append(other_state)
        
        return neighbors
    
    def _calculate_separation(self, state: DroneState, 
                             neighbors: List[DroneState]) -> np.ndarray:
        """Вычисление вектора разделения"""
        separation = np.array([0.0, 0.0, 0.0])
        
        for neighbor in neighbors:
            diff = state.position - neighbor.position
            distance = np.linalg.norm(diff)
            if distance > 0 and distance < 10:  # минимальная дистанция 10м
                separation += diff / (distance ** 2)
        
        return separation
    
    def _calculate_alignment(self, state: DroneState, 
                            neighbors: List[DroneState]) -> np.ndarray:
        """Вычисление вектора выравнивания"""
        avg_velocity = np.mean([n.velocity for n in neighbors], axis=0)
        return avg_velocity - state.velocity
    
    def _calculate_cohesion(self, state: DroneState, 
                           neighbors: List[DroneState]) -> np.ndarray:
        """Вычисление вектора сплочения"""
        center = np.mean([n.position for n in neighbors], axis=0)
        return center - state.position
    
    async def _basic_consensus(self) -> Dict[int, Dict[str, Any]]:
        """Базовый алгоритм консенсуса"""
        commands = {}
        
        # Находим центр роя
        center = np.mean([s.position for s in self.swarm_state.values() if s.connected], axis=0)
        
        for drone_id, state in self.swarm_state.items():
            if not state.connected:
                continue
            
            # Движение к центру
            direction = center - state.position
            distance = np.linalg.norm(direction)
            
            if distance > 0:
                direction = direction / distance
                speed = min(distance * 0.5, 3.0)  # пропорционально расстоянию
                velocity = direction * speed
            else:
                velocity = np.array([0.0, 0.0, 0.0])
            
            commands[drone_id] = {
                "command": "set_velocity",
                "params": {
                    "vx": float(velocity[0]),
                    "vy": float(velocity[1]),
                    "vz": float(velocity[2])
                }
            }
        
        return commands
    
    async def _apply_formation(self, formation: str) -> Dict[int, Dict[str, Any]]:
        """
        Применение строя к рою.
        
        Args:
            formation (str): Тип строя.
            
        Returns:
            Dict[int, Dict[str, Any]]: Команды для построения.
        """
        commands = {}
        
        # Центр строя (позиция лидера)
        leader = self.swarm_state.get(self.leader_id)
        if leader:
            center = leader.position
        else:
            center = np.array([0.0, 0.0, 10.0])
        
        for drone_id, state in self.swarm_state.items():
            if drone_id == self.leader_id:
                continue  # Лидер не меняет позицию
            
            if formation == "line":
                # Линия вдоль оси X
                target_position = center + np.array([(drone_id - self.leader_id) * 5.0, 0.0, 0.0])
            
            elif formation == "circle":
                # Круг радиусом 10 метров
                angle = 2 * np.pi * (drone_id - self.leader_id) / (self.swarm_size - 1)
                target_position = center + np.array([10.0 * np.cos(angle), 10.0 * np.sin(angle), 0.0])
            
            elif formation == "pyramid":
                # Пирамида
                level = (drone_id - self.leader_id) // 3
                offset = (drone_id - self.leader_id) % 3
                target_position = center + np.array([offset * 4.0 - 4.0, level * 4.0, -level * 2.0])
            
            elif formation == "v_shape":
                # V-образное построение
                offset = drone_id - self.leader_id
                side = 1 if offset > 0 else -1
                target_position = center + np.array([abs(offset) * 5.0, side * abs(offset) * 3.0, 0.0])
            
            else:
                target_position = center
            
            # Вычисляем направление к целевой позиции
            direction = target_position - state.position
            distance = np.linalg.norm(direction)
            
            if distance > 1.0:
                direction = direction / distance
                velocity = direction * min(distance * 0.5, 3.0)
            else:
                velocity = np.array([0.0, 0.0, 0.0])
            
            commands[drone_id] = {
                "command": "set_velocity",
                "params": {
                    "vx": float(velocity[0]),
                    "vy": float(velocity[1]),
                    "vz": float(velocity[2])
                }
            }
        
        return commands
    
    async def _collective_obstacle_avoidance(self, 
                                             obstacles: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Коллективное избегание препятствий.
        
        Args:
            obstacles (List[Dict[str, Any]]): Список препятствий.
            
        Returns:
            Dict[int, Dict[str, Any]]: Команды для избегания.
        """
        commands = {}
        
        for drone_id, state in self.swarm_state.items():
            if not state.connected:
                continue
            
            avoidance_vector = np.array([0.0, 0.0, 0.0])
            
            for obstacle in obstacles:
                obs_pos = np.array([
                    obstacle.get('x', 0),
                    obstacle.get('y', 0),
                    obstacle.get('z', 0)
                ])
                distance = np.linalg.norm(state.position - obs_pos)
                radius = obstacle.get('radius', 5.0)
                
                if distance < radius + 5.0:  # зона опасности
                    # Вектор отталкивания
                    direction = state.position - obs_pos
                    if np.linalg.norm(direction) > 0:
                        direction = direction / np.linalg.norm(direction)
                        # Сила отталкивания обратно пропорциональна расстоянию
                        force = (radius + 5.0 - distance) / (radius + 5.0)
                        avoidance_vector += direction * force * 5.0
            
            if np.linalg.norm(avoidance_vector) > 0:
                commands[drone_id] = {
                    "command": "adjust_velocity",
                    "params": {
                        "vx": float(avoidance_vector[0]),
                        "vy": float(avoidance_vector[1]),
                        "vz": float(avoidance_vector[2])
                    }
                }
        
        return commands
    
    def _merge_commands(self, commands1: Dict, commands2: Dict) -> Dict:
        """Объединение двух наборов команд"""
        merged = commands1.copy()
        
        for drone_id, cmd in commands2.items():
            if drone_id in merged:
                # Приоритет у команд избегания препятствий
                if cmd.get('command') == 'adjust_velocity':
                    # Суммируем векторы скоростей
                    existing = merged[drone_id]
                    if existing.get('command') in ['set_velocity', 'adjust_velocity']:
                        existing_params = existing.get('params', {})
                        new_params = cmd.get('params', {})
                        merged[drone_id] = {
                            "command": "set_velocity",
                            "params": {
                                "vx": existing_params.get('vx', 0) + new_params.get('vx', 0),
                                "vy": existing_params.get('vy', 0) + new_params.get('vy', 0),
                                "vz": existing_params.get('vz', 0) + new_params.get('vz', 0)
                            }
                        }
            else:
                merged[drone_id] = cmd
        
        return merged
    
    async def action_set_formation(self, formation: str) -> Dict[str, Any]:
        """Установка строя роя"""
        valid_formations = ["line", "circle", "pyramid", "v_shape", "free"]
        
        if formation not in valid_formations:
            return {
                "success": False,
                "error": f"Неверный тип строя. Доступные: {valid_formations}"
            }
        
        self.formation = formation
        logger.info(f"Установлено строе: {formation}")
        
        return {
            "success": True,
            "formation": formation,
            "swarm_size": self.swarm_size
        }
    
    async def action_set_target(self, x: float, y: float, z: float) -> Dict[str, Any]:
        """Установка целевой точки для роя"""
        self.swarm_target = np.array([x, y, z])
        
        return {
            "success": True,
            "target": {"x": x, "y": y, "z": z}
        }
    
    async def action_set_leader(self, drone_id: int) -> Dict[str, Any]:
        """Установка лидера роя"""
        if drone_id not in self.swarm_state:
            return {
                "success": False,
                "error": f"Дрон {drone_id} не найден в рое"
            }
        
        self.leader_id = drone_id
        
        return {
            "success": True,
            "leader_id": drone_id
        }
    
    async def action_get_swarm_status(self) -> Dict[str, Any]:
        """Получение статуса роя"""
        connected_count = sum(1 for s in self.swarm_state.values() if s.connected)
        
        return {
            "success": True,
            "swarm_size": self.swarm_size,
            "connected": connected_count,
            "formation": self.formation,
            "leader_id": self.leader_id,
            "consensus_algorithm": self.consensus_algorithm,
            "drones": [
                {
                    "id": s.drone_id,
                    "connected": s.connected,
                    "battery": s.battery,
                    "position": s.position.tolist()
                }
                for s in self.swarm_state.values()
            ]
        }
    
    async def shutdown(self):
        """Завершение работы инструмента"""
        logger.info(f"Инструмент {self.name} завершает работу")
        self.swarm_state.clear()
        self.status = ToolStatus.SHUTDOWN
