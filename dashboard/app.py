"""
Веб-дашборд для управления дроном с ИИ-агентом
"""
import streamlit as st
import asyncio
import json
import requests
from datetime import datetime

# Настройка страницы
st.set_page_config(
    page_title="COBA AI Drone Agent - Панель управления",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .telemetry-value {
        font-size: 1.2rem;
        font-weight: bold;
        color: #43A047;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# API URL
API_URL = "http://localhost:8000"


def api_get(endpoint: str) -> dict:
    """GET запрос к API"""
    try:
        response = requests.get(f"{API_URL}{endpoint}", timeout=5)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}


def api_post(endpoint: str, data: dict = None) -> dict:
    """POST запрос к API"""
    try:
        response = requests.post(f"{API_URL}{endpoint}", json=data, timeout=5)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}


def render_sidebar():
    """Боковая панель"""
    with st.sidebar:
        st.title("⚙️ Управление")
        
        # Статус подключения
        st.subheader("Статус системы")
        
        health = api_get("/health")
        if "error" not in health:
            st.success("✅ API подключен")
        else:
            st.error("❌ API недоступен")
        
        # Управление агентом
        st.subheader("Агент")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Инициализировать"):
                result = api_post("/api/v1/agent/initialize")
                if result.get("success"):
                    st.success("Агент инициализирован")
                else:
                    st.error(result.get("error", "Ошибка"))
        
        with col2:
            if st.button("⏹️ Остановить"):
                result = api_post("/api/v1/agent/shutdown")
                if result.get("success"):
                    st.success("Агент остановлен")
                else:
                    st.error(result.get("error", "Ошибка"))
        
        # Инструменты
        st.subheader("🛠️ Инструменты")
        
        tools = api_get("/api/v1/tools")
        if "error" not in tools:
            for tool in tools.get("tools", []):
                status_color = "🟢" if tool.get("status") == "ready" else "🔴"
                st.write(f"{status_color} {tool['name']}")


def render_telemetry():
    """Вкладка телеметрии"""
    st.header("📊 Телеметрия")
    
    # Получение телеметрии
    telemetry_data = api_get("/api/v1/telemetry")
    
    if "error" in telemetry_data:
        st.warning("Телеметрия недоступна")
        return
    
    telemetry = telemetry_data.get("telemetry", {})
    
    # Показатели
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Батарея", f"{telemetry.get('battery', 0):.1f}%")
    
    with col2:
        pos = telemetry.get("position", {})
        st.metric("Высота", f"{pos.get('z', 0):.1f} м")
    
    with col3:
        vel = telemetry.get("velocity", {})
        speed = (vel.get("vx", 0)**2 + vel.get("vy", 0)**2 + vel.get("vz", 0)**2) ** 0.5
        st.metric("Скорость", f"{speed:.1f} м/с")
    
    with col4:
        st.metric("GPS", telemetry.get("gps_status", "Unknown"))
    
    # Позиция
    st.subheader("Позиция")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**X:** {pos.get('x', 0):.2f} м")
    
    with col2:
        st.write(f"**Y:** {pos.get('y', 0):.2f} м")
    
    with col3:
        st.write(f"**Z:** {pos.get('z', 0):.2f} м")
    
    # Скорость
    st.subheader("Скорость")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Vx:** {vel.get('vx', 0):.2f} м/с")
    
    with col2:
        st.write(f"**Vy:** {vel.get('vy', 0):.2f} м/с")
    
    with col3:
        st.write(f"**Vz:** {vel.get('vz', 0):.2f} м/с")
    
    # Аттитюд
    st.subheader("Ориентация")
    
    att = telemetry.get("attitude", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Roll:** {att.get('roll', 0):.2f}")
    
    with col2:
        st.write(f"**Pitch:** {att.get('pitch', 0):.2f}")
    
    with col3:
        st.write(f"**Yaw:** {att.get('yaw', 0):.2f}")


def render_mission_control():
    """Вкладка управления миссиями"""
    st.header("🗺️ Управление миссиями")
    
    # Создание миссии
    st.subheader("Создать миссию")
    
    mission_name = st.text_input("Название миссии", "Миссия 1")
    
    # Точки маршрута
    st.write("Точки маршрута:")
    
    waypoints = []
    
    for i in range(3):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            x = st.number_input(f"X {i+1}", value=float(i*10), key=f"x_{i}")
        
        with col2:
            y = st.number_input(f"Y {i+1}", value=0.0, key=f"y_{i}")
        
        with col3:
            z = st.number_input(f"Z {i+1}", value=10.0, key=f"z_{i}")
        
        with col4:
            speed = st.number_input(f"Скорость {i+1}", value=5.0, key=f"speed_{i}")
        
        waypoints.append({"x": x, "y": y, "z": z, "speed": speed})
    
    altitude = st.slider("Высота полета", 5, 100, 30)
    
    if st.button("▶️ Запустить миссию"):
        mission_data = {
            "name": mission_name,
            "waypoints": waypoints,
            "altitude": altitude
        }
        
        result = api_post("/api/v1/mission/start", mission_data)
        
        if result.get("success"):
            st.success(f"Миссия {result.get('mission_id')} запущена")
        else:
            st.error(result.get("error", "Ошибка запуска миссии"))
    
    # Текущая миссия
    st.subheader("Текущая миссия")
    
    mission_status = api_get("/api/v1/mission/status")
    
    if "error" not in mission_status:
        current = mission_status.get("current_mission")
        
        if current:
            st.write(f"**Название:** {current.get('name', 'Unknown')}")
            st.write(f"**ID:** {current.get('mission_id', 'Unknown')}")
            st.write(f"**Точек:** {len(current.get('waypoints', []))}")
            
            if st.button("⏹️ Остановить миссию"):
                result = api_post("/api/v1/mission/stop")
                st.success("Миссия остановлена")
        else:
            st.info("Нет активной миссии")


def render_commands():
    """Вкладка команд"""
    st.header("🎮 Команды")
    
    # Быстрые команды
    st.subheader("Быстрые команды")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🛫 Взлет"):
            result = api_post("/api/v1/command", {
                "command": "takeoff",
                "params": {"altitude": 10}
            })
            st.success("Команда отправлена")
    
    with col2:
        if st.button("🛬 Посадка"):
            result = api_post("/api/v1/command", {
                "command": "land"
            })
            st.success("Команда отправлена")
    
    with col3:
        if st.button("🏠 RTL"):
            result = api_post("/api/v1/command", {
                "command": "rtl"
            })
            st.success("Команда отправлена")
    
    # Навигация
    st.subheader("Навигация")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        goto_x = st.number_input("X", value=10.0, key="goto_x")
    
    with col2:
        goto_y = st.number_input("Y", value=10.0, key="goto_y")
    
    with col3:
        goto_z = st.number_input("Z", value=10.0, key="goto_z")
    
    if st.button("🎯 Лететь в точку"):
        result = api_post("/api/v1/command", {
            "command": "goto",
            "params": {"x": goto_x, "y": goto_y, "z": goto_z}
        })
        st.success("Команда отправлена")
    
    # Аварийная остановка
    st.subheader("Аварийные команды")
    
    if st.button("🚨 Аварийная остановка", type="primary"):
        result = api_post("/api/v1/emergency/stop")
        st.error("Аварийная остановка выполнена!")


def render_ai_assistant():
    """Вкладка ИИ-помощника"""
    st.header("🧠 ИИ-Помощник")
    
    # Статус субагента
    agent_status = api_get("/api/v1/agent/status")
    
    if "error" not in agent_status:
        sub_agent_online = agent_status.get("sub_agent_online", False)
        
        if sub_agent_online:
            st.success("✅ Субагент активен")
        else:
            st.warning("⚠️ Субагент не активен")
    
    # Чат с помощником
    st.subheader("Чат с помощником")
    
    question = st.text_area("Ваш вопрос:", placeholder="Например: Какие инструменты доступны?")
    
    if st.button("💬 Спросить"):
        if question:
            result = api_get(f"/api/v1/sub_agent/ask?question={question}")
            
            if "error" not in result:
                st.write(f"**Ответ:** {result.get('answer', 'Нет ответа')}")
            else:
                st.error("Не удалось получить ответ")


def render_learning():
    """Вкладка обучения"""
    st.header("🎓 Обучение")
    
    # Прогресс обучения
    progress = api_get("/api/v1/learning/progress")
    
    if "error" not in progress:
        learning = progress.get("learning_progress", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Шагов", learning.get("step_count", 0))
        
        with col2:
            st.metric("Эпизодов", learning.get("episode_count", 0))
        
        with col3:
            st.metric("Epsilon", f"{learning.get('epsilon', 0):.3f}")
        
        # График наград (если есть данные)
        st.subheader("Прогресс обучения")
        
        # Здесь можно добавить график с помощью st.line_chart
        st.info("Данные о наградах будут отображаться здесь")
    else:
        st.warning("Данные об обучении недоступны")


def main():
    """Главная функция"""
    # Заголовок
    st.markdown('<h1 class="main-header">🚁 COBA AI Drone Agent</h1>', unsafe_allow_html=True)
    
    # Боковая панель
    render_sidebar()
    
    # Вкладки
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Телеметрия",
        "🗺️ Миссии",
        "🎮 Команды",
        "🧠 ИИ-Помощник",
        "🎓 Обучение"
    ])
    
    with tab1:
        render_telemetry()
    
    with tab2:
        render_mission_control()
    
    with tab3:
        render_commands()
    
    with tab4:
        render_ai_assistant()
    
    with tab5:
        render_learning()
    
    # Автообновление
    st.empty()


if __name__ == "__main__":
    main()
