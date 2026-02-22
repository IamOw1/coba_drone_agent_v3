"""
Ядро ИИ-агента для управления дроном
"""
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from agent.memory import ShortTermMemory, LongTermMemory
from agent.decision_maker import DecisionMaker
from agent.learner import Learner
from agent.sub_agent import SubAgent
from tools.base_tool import BaseTool
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentState(Enum):
    """Состояния агента"""
    INITIALIZING = "initializing"
    READY = "ready"
    FLYING = "flying"
    LANDING = "landing"
    EMERGENCY = "emergency"
    LEARNING = "learning"
    UPDATING = "updating"
    SHUTDOWN = "shutdown"


@dataclass
class MissionParams:
    """Параметры миссии"""
    name: str
    mission_id: str
    waypoints: List[Dict[str, float]]
    altitude: float = 50.0
    speed: float = 10.0
    max_distance: float = 5000.0
    emergency_protocols: Dict[str, Any] = field(default_factory=dict)
    data_collection: bool = True
    learning_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mission_id": self.mission_id,
            "waypoints": self.waypoints,
            "altitude": self.altitude,
            "speed": self.speed,
            "max_distance": self.max_distance,
            "emergency_protocols": self.emergency_protocols,
            "data_collection": self.data_collection,
            "learning_enabled": self.learning_enabled
        }


class DroneIntelligentAgent:
    """
    Основной класс интеллектуального агента для управления дроном.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Инициализация агента.
        
        Args:
            config_path (str): Путь к файлу конфигурации.
        """
        self.config = self._load_config(config_path)
        self.agent_id = self.config.get('agent_id', 'drone_agent_1')
        self.state = AgentState.INITIALIZING
        
        # Инициализация компонентов
        self.short_term_memory = ShortTermMemory(capacity=1000)
        self.long_term_memory = LongTermMemory(storage_path="data/memory/knowledge_base.db")
        self.decision_maker = DecisionMaker(self.config)
        self.learner = Learner(self.config)
        self.sub_agent = SubAgent(self.config, main_agent=self)
        
        # Клиенты симуляторов
        self.sim_mode = self.config.get('simulation', {}).get('enabled', False)
        self.sim_client = None
        self.real_drone_client = None
        
        # Реестр инструментов
        self.tools: Dict[str, BaseTool] = {}
        self._load_tools()
        
        # Телеметрия
        self.telemetry = {
            "position": {"x": 0, "y": 0, "z": 0},
            "velocity": {"vx": 0, "vy": 0, "vz": 0},
            "attitude": {"roll": 0, "pitch": 0, "yaw": 0},
            "battery": 100.0,
            "signal_strength": 100,
            "gps_status": "3D_FIX",
            "temperature": 25.0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Система событий
        self.event_bus = asyncio.Queue()
        self.command_queue = asyncio.Queue()
        
        # Текущая миссия
        self.current_mission: Optional[MissionParams] = None
        self.mission_history: List[Dict] = []
        
        logger.info(f"Агент {self.agent_id} инициализирован. Режим: {'симуляция' if self.sim_mode else 'реальный дрон'}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации."""
        import yaml
        import os
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Замена переменных окружения
            for key, value in config.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    config[key] = os.getenv(env_var, value)
            
            return config
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return {}
    
    def _load_tools(self):
        """Динамическая загрузка инструментов."""
        tool_configs = self.config.get('tools', [])
        for tool_config in tool_configs:
            try:
                module_path = f"tools.{tool_config['module']}"
                class_name = tool_config['class']
                module = __import__(module_path, fromlist=[class_name])
                tool_class = getattr(module, class_name)
                tool = tool_class(self.config, agent=self)
                self.tools[tool.name] = tool
                logger.info(f"Загружен инструмент: {tool.name}")
            except Exception as e:
                logger.error(f"Не удалось загрузить инструмент {tool_config}: {e}")
    
    async def initialize(self):
        """
        Полная инициализация агента и подключение к дрону.
        """
        logger.info("Начало инициализации агента...")
        
        # Подключение к симулятору или реальному дрону
        if self.sim_mode:
            from sim.airsim_client import AirSimClient
            self.sim_client = AirSimClient(self.config)
            await self.sim_client.connect()
            logger.info("Подключено к симулятору AirSim")
        else:
            from hardware.mavlink_handler import MAVLinkHandler
            self.real_drone_client = MAVLinkHandler(self.config)
            await self.real_drone_client.connect()
            logger.info("Подключено к реальному дрону через MAVLink")
        
        # Инициализация инструментов
        for tool in self.tools.values():
            await tool.initialize()
        
        # Инициализация субагента
        await self.sub_agent.initialize()
        
        # Загрузка сохраненного состояния
        await self.load_state()
        
        # Проверка всех систем
        await self._system_check()
        
        self.state = AgentState.READY
        logger.info("Агент готов к работе.")
        return True
    
    async def _system_check(self):
        """Проверка всех систем."""
        checks = []
        
        # Проверка связи
        if self.sim_client or self.real_drone_client:
            connection_ok = await self._check_connection()
            checks.append(("connection", connection_ok))
        
        # Проверка инструментов
        for name, tool in self.tools.items():
            try:
                tool_ok = await tool.health_check()
                checks.append((f"tool_{name}", tool_ok))
            except:
                checks.append((f"tool_{name}", False))
        
        # Проверка памяти
        memory_ok = self.short_term_memory is not None and self.long_term_memory is not None
        checks.append(("memory", memory_ok))
        
        failed = [name for name, ok in checks if not ok]
        if failed:
            logger.warning(f"Следующие системы требуют внимания: {failed}")
        
        return all(ok for _, ok in checks)
    
    async def _check_connection(self) -> bool:
        """Проверка подключения."""
        try:
            if self.sim_client:
                return await self.sim_client.is_connected()
            elif self.real_drone_client:
                return await self.real_drone_client.is_connected()
            return False
        except:
            return False
    
    async def perceive(self) -> Dict[str, Any]:
        """
        Сбор данных с датчиков дрона.
        
        Returns:
            Dict[str, Any]: Данные телеметрии и сенсоров.
        """
        perception = {}
        
        try:
            # Получение телеметрии
            if self.sim_client:
                perception["telemetry"] = await self.sim_client.get_telemetry()
            elif self.real_drone_client:
                perception["telemetry"] = await self.real_drone_client.get_telemetry()
            
            # Данные с инструментов
            perception["tools"] = {}
            for name, tool in self.tools.items():
                try:
                    tool_data = await tool.perceive()
                    perception["tools"][name] = tool_data
                except Exception as e:
                    logger.error(f"Ошибка восприятия инструмента {name}: {e}")
            
            # Обновление телеметрии агента
            self.telemetry.update(perception.get("telemetry", {}))
            self.telemetry["timestamp"] = datetime.now().isoformat()
            
            # Сохранение в краткосрочную память
            self.short_term_memory.add(perception)
            
            return perception
        except Exception as e:
            logger.error(f"Ошибка восприятия: {e}")
            return {}
    
    async def decide(self, perception_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Принятие решений на основе данных восприятия.
        
        Args:
            perception_data (Dict[str, Any]): Данные с датчиков.
            
        Returns:
            Dict[str, Any]: Решение (команда для дрона).
        """
        try:
            # Обновление состояния агента
            self.telemetry.update({
                "position": perception_data.get("position", self.telemetry["position"]),
                "velocity": perception_data.get("velocity", self.telemetry["velocity"]),
                "battery": perception_data.get("battery", self.telemetry["battery"])
            })
            
            # Проверка на аварийные ситуации через инструмент Slom
            if "slom" in self.tools:
                emergency = await self.tools["slom"].check_emergency(perception_data)
                if emergency:
                    logger.warning(f"Обнаружена аварийная ситуация: {emergency}")
                    return {"command": "RTL", "reason": emergency, "priority": "high"}
            
            # Проверка на экстренные ситуации
            emergency = await self._check_emergency(perception_data)
            if emergency:
                return await self._handle_emergency(emergency)
            
            # Получение текущей миссии
            if self.current_mission:
                decision = await self.decision_maker.decide_mission(perception_data, self.current_mission)
            else:
                decision = await self.decision_maker.decide_free(perception_data)
            
            # Консультация с субагентом
            if self.config.get('sub_agent', {}).get('enabled', False):
                sub_agent_advice = await self.sub_agent.review_decision(decision, perception_data)
                if sub_agent_advice.get("suggest_change", False):
                    decision = self._merge_decisions(decision, sub_agent_advice)
            
            return decision
        except Exception as e:
            logger.error(f"Ошибка принятия решения: {e}")
            return await self._fallback_decision()
    
    async def _check_emergency(self, perception: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Проверка на экстренные ситуации."""
        # Проверка низкого заряда батареи
        battery = perception.get("telemetry", {}).get("battery", 100)
        if battery < 20:
            return {"type": "low_battery", "severity": "high", "data": {"battery": battery}}
        
        # Проверка потери сигнала
        signal = perception.get("telemetry", {}).get("signal_strength", 100)
        if signal < 30:
            return {"type": "signal_lost", "severity": "high", "data": {"signal": signal}}
        
        return None
    
    async def _handle_emergency(self, emergency: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка экстренной ситуации."""
        emergency_type = emergency["type"]
        
        if emergency_type == "low_battery":
            return {"command": "RTL", "reason": "Низкий заряд батареи", "priority": "high"}
        elif emergency_type == "signal_lost":
            return {"command": "RTL", "reason": "Потеря сигнала", "priority": "high"}
        
        return {"command": "LAND", "reason": "Неизвестная аварийная ситуация", "priority": "high"}
    
    async def _fallback_decision(self) -> Dict[str, Any]:
        """Резервное решение при ошибке."""
        return {"command": "HOVER", "reason": "Резервный режим", "priority": "medium"}
    
    async def act(self, decision: Dict[str, Any]):
        """
        Выполнение решения (отправка команд дрону).
        
        Args:
            decision (Dict[str, Any]): Решение (команда).
        """
        command = decision.get("command")
        params = decision.get("params", {})
        
        logger.info(f"Выполнение команды: {command} с параметрами: {params}")
        
        try:
            # Отправка команды дрону
            if self.sim_client:
                result = await self.sim_client.send_command(command, **params)
            elif self.real_drone_client:
                result = await self.real_drone_client.send_command(command, **params)
            else:
                result = {"success": False, "error": "Нет подключения к дрону"}
            
            # Обновление состояния
            if command in ["TAKEOFF", "GOTO", "FOLLOW_PATH"]:
                self.state = AgentState.FLYING
            elif command in ["LAND", "RTL"]:
                self.state = AgentState.LANDING
            
            # Уведомление субагента
            if self.sub_agent:
                await self.sub_agent.notify_action(command, result)
            
            return result
        except Exception as e:
            logger.error(f"Ошибка выполнения действия: {e}")
            return {"success": False, "error": str(e)}
    
    async def learn(self, experience: Dict[str, Any]):
        """
        Обучение агента на основе опыта.
        
        Args:
            experience (Dict[str, Any]): Опыт (состояние, действие, награда, следующее состояние).
        """
        try:
            # Сохранение опыта в долговременную память
            self.long_term_memory.store_experience(experience)
            
            # Обучение RL-агента
            if self.config.get('learning', {}).get('enabled', False):
                await self.learner.learn_from_experience(experience)
            
            # Консультация с субагентом
            if self.sub_agent:
                lessons = await self.sub_agent.analyze_experience(experience)
                await self._apply_lessons(lessons)
            
            logger.info("Обучение завершено успешно")
        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
    
    async def _apply_lessons(self, lessons: Dict[str, Any]):
        """Применение уроков от субагента."""
        if lessons.get("improvements"):
            for improvement in lessons["improvements"]:
                logger.info(f"Применяю улучшение: {improvement}")
    
    async def run_mission(self, mission: MissionParams):
        """
        Выполнение миссии.
        
        Args:
            mission (MissionParams): Параметры миссии.
        """
        self.current_mission = mission
        self.state = AgentState.FLYING
        logger.info(f"Начало миссии: {mission.name}")
        
        # Уведомление субагента
        await self.sub_agent.notify_mission_start(mission)
        
        # Данные миссии
        mission_data = {
            "start_time": datetime.now(),
            "waypoints_completed": [],
            "events": [],
            "data_collected": []
        }
        
        try:
            # Основной цикл миссии
            for waypoint in mission.waypoints:
                # Проверка на прерывание
                if self.state == AgentState.EMERGENCY:
                    break
                
                # Перемещение к точке
                result = await self._goto_waypoint(waypoint)
                if result.get("success"):
                    mission_data["waypoints_completed"].append(waypoint)
                    mission_data["events"].append({
                        "type": "waypoint_reached",
                        "waypoint": waypoint,
                        "timestamp": datetime.now()
                    })
                    
                    # Сбор данных в точке
                    if mission.data_collection:
                        data = await self._collect_waypoint_data(waypoint)
                        mission_data["data_collected"].append(data)
                
                await asyncio.sleep(0.1)
            
            # Завершение миссии
            await self._complete_mission(mission, mission_data)
            
        except Exception as e:
            logger.error(f"Ошибка выполнения миссии: {e}")
            await self._handle_mission_failure(e)
    
    async def _goto_waypoint(self, waypoint: Dict[str, float]) -> Dict[str, Any]:
        """Перемещение к точке маршрута."""
        command = "GOTO"
        params = {
            "x": waypoint.get("x", 0),
            "y": waypoint.get("y", 0),
            "z": waypoint.get("z", 10),
            "speed": waypoint.get("speed", 5.0)
        }
        
        if self.sim_client:
            return await self.sim_client.send_command(command, **params)
        elif self.real_drone_client:
            return await self.real_drone_client.send_command(command, **params)
        
        return {"success": False, "error": "Нет подключения"}
    
    async def _collect_waypoint_data(self, waypoint: Dict[str, float]) -> Dict[str, Any]:
        """Сбор данных в точке маршрута."""
        perception = await self.perceive()
        return {
            "waypoint": waypoint,
            "telemetry": perception.get("telemetry", {}),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _complete_mission(self, mission: MissionParams, mission_data: Dict[str, Any]):
        """Завершение миссии."""
        logger.info(f"Миссия завершена: {mission.name}")
        
        # Формирование отчета
        report = {
            "mission_id": mission.mission_id,
            "mission_name": mission.name,
            "start_time": mission_data["start_time"],
            "end_time": datetime.now(),
            "status": "completed",
            "waypoints_completed": len(mission_data["waypoints_completed"]),
            "total_waypoints": len(mission.waypoints),
            "events": mission_data["events"],
            "data_collected": mission_data["data_collected"]
        }
        
        # Сохранение отчета
        import os
        os.makedirs("data/reports", exist_ok=True)
        with open(f"data/reports/{mission.mission_id}.json", "w", encoding='utf-8') as f:
            json.dump(report, f, indent=4, default=str)
        
        # Уведомление субагента
        await self.sub_agent.notify_mission_complete(report)
        
        # Обучение на опыте миссии
        if mission.learning_enabled:
            await self.learn({
                "mission": mission.to_dict(),
                "result": report
            })
        
        # Сброс состояния
        self.current_mission = None
        self.state = AgentState.READY
        self.mission_history.append(report)
        
        return report
    
    async def _handle_mission_failure(self, error: Exception):
        """Обработка ошибки миссии."""
        logger.error(f"Ошибка миссии: {error}")
        
        # Аварийная посадка
        await self.act({"command": "LAND", "reason": "Ошибка миссии", "priority": "high"})
        
        self.current_mission = None
        self.state = AgentState.READY
    
    def _merge_decisions(self, decision: Dict[str, Any], sub_agent_advice: Dict[str, Any]) -> Dict[str, Any]:
        """
        Объединение решения агента и рекомендации субагента.
        
        Args:
            decision (Dict[str, Any]): Решение агента.
            sub_agent_advice (Dict[str, Any]): Рекомендация субагента.
            
        Returns:
            Dict[str, Any]: Объединенное решение.
        """
        if sub_agent_advice.get("suggested_command"):
            decision["command"] = sub_agent_advice["suggested_command"]
            decision["reason"] = sub_agent_advice.get("reason", "Рекомендация субагента")
        
        return decision
    
    async def process_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Обработка команды от оператора.
        
        Args:
            command (str): Текстовая команда.
            params (Dict[str, Any]): Дополнительные параметры.
            
        Returns:
            Dict[str, Any]: Результат выполнения.
        """
        params = params or {}
        logger.info(f"Обработка команды: {command}")
        
        try:
            # Парсинг команды
            parsed = self._parse_command(command)
            
            # Выполнение команды
            if parsed["action"] == "takeoff":
                return await self.act({"command": "TAKEOFF", "params": {"altitude": parsed.get("altitude", 10)}})
            elif parsed["action"] == "land":
                return await self.act({"command": "LAND", "params": {}})
            elif parsed["action"] == "goto":
                return await self.act({"command": "GOTO", "params": parsed.get("coordinates", {})})
            elif parsed["action"] == "rtl":
                return await self.act({"command": "RTL", "params": {}})
            elif parsed["action"] == "hover":
                return await self.act({"command": "HOVER", "params": {}})
            else:
                return {"success": False, "error": f"Неизвестная команда: {command}"}
        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_command(self, command: str) -> Dict[str, Any]:
        """Парсинг текстовой команды."""
        command = command.lower().strip()
        
        if "взлет" in command or "takeoff" in command:
            # Извлечение высоты
            import re
            numbers = re.findall(r'\d+', command)
            altitude = int(numbers[0]) if numbers else 10
            return {"action": "takeoff", "altitude": altitude}
        
        elif "посадка" in command or "land" in command:
            return {"action": "land"}
        
        elif "вернись" in command or "rtl" in command or "домой" in command:
            return {"action": "rtl"}
        
        elif "зависни" in command or "hover" in command:
            return {"action": "hover"}
        
        elif "лети" in command or "goto" in command:
            return {"action": "goto", "coordinates": {"x": 10, "y": 10, "z": 10}}
        
        return {"action": "unknown"}
    
    async def emergency_stop(self):
        """Аварийная остановка дрона."""
        logger.error("Аварийная остановка!")
        self.state = AgentState.EMERGENCY
        
        if self.sim_client:
            await self.sim_client.emergency_stop()
        elif self.real_drone_client:
            await self.real_drone_client.emergency_stop()
    
    async def save_state(self):
        """Сохранение состояния агента."""
        try:
            state_data = {
                "agent_id": self.agent_id,
                "state": self.state.value,
                "telemetry": self.telemetry,
                "current_mission": self.current_mission.to_dict() if self.current_mission else None,
                "timestamp": datetime.now().isoformat()
            }
            
            import os
            os.makedirs("data/state", exist_ok=True)
            
            with open(f"data/state/agent_{self.agent_id}_state.json", "w", encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Состояние агента сохранено")
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")
    
    async def load_state(self, state_id: str = None):
        """Загрузка состояния агента."""
        try:
            import os
            from pathlib import Path
            
            if state_id:
                state_path = Path(f"data/state/{state_id}.json")
            else:
                state_dir = Path("data/state")
                if state_dir.exists():
                    states = list(state_dir.glob(f"agent_{self.agent_id}_state.json"))
                    if states:
                        state_path = states[0]
                    else:
                        return False
                else:
                    return False
            
            if state_path and state_path.exists():
                with open(state_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                self.state = AgentState(state_data.get("state", "ready"))
                self.telemetry.update(state_data.get("telemetry", {}))
                
                logger.info(f"Состояние агента загружено из {state_path}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния: {e}")
            return False
    
    async def shutdown(self):
        """Корректное завершение работы агента."""
        logger.info("Завершение работы агента...")
        
        # Безопасная посадка если в полете
        if self.state == AgentState.FLYING:
            await self._safe_landing()
        
        # Сохранение состояния
        await self.save_state()
        
        # Завершение инструментов
        for tool in self.tools.values():
            await tool.shutdown()
        
        # Завершение субагента
        await self.sub_agent.shutdown()
        
        # Отключение от симулятора/аппаратуры
        if self.sim_client:
            await self.sim_client.disconnect()
        if self.real_drone_client:
            await self.real_drone_client.disconnect()
        
        self.state = AgentState.SHUTDOWN
        logger.info("Агент завершил работу.")
    
    async def _safe_landing(self):
        """Безопасная посадка."""
        logger.info("Выполняю безопасную посадку...")
        await self.act({"command": "LAND", "params": {}})
        self.state = AgentState.READY
    
    async def get_status(self) -> Dict[str, Any]:
        """Получение текущего статуса агента."""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "mission": self.current_mission.to_dict() if self.current_mission else None,
            "telemetry": self.telemetry,
            "tools_status": {name: getattr(tool, 'status', 'unknown') for name, tool in self.tools.items()},
            "sub_agent_online": self.sub_agent is not None and getattr(self.sub_agent, 'status', '') == 'ready',
            "timestamp": datetime.now().isoformat()
        }
