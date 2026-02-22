"""
REST API для управления дроном
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from agent.core import DroneIntelligentAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Модели данных
class MissionRequest(BaseModel):
    name: str
    waypoints: List[Dict[str, float]]
    altitude: float = 30.0
    speed: float = 5.0

class CommandRequest(BaseModel):
    command: str
    params: Optional[Dict[str, Any]] = {}

class ConfigRequest(BaseModel):
    key: str
    value: Any

# Глобальные переменные
agent: Optional[DroneIntelligentAgent] = None
app = FastAPI(
    title="COBA AI Drone Agent API",
    description="API для управления дроном с ИИ-агентом",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_app(drone_agent: DroneIntelligentAgent = None) -> FastAPI:
    """
    Создание приложения FastAPI.
    
    Args:
        drone_agent (DroneIntelligentAgent): Экземпляр агента.
        
    Returns:
        FastAPI: Приложение FastAPI.
    """
    global agent
    agent = drone_agent
    return app


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "name": "COBA AI Drone Agent API",
        "version": "2.0.0",
        "status": "active"
    }


@app.get("/api/v1/agent/status")
async def get_agent_status():
    """Получение статуса агента"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    status = await agent.get_status()
    return status


@app.post("/api/v1/agent/initialize")
async def initialize_agent():
    """Инициализация агента"""
    global agent
    
    if not agent:
        agent = DroneIntelligentAgent()
    
    success = await agent.initialize()
    
    return {
        "success": success,
        "agent_id": agent.agent_id,
        "status": agent.state.value
    }


@app.post("/api/v1/agent/shutdown")
async def shutdown_agent():
    """Завершение работы агента"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    await agent.shutdown()
    
    return {
        "success": True,
        "message": "Агент завершил работу"
    }


@app.post("/api/v1/mission/start")
async def start_mission(mission: MissionRequest, background_tasks: BackgroundTasks):
    """Запуск миссии"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    from agent.core import MissionParams
    
    mission_params = MissionParams(
        name=mission.name,
        mission_id=f"mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        waypoints=mission.waypoints,
        altitude=mission.altitude,
        speed=mission.speed
    )
    
    # Запуск миссии в фоне
    background_tasks.add_task(agent.run_mission, mission_params)
    
    return {
        "success": True,
        "mission_id": mission_params.mission_id,
        "status": "started"
    }


@app.post("/api/v1/mission/stop")
async def stop_mission():
    """Остановка текущей миссии"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    # Установка статуса для остановки миссии
    agent.state = agent.agent.state.__class__.READY if hasattr(agent, 'state') else None
    
    return {
        "success": True,
        "message": "Миссия остановлена"
    }


@app.get("/api/v1/mission/status")
async def get_mission_status():
    """Получение статуса миссии"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    return {
        "current_mission": agent.current_mission.to_dict() if agent.current_mission else None,
        "mission_history": agent.mission_history
    }


@app.post("/api/v1/command")
async def send_command(request: CommandRequest):
    """Отправка команды дрону"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    result = await agent.process_command(request.command, request.params)
    
    return result


@app.post("/api/v1/emergency/stop")
async def emergency_stop():
    """Аварийная остановка"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    await agent.emergency_stop()
    
    return {
        "success": True,
        "message": "Аварийная остановка выполнена"
    }


@app.get("/api/v1/telemetry")
async def get_telemetry():
    """Получение телеметрии"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    return {
        "telemetry": agent.telemetry
    }


@app.get("/api/v1/tools")
async def get_tools():
    """Получение списка инструментов"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "status": tool.status.value if hasattr(tool, 'status') else "unknown"
            }
            for name, tool in agent.tools.items()
        ]
    }


@app.post("/api/v1/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, request: CommandRequest):
    """Выполнение инструмента"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    if tool_name not in agent.tools:
        raise HTTPException(status_code=404, detail=f"Инструмент {tool_name} не найден")
    
    tool = agent.tools[tool_name]
    result = await tool.execute(request.command, request.params)
    
    return result


@app.get("/api/v1/learning/progress")
async def get_learning_progress():
    """Получение прогресса обучения"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    progress = agent.learner.get_progress()
    
    return {
        "learning_progress": progress
    }


@app.get("/api/v1/memory/short_term")
async def get_short_term_memory(limit: int = 10):
    """Получение краткосрочной памяти"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    memory = agent.short_term_memory.get_recent(limit)
    
    return {
        "memory": memory,
        "count": len(memory)
    }


@app.get("/api/v1/sub_agent/ask")
async def ask_sub_agent(question: str):
    """Вопрос субагенту"""
    if not agent or not agent.sub_agent:
        raise HTTPException(status_code=503, detail="Субагент не инициализирован")
    
    answer = await agent.sub_agent.ask(question)
    
    return {
        "question": question,
        "answer": answer
    }


@app.get("/api/v1/reports/missions")
async def get_mission_reports():
    """Получение отчетов о миссиях"""
    if not agent:
        raise HTTPException(status_code=503, detail="Агент не инициализирован")
    
    return {
        "reports": agent.mission_history
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_connected": agent is not None
    }


# WebSocket для real-time данных (опционально)
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket):
    """WebSocket для телеметрии в реальном времени"""
    await websocket.accept()
    
    try:
        while True:
            if agent:
                telemetry = await agent.perceive()
                await websocket.send_json(telemetry)
            
            await asyncio.sleep(0.1)  # 10 Hz
    except Exception as e:
        logger.error(f"WebSocket ошибка: {e}")
    finally:
        await websocket.close()
