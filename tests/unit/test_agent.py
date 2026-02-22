"""
Unit тесты для агента
"""
import pytest
import asyncio
from unittest.mock import Mock, patch

from agent.core import DroneIntelligentAgent, MissionParams
from agent.memory import ShortTermMemory, LongTermMemory
from agent.decision_maker import DecisionMaker
from agent.learner import Learner


class TestShortTermMemory:
    """Тесты краткосрочной памяти"""
    
    def test_add_and_get(self):
        memory = ShortTermMemory(capacity=10)
        memory.add({"test": "data"})
        
        assert len(memory.get_all()) == 1
        assert memory.get_recent(1)[0]["test"] == "data"
    
    def test_capacity_limit(self):
        memory = ShortTermMemory(capacity=5)
        
        for i in range(10):
            memory.add({"index": i})
        
        assert len(memory.get_all()) == 5
    
    def test_search(self):
        memory = ShortTermMemory(capacity=10)
        memory.add({"key": "value1", "data": "a"})
        memory.add({"key": "value2", "data": "b"})
        
        results = memory.search("key", "value1")
        assert len(results) == 1
        assert results[0]["data"] == "a"
    
    def test_clear(self):
        memory = ShortTermMemory(capacity=10)
        memory.add({"test": "data"})
        memory.clear()
        
        assert len(memory.get_all()) == 0


class TestDecisionMaker:
    """Тесты принятия решений"""
    
    @pytest.fixture
    def decision_maker(self):
        config = {
            "safety": {"threshold": 0.8},
            "decision": {"confidence_threshold": 0.7}
        }
        return DecisionMaker(config)
    
    @pytest.mark.asyncio
    async def test_safety_rules_trigger(self, decision_maker):
        telemetry = {"battery": 10}  # Критический заряд
        
        result = decision_maker._check_safety_rules(telemetry)
        
        assert result is not None
        assert result["action"] == "LAND"
    
    @pytest.mark.asyncio
    async def test_safety_rules_no_trigger(self, decision_maker):
        telemetry = {"battery": 80}  # Нормальный заряд
        
        result = decision_maker._check_safety_rules(telemetry)
        
        assert result is None
    
    def test_calculate_distance(self, decision_maker):
        pos1 = {"x": 0, "y": 0, "z": 0}
        pos2 = {"x": 3, "y": 4, "z": 0}
        
        distance = decision_maker._calculate_distance(pos1, pos2)
        
        assert distance == 5.0


class TestLearner:
    """Тесты обучения"""
    
    @pytest.fixture
    def learner(self):
        config = {
            "learning": {
                "state_size": 24,
                "action_size": 8,
                "learning_rate": 0.001,
                "gamma": 0.99,
                "epsilon": 1.0,
                "epsilon_min": 0.01,
                "epsilon_decay": 0.995,
                "batch_size": 64,
                "buffer_size": 1000,
                "target_update": 100
            }
        }
        return Learner(config)
    
    def test_initialization(self, learner):
        assert learner.state_size == 24
        assert learner.action_size == 8
        assert learner.epsilon == 1.0
    
    def test_calculate_reward(self, learner):
        experience = {
            "mission_completed": True,
            "waypoint_reached": True,
            "state": {"telemetry": {"battery": 80}}
        }
        
        reward = learner._calculate_reward(experience)
        
        assert reward > 0
    
    def test_select_action_exploration(self, learner):
        import numpy as np
        
        state = np.zeros(24)
        learner.epsilon = 1.0  # Полная эксплорация
        
        action = learner.select_action(state, training=True)
        
        assert 0 <= action < learner.action_size


class TestMissionParams:
    """Тесты параметров миссии"""
    
    def test_to_dict(self):
        mission = MissionParams(
            name="Test Mission",
            mission_id="test_001",
            waypoints=[{"x": 0, "y": 0, "z": 10}],
            altitude=30,
            speed=5
        )
        
        data = mission.to_dict()
        
        assert data["name"] == "Test Mission"
        assert data["mission_id"] == "test_001"
        assert len(data["waypoints"]) == 1


@pytest.mark.asyncio
class TestDroneIntelligentAgent:
    """Тесты агента"""
    
    @pytest.fixture
    async def agent(self):
        with patch.object(DroneIntelligentAgent, '_load_config', return_value={
            'agent_id': 'test_agent',
            'simulation': {'enabled': True},
            'sub_agent': {'enabled': False},
            'tools': [],
            'learning': {'enabled': False}
        }):
            agent = DroneIntelligentAgent()
            yield agent
    
    async def test_parse_command_takeoff(self, agent):
        result = agent._parse_command("взлет на 20 метров")
        
        assert result["action"] == "takeoff"
        assert result["altitude"] == 20
    
    async def test_parse_command_land(self, agent):
        result = agent._parse_command("посадка")
        
        assert result["action"] == "land"
    
    async def test_parse_command_rtl(self, agent):
        result = agent._parse_command("вернись домой")
        
        assert result["action"] == "rtl"
