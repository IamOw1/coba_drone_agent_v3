# 🚁 COBA AI Drone Agent 2.0 - Быстрый старт

## ⚡ За 5 минут до первого полета!

### Простые шаги (вручную или через Docker)

#### Ручной режим
```bash
# 1. Клонируем и переходим в каталог
git clone https://github.com/IamOw1/coba_drone_agent_v3.git
cd coba_drone_agent_v3

# 2. Готовим виртуальное окружение
python -m venv venv  # или python3
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Быстрая проверка
python check_system.py        # 5/5 проверок

# 4. Запускаем нужный режим
python main.py agent          # только агент
python main.py api            # API (http://localhost:8000)
python main.py dashboard      # дашборд (http://localhost:8501)
python main.py all            # всё сразу
```
> или используйте `./run.sh <mode>` / `run.bat <mode>` для удобства

#### Docker (один контейнер)
```bash
# собрать образ(docker-compose build)
docker build -t coba-drone-agent .

# запустить контейнер (проброс портов, сохраняет данные в ./data)
docker run -d --name coba \
    -p 8000:8000 -p 8501:8501 \
    -v "$(pwd)/data:/app/data" \
    -e OPENAI_API_KEY=${OPENAI_API_KEY} \
    coba-drone-agent

# с docker-compose:
docker-compose up -d
```

Контейнер использует `CMD ["python","main.py","all"]` по умолчанию.


---

## 💡 Примеры использования

---

## 💡 Примеры использования

### Пример 1: Простая команда через Python

```python
import asyncio
from agent.core import DroneIntelligentAgent

async def main():
    # Создание и инициализация агента
    agent = DroneIntelligentAgent()
    await agent.initialize()
    
    # Взлет на 30 метров
    await agent.process_command("взлет на 30 метров")
    
    # Зависание (hover)
    await agent.process_command("зависни")
    
    # Возврат домой
    await agent.process_command("вернись домой")
    
    # Посадка
    await agent.process_command("посадка")
    
    # Завершение
    await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Пример 2: Выполнение миссии

```python
import asyncio
from agent.core import DroneIntelligentAgent, MissionParams

async def main():
    agent = DroneIntelligentAgent()
    await agent.initialize()
    
    # Создание миссии - облет прямоугольника
    mission = MissionParams(
        name="Облет здания",
        mission_id="building_survey_001",
        waypoints=[
            {"x": 0, "y": 0, "z": 30},
            {"x": 100, "y": 0, "z": 30},
            {"x": 100, "y": 100, "z": 30},
            {"x": 0, "y": 100, "z": 30},
        ],
        altitude=30,
        speed=10.0,
        data_collection=True,
        learning_enabled=False
    )
    
    # Запуск миссии
    await agent.run_mission(mission)
    
    await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Пример 3: Использование инструментов

```python
import asyncio
from agent.core import DroneIntelligentAgent

async def main():
    agent = DroneIntelligentAgent()
    await agent.initialize()
    
    # Использование инструмента GeoMap
    result = await agent.tools["geomap"].execute("add_point", {
        "lat": 55.7558,
        "lon": 37.6173,
        "name": "Москва"
    })
    print(f"Результат: {result}")
    
    # Использование инструмента MiFly
    result = await agent.tools["mifly"].execute("takeoff", {
        "altitude": 20
    })
    print(f"Результат: {result}")
    
    await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Пример 4: REST API

```bash
# Инициализация
curl -X POST http://localhost:8000/api/v1/agent/initialize

# Отправка команды
curl -X POST http://localhost:8000/api/v1/command \
  -H "Content-Type: application/json" \
  -d '{"command": "takeoff", "params": {"altitude": 20}}'

# Получение статуса
curl http://localhost:8000/api/v1/agent/status

# Получение телеметрии
curl http://localhost:8000/api/v1/telemetry

# Список инструментов
curl http://localhost:8000/api/v1/tools
```

---

## 🔧 Конфигурация

Основной файл конфигурации: `config/config.yaml`

### Полезные параметры для модификации:

```yaml
# Режим работы (true - симуляция, false - реальный дрон)
simulation:
  enabled: true

# Параметры безопасности
safety:
  battery_critical: 15      # Критический уровень батареи (%)
  battery_low: 25           # Низкий уровень батареи (%)
  max_altitude: 120         # Максимальная высота (м)
  max_distance: 1000        # Максимальное расстояние (м)

# Параметры полета
flight:
  default_speed: 5.0        # Скорость по умолчанию (м/с)
  max_speed: 15.0           # Максимальная скорость (м/с)
  max_altitude: 120.0       # Максимальная высота (м)

# Обучение
learning:
  enabled: true             # Включить обучение
  algorithm: "dqn"          # Алгоритм (dqn, ppo)
  epsilon: 1.0              # Коэффициент exploration (начальный)
  epsilon_min: 0.01         # Минимальный epsilon
  epsilon_decay: 0.995      # Скорость уменьшения epsilon

# Субагент GPT-4o
sub_agent:
  enabled: true             # Включить субагента
  api_key: "${OPENAI_API_KEY}"  # API ключ OpenAI
```

---

## 🎯 Типичные рабочие процессы

### Рабочий процесс 1: Быстрая демонстрация

```bash
# 1. Проверка
python check_system.py

# 2. Демонстрация
python demo.py

# 3. Выбрать "1" для базовых команд
```

### Рабочий процесс 2: Запуск специальной миссии

```python
# 1. Создать миссия.py с нужными waypoints
# 2. Запустить специальный скрипт
# 3. Сохранить отчет в data/reports/
```

### Рабочий процесс 3: Разработка нового инструмента

```python
# 1. Создать tools/my_tool.py
# 2. Наследоваться от BaseTool
# 3. Реализовать методы: initialize, apply, shutdown
# 4. Добавить в config.yaml
```

---

## 🚨 Решение проблем

### Проблема: "ModuleNotFoundError: No module named 'agents'"
**Решение:**
```bash
pip install -r requirements.txt
```

### Проблема: "AirSim не установлен"
**Решение:**
```bash
pip install airsim
```
Или используется встроенная симуляция (нормально)

### Проблема: "API недоступен на localhost:8000"
**Решение:**
1. Убедитесь что сервер запущен: `python main.py api`
2. Проверьте порт в параметрах: `python main.py api --port 8080`

### Проблема: "Телеметрия все нули"
**Решение:**
Это нормально в режиме симуляции - используется встроенная симуляция телеметрии

---

## 📚 Дополнительная информация

- **Полная документация:** [README.md](README.md)
- **Архитектура системы:** [PRESENTATION.md](PRESENTATION.md)
- **Итоговый отчет:** [COMPLETION_REPORT.md](COMPLETION_REPORT.md)

---

## ✨ Что дальше?

1. **Изучите примеры** в папке `examples/`
2. **Прочитайте документацию** по интересующим вас компонентам
3. **Разработайте собственные инструменты** на базе `BaseTool`
4. **Интегрируйте с реальным дроном** используя `MAVLinkHandler`
5. **Обучите агента** на новых данных полета

---

**Готовы? Начните с `python check_system.py` прямо сейчас! 🚀**
