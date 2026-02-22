"""
Unit тесты для инструментов
"""
import pytest
import asyncio
import numpy as np

from tools.slom import SlomTool, SafetyLevel
from tools.mifly import MiFlyTool
from tools.amorfus import AmorfusTool, DroneState


class TestSlomTool:
    """Тесты инструмента безопасности"""
    
    @pytest.fixture
    def slom(self):
        config = {
            'safety': {
                'battery_critical': 15,
                'battery_low': 25,
                'signal_critical': 20,
                'obstacle_distance': 5,
                'max_altitude': 120
            }
        }
        return SlomTool(config)
    
    @pytest.mark.asyncio
    async def test_low_battery_critical(self, slom):
        await slom.initialize()
        
        data = {"telemetry": {"battery": 10}}
        result = await slom.check_emergency(data)
        
        assert result is not None
        assert result["type"] == "low_battery"
        assert result["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_low_battery_warning(self, slom):
        await slom.initialize()
        
        data = {"telemetry": {"battery": 20}}
        result = await slom.check_emergency(data)
        
        assert result is not None
        assert result["severity"] == "warning"
    
    @pytest.mark.asyncio
    async def test_normal_battery(self, slom):
        await slom.initialize()
        
        data = {"telemetry": {"battery": 80}}
        result = await slom.check_emergency(data)
        
        assert result is None
        assert slom.safety_level == SafetyLevel.NORMAL
    
    @pytest.mark.asyncio
    async def test_signal_lost(self, slom):
        await slom.initialize()
        
        data = {"telemetry": {"signal_strength": 15}}
        result = await slom.check_emergency(data)
        
        assert result is not None
        assert result["type"] == "signal_lost"


class TestMiFlyTool:
    """Тесты инструмента управления полетом"""
    
    @pytest.fixture
    def mifly(self):
        config = {
            'flight': {
                'default_speed': 5.0,
                'max_speed': 15.0,
                'takeoff_altitude': 10.0
            }
        }
        return MiFlyTool(config)
    
    @pytest.mark.asyncio
    async def test_takeoff(self, mifly):
        await mifly.initialize()
        
        result = await mifly.action_takeoff(altitude=15)
        
        assert result["success"] is True
        assert mifly.is_flying is True
        assert mifly.current_position["z"] == 15
    
    @pytest.mark.asyncio
    async def test_takeoff_while_flying(self, mifly):
        await mifly.initialize()
        mifly.is_flying = True
        
        result = await mifly.action_takeoff()
        
        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_land(self, mifly):
        await mifly.initialize()
        mifly.is_flying = True
        mifly.current_position["z"] = 10
        
        result = await mifly.action_land()
        
        assert result["success"] is True
        assert mifly.is_flying is False
        assert mifly.current_position["z"] == 0
    
    @pytest.mark.asyncio
    async def test_goto(self, mifly):
        await mifly.initialize()
        mifly.is_flying = True
        
        result = await mifly.action_goto(x=50, y=50, z=20, speed=5)
        
        assert result["success"] is True
        assert mifly.current_position["x"] == 50
        assert mifly.current_position["y"] == 50
    
    @pytest.mark.asyncio
    async def test_goto_while_not_flying(self, mifly):
        await mifly.initialize()
        
        result = await mifly.action_goto(x=50, y=50, z=20)
        
        assert result["success"] is False


class TestAmorfusTool:
    """Тесты инструмента роевого интеллекта"""
    
    @pytest.fixture
    def amorfus(self):
        config = {
            'swarm': {
                'size': 5,
                'consensus_algorithm': 'vicsek',
                'communication_range': 50.0
            }
        }
        return AmorfusTool(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, amorfus):
        await amorfus.initialize()
        
        assert len(amorfus.swarm_state) == 5
        assert amorfus.leader_id == 0
    
    @pytest.mark.asyncio
    async def test_set_formation(self, amorfus):
        await amorfus.initialize()
        
        result = await amorfus.action_set_formation("circle")
        
        assert result["success"] is True
        assert amorfus.formation == "circle"
    
    @pytest.mark.asyncio
    async def test_set_invalid_formation(self, amorfus):
        await amorfus.initialize()
        
        result = await amorfus.action_set_formation("invalid")
        
        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_set_leader(self, amorfus):
        await amorfus.initialize()
        
        result = await amorfus.action_set_leader(2)
        
        assert result["success"] is True
        assert amorfus.leader_id == 2
    
    @pytest.mark.asyncio
    async def test_set_invalid_leader(self, amorfus):
        await amorfus.initialize()
        
        result = await amorfus.action_set_leader(10)
        
        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_get_swarm_status(self, amorfus):
        await amorfus.initialize()
        
        result = await amorfus.action_get_swarm_status()
        
        assert result["success"] is True
        assert result["swarm_size"] == 5


class TestBaseTool:
    """Тесты базового класса инструментов"""
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        from tools.base_tool import BaseTool, ToolStatus
        
        class TestTool(BaseTool):
            async def initialize(self):
                self.status = ToolStatus.READY
            
            async def apply(self, data):
                return {"success": True}
            
            async def shutdown(self):
                pass
            
            async def action_test(self):
                return {"success": True}
        
        tool = TestTool({})
        await tool.initialize()
        
        # Проверка начальных метрик
        assert tool.metrics["calls"] == 0
        
        # Выполнение действия
        await tool.execute("test")
        
        # Проверка обновленных метрик
        assert tool.metrics["calls"] == 1
    
    def test_enable_disable(self):
        from tools.base_tool import BaseTool, ToolStatus
        
        class TestTool(BaseTool):
            async def initialize(self): pass
            async def apply(self, data): pass
            async def shutdown(self): pass
        
        tool = TestTool({})
        
        assert tool.enabled is True
        
        tool.disable()
        assert tool.enabled is False
        
        tool.enable()
        assert tool.enabled is True
