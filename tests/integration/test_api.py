"""
Интеграционные тесты API
"""
import pytest
from fastapi.testclient import TestClient

from api.rest_api import create_app


@pytest.fixture
def client():
    """Фикстура для тестового клиента"""
    app = create_app()
    return TestClient(app)


def test_root_endpoint(client):
    """Тест корневого эндпоинта"""
    response = client.get("/")
    
    assert response.status_code == 200
    assert response.json()["name"] == "COBA AI Drone Agent API"


def test_health_check(client):
    """Тест проверки здоровья"""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_agent_status_without_agent(client):
    """Тест статуса агента без инициализации"""
    response = client.get("/api/v1/agent/status")
    
    assert response.status_code == 503


def test_telemetry_without_agent(client):
    """Тест телеметрии без инициализации"""
    response = client.get("/api/v1/telemetry")
    
    assert response.status_code == 503


def test_tools_without_agent(client):
    """Тест списка инструментов без инициализации"""
    response = client.get("/api/v1/tools")
    
    assert response.status_code == 503


def test_mission_status_without_agent(client):
    """Тест статуса миссии без инициализации"""
    response = client.get("/api/v1/mission/status")
    
    assert response.status_code == 503


def test_learning_progress_without_agent(client):
    """Тест прогресса обучения без инициализации"""
    response = client.get("/api/v1/learning/progress")
    
    assert response.status_code == 503


def test_sub_agent_ask_without_agent(client):
    """Тест вопроса субагенту без инициализации"""
    response = client.get("/api/v1/sub_agent/ask?question=test")
    
    assert response.status_code == 503
