# 📚 ПОЛНАЯ ДОКУМЕНТАЦИЯ REST API - COBA AI Drone Agent v3

## 📋 Содержание
- [Базовая информация](#базовая-информация)
- [Аутентификация](#аутентификация)
- [Статус и инициализация](#статус-и-инициализация)
- [Управление миссиями](#управление-миссиями)
- [Команды управления](#команды-управления)
- [Телеметрия и мониторинг](#телеметрия-и-мониторинг)
- [Инструменты (Tools)](#инструменты-tools)
- [Обучение и память](#обучение-и-память)
- [Субагент и AI](#субагент-и-ai)
- [Отчеты и история](#отчеты-и-история)
- [WebSocket реал-тайм](#websocket-реал-тайм)
- [Коды ошибок](#коды-ошибок)
- [Примеры использования](#примеры-использования)

## Базовая информация

### Базовый URL
```
http://localhost:8000
```

### Версия API
```
v1
```

### Префикс
```
/api/v1
```

### Поддерживаемые форматы
- JSON (основной)
- WebSocket (для реал-тайм)

### Таймауты
- HTTP запрос: 30 сек
- WebSocket соединение: 5 мин неактивности

## Аутентификация

### API Key (если включена)
```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/v1/agent/status
```

### JWT Token (опционально)
```bash
# Получить токен
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Использовать токен
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/v1/agent/status
```

## Статус и инициализация

### GET /health
Проверка здоровья сервера

**Запрос:**
```bash
curl http://localhost:8000/health
```

**Ответ (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-23T10:30:45.123Z",
  "uptime_seconds": 3600,
  "version": "3.0.0"
}
```

### GET /api/v1/agent/status
Получить статус агента

**Запрос:**
```bash
curl http://localhost:8000/api/v1/agent/status
```

**Ответ (200 OK):**
```json
{
  "agent_id": "drone_agent_001",
  "state": "READY",
  "battery_level": 85,
  "altitude": 45.5,
  "latitude": 55.7558,
  "longitude": 37.6173,
  "speed": 5.2,
  "heading": 90,
  "connected": true,
  "simulator_mode": true,
  "tools_count": 10,
  "memory_usage_mb": 256,
  "uptime_seconds": 3600
}
```

### POST /api/v1/agent/initialize
Инициализировать агента

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/agent/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "drone_type": "quadcopter",
    "connection_string": "udp:127.0.0.1:14550",
    "simulator_enabled": true,
    "verbose": true
  }'
```

**Ответ (200 OK):**
```json
{
  "success": true,
  "agent_id": "drone_agent_001",
  "initialized_at": "2026-02-23T10:30:45.123Z",
  "message": "Agent initialized successfully"
}
```

### POST /api/v1/agent/shutdown
Выключить агента

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/agent/shutdown
```

**Ответ (200 OK):**
```json
{
  "success": true,
  "message": "Agent shutdown initiated",
  "shutdown_time": "2026-02-23T10:35:45.123Z"
}
```

## Управление миссиями

### POST /api/v1/mission/start
Запустить новую миссию

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/mission/start \
  -H "Content-Type: application/json" \
  -d '{
    "mission_id": "MISSION_001",
    "mission_name": "Обследование территории",
    "mission_type": "survey",
    "template": "area_mapping",
    "parameters": {
      "area_bounds": {
        "north": 55.7600,
        "south": 55.7500,
        "east": 37.6200,
        "west": 37.6100
      },
      "altitude": 50,
      "speed": 10,
      "overlap_percent": 30,
      "objectives": [
        "map_terrain",
        "detect_objects",
        "collect_photos"
      ]
    },
    "waypoints": [
      {"latitude": 55.7558, "longitude": 37.6173, "altitude": 50, "action": "photo"},
      {"latitude": 55.7560, "longitude": 37.6175, "altitude": 50, "action": "photo"}
    ],
    "start_immediately": true,
    "enable_learning": true,
    "backup_enabled": true
  }'
```

**Ответ (201 Created):**
```json
{
  "success": true,
  "mission_id": "MISSION_001",
  "status": "RUNNING",
  "start_time": "2026-02-23T10:30:45.123Z",
  "estimated_duration_seconds": 1800,
  "route_optimized": true,
  "waypoints_count": 15,
  "message": "Mission started successfully"
}
```

### POST /api/v1/mission/stop
Остановить текущую миссию

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/mission/stop \
  -H "Content-Type: application/json" \
  -d '{
    "mission_id": "MISSION_001",
    "reason": "user_request",
    "return_to_home": true
  }'
```

**Ответ (200 OK):**
```json
{
  "success": true,
  "mission_id": "MISSION_001",
  "stopped_at": "2026-02-23T10:32:45.123Z",
  "reason": "user_request",
  "data_saved": true,
  "report_generated": true
}
```

### GET /api/v1/mission/status
Получить статус текущей миссии

**Запрос:**
```bash
curl http://localhost:8000/api/v1/mission/status
```

**Ответ (200 OK):**
```json
{
  "mission_id": "MISSION_001",
  "mission_name": "Обследование территории",
  "status": "RUNNING",
  "progress_percent": 45,
  "elapsed_time_seconds": 810,
  "remaining_time_seconds": 990,
  "current_waypoint_index": 7,
  "total_waypoints": 15,
  "events": [
    {
      "timestamp": "2026-02-23T10:31:10.123Z",
      "event_type": "WAYPOINT_REACHED",
      "description": "Достигнута точка маршрута #6"
    },
    {
      "timestamp": "2026-02-23T10:31:20.123Z",
      "event_type": "PHOTO_TAKEN",
      "description": "Сделано фото объекта"
    }
  ],
  "telemetry": {
    "altitude": 50,
    "speed": 10,
    "battery": 65,
    "latitude": 55.7559,
    "longitude": 37.6174
  }
}
```

### GET /api/v1/mission/history
Получить историю миссий

**Запрос:**
```bash
curl "http://localhost:8000/api/v1/mission/history?limit=20&offset=0&status=COMPLETED"
```

**Ответ (200 OK):**
```json
{
  "total": 45,
  "limit": 20,
  "offset": 0,
  "missions": [
    {
      "mission_id": "MISSION_042",
      "mission_name": "Вечернее обследование",
      "status": "COMPLETED",
      "start_time": "2026-02-23T09:00:00.000Z",
      "end_time": "2026-02-23T09:45:00.000Z",
      "duration_seconds": 2700,
      "success": true,
      "waypoints_completed": 12,
      "total_waypoints": 12,
      "report_available": true
    }
  ]
}
```

## Команды управления

### POST /api/v1/command
Отправить команду дрону

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "takeoff",
    "parameters": {
      "altitude": 50,
      "rate": 1.0
    },
    "timeout_seconds": 30,
    "confirm": true
  }'
```

**Доступные команды:**
- `takeoff` - Взлёт
- `land` - Посадка
- `arm` - Взвести вооружение
- `disarm` - Расвести вооружение
- `goto` - Перемещение на точку
- `hover` - Зависание
- `set_mode` - Установить режим
- `set_speed` - Установить скорость
- `set_heading` - Установить курс
- `rtl` - Возврат на базу
- `emergency_stop` - Аварийная остановка

**Ответ (200 OK):**
```json
{
  "command_id": "CMD_12345",
  "command": "takeoff",
  "status": "EXECUTING",
  "message": "Drone is taking off",
  "estimated_completion_seconds": 25
}
```

### POST /api/v1/command/confirm
Подтвердить выполнение команды

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/command/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "command_id": "CMD_12345",
    "confirmed": true
  }'
```

**Ответ (200 OK):**
```json
{
  "command_id": "CMD_12345",
  "confirmed": true,
  "execution_started": true
}
```

### POST /api/v1/emergency/stop
Аварийная остановка

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/emergency/stop \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "critical_battery_level",
    "force": true
  }'
```

**Ответ (200 OK):**
```json
{
  "emergency_stop_triggered": true,
  "timestamp": "2026-02-23T10:32:45.123Z",
  "reason": "critical_battery_level",
  "drone_state": "LANDING",
  "landing_time_estimate_seconds": 30
}
```

## Телеметрия и мониторинг

### GET /api/v1/telemetry
Получить текущую телеметрию

**Запрос:**
```bash
curl http://localhost:8000/api/v1/telemetry
```

**Ответ (200 OK):**
```json
{
  "timestamp": "2026-02-23T10:32:45.123Z",
  "position": {
    "latitude": 55.7558,
    "longitude": 37.6173,
    "altitude": 45.5,
    "speed_horizontal": 5.2,
    "speed_vertical": -0.5,
    "heading": 90
  },
  "attitude": {
    "roll": 2.1,
    "pitch": -1.3,
    "yaw": 90.0
  },
  "power": {
    "battery_percent": 78,
    "battery_voltage": 14.8,
    "current_amps": 12.3,
    "estimated_remaining_minutes": 18.5
  },
  "environment": {
    "wind_speed": 3.5,
    "temperature_celsius": 15.2,
    "humidity_percent": 65,
    "air_pressure_hpa": 1013.25
  },
  "sensors": {
    "gps_satellites": 12,
    "gps_accuracy_meters": 2.5,
    "signal_strength_dbm": -65,
    "lidar_distance_meters": 45.2
  },
  "system": {
    "cpu_usage_percent": 42,
    "memory_usage_mb": 356,
    "temperature_cpu_celsius": 52,
    "sys_uptime_seconds": 3600
  }
}
```

### GET /api/v1/telemetry/stream
Получить поток телеметрии (Server-Sent Events)

**Запрос:**
```bash
curl http://localhost:8000/api/v1/telemetry/stream --no-buffer
```

**Поток (application/event-stream):**
```
event: telemetry_update
data: {"timestamp":"2026-02-23T10:32:46.000Z","altitude":45.5,"battery":78}

event: telemetry_update
data: {"timestamp":"2026-02-23T10:32:47.000Z","altitude":45.6,"battery":78}
```

### GET /api/v1/sensors/all
Получить все данные с датчиков

**Запрос:**
```bash
curl http://localhost:8000/api/v1/sensors/all
```

**Ответ (200 OK):**
```json
{
  "gps": {
    "latitude": 55.7558,
    "longitude": 37.6173,
    "altitude": 45.5,
    "satellites": 12,
    "hdop": 1.2,
    "fix_type": 3
  },
  "imu": {
    "accelerometer": [0.1, 0.2, 9.8],
    "gyroscope": [0.05, -0.1, 0.02],
    "magnetometer": [123, 456, 789]
  },
  "barometer": {
    "altitude": 45.5,
    "pressure": 1013.25,
    "temperature": 15.2
  },
  "lidar": {
    "distance_meters": 45.2,
    "scan_data": [45.1, 45.2, 45.3, ...]
  },
  "camera_primary": {
    "resolution": "1920x1080",
    "fps": 30,
    "focus": "auto"
  },
  "camera_thermal": {
    "resolution": "640x512",
    "fps": 30,
    "temperature_min": 10.5,
    "temperature_max": 35.2
  }
}
```

## Инструменты (Tools)

### GET /api/v1/tools
Получить список всех инструментов

**Запрос:**
```bash
curl http://localhost:8000/api/v1/tools
```

**Ответ (200 OK):**
```json
{
  "total": 10,
  "tools": [
    {
      "name": "slom",
      "class": "SlomTool",
      "enabled": true,
      "description": "Безопасность и контроль отказоустойчивости",
      "version": "1.0.0",
      "actions": [
        "check_safety",
        "set_geofence",
        "avoid_obstacle",
        "emergency_protocol",
        "monitor_parameters"
      ]
    },
    {
      "name": "amorfus",
      "class": "AmorfusTool",
      "enabled": true,
      "description": "Роевой интеллект для групп дронов",
      "version": "1.0.0",
      "actions": [
        "set_formation",
        "set_target",
        "sync_speed",
        "swarm_fly",
        "formation_dance"
      ]
    },
    {
      "name": "mifly",
      "class": "MiFlyTool",
      "enabled": true,
      "description": "Базовое управление полётом",
      "version": "1.0.0",
      "actions": [
        "takeoff",
        "land",
        "goto",
        "hover",
        "rtl",
        "set_speed"
      ]
    },
    {
      "name": "geomap",
      "class": "GeoMapTool",
      "enabled": true,
      "description": "Геопространственное картографирование",
      "version": "1.0.0",
      "actions": [
        "create_survey_mission",
        "generate_route",
        "analyze_area",
        "create_map"
      ]
    },
    {
      "name": "precision_landing",
      "class": "PrecisionLandingTool",
      "enabled": true,
      "description": "Точная посадка на маркеры",
      "version": "1.0.0",
      "actions": [
        "set_target",
        "detect_markers",
        "precision_land",
        "align_position"
      ]
    },
    {
      "name": "object_detection",
      "class": "ObjectDetectionTool",
      "enabled": true,
      "description": "Обнаружение объектов (YOLO)",
      "version": "1.0.0",
      "actions": [
        "detect",
        "track_object",
        "classify",
        "get_statistics"
      ]
    },
    {
      "name": "mission_planner",
      "class": "MissionPlannerTool",
      "enabled": true,
      "description": "Планировщик миссий",
      "version": "1.0.0",
      "actions": [
        "create_mission",
        "load_mission",
        "execute_mission",
        "replay_mission",
        "save_mission"
      ]
    },
    {
      "name": "autonomous_flight",
      "class": "AutonomousFlightTool",
      "enabled": true,
      "description": "Автономный полёт и навигация",
      "version": "1.0.0",
      "actions": [
        "set_flight_mode",
        "navigate_to",
        "follow_path",
        "optimize_route"
      ]
    },
    {
      "name": "deployment_manager",
      "class": "DeploymentManagerTool",
      "enabled": true,
      "description": "Управление развертыванием группы",
      "version": "1.0.0",
      "actions": [
        "deploy",
        "recall",
        "get_status",
        "coordinate_group"
      ]
    },
    {
      "name": "logistics",
      "class": "LogisticsTool",
      "enabled": true,
      "description": "Управление логистикой и доставкой",
      "version": "1.0.0",
      "actions": [
        "register_package",
        "deliver_package",
        "optimize_route",
        "track_delivery"
      ]
    }
  ]
}
```

### POST /api/v1/tools/{tool_name}/execute
Выполнить действие инструмента

**Запрос (пример для GeoMap):**
```bash
curl -X POST http://localhost:8000/api/v1/tools/geomap/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_survey_mission",
    "parameters": {
      "area_name": "Район А",
      "bounds": {
        "north": 55.7600,
        "south": 55.7500,
        "east": 37.6200,
        "west": 37.6100
      },
      "altitude": 50,
      "overlap_percent": 30,
      "objectives": ["map_terrain", "detect_objects"]
    }
  }'
```

**Ответ (200 OK):**
```json
{
  "tool": "geomap",
  "action": "create_survey_mission",
  "success": true,
  "mission_id": "SURVEY_001",
  "waypoints_generated": 24,
  "estimated_time_minutes": 45,
  "coverage_percent": 98.5,
  "data": {
    "mission_name": "Район А - Обследование",
    "total_distance_km": 15.2,
    "estimated_photos": 240
  }
}
```

### GET /api/v1/tools/{tool_name}/info
Получить информацию о инструменте

**Запрос:**
```bash
curl http://localhost:8000/api/v1/tools/slom/info
```

**Ответ (200 OK):**
```json
{
  "name": "slom",
  "class": "SlomTool",
  "enabled": true,
  "description": "Безопасность и контроль отказоустойчивости",
  "version": "1.0.0",
  "author": "COBA AI Team",
  "actions": [
    {
      "name": "check_safety",
      "description": "Проверить статус безопасности",
      "parameters": {
        "detailed": "boolean"
      }
    },
    {
      "name": "set_geofence",
      "description": "Установить геозону",
      "parameters": {
        "center": "object",
        "radius_meters": "number",
        "max_altitude": "number"
      }
    }
  ]
}
```

## Обучение и память

### GET /api/v1/learning/progress
Получить прогресс обучения

**Запрос:**
```bash
curl http://localhost:8000/api/v1/learning/progress
```

**Ответ (200 OK):**
```json
{
  "algorithm": "dqn",
  "status": "training",
  "epoch": 45,
  "total_experiences": 2341,
  "episodes_completed": 156,
  "average_reward": 145.3,
  "best_reward": 298.5,
  "loss": 0.042,
  "epsilon": 0.15,
  "learning_rate": 0.0005,
  "models": {
    "main_network_accuracy": 0.92,
    "target_network_accuracy": 0.89
  },
  "performance": {
    "mission_success_rate": 0.87,
    "average_mission_time_seconds": 1845,
    "energy_efficiency": 0.78
  },
  "last_update": "2026-02-23T10:32:45.123Z"
}
```

### GET /api/v1/memory/short_term
Получить краткосрочную память

**Запрос:**
```bash
curl "http://localhost:8000/api/v1/memory/short_term?limit=20"
```

**Ответ (200 OK):**
```json
{
  "capacity": 1000,
  "current_size": 234,
  "memories": [
    {
      "timestamp": "2026-02-23T10:32:45.123Z",
      "type": "event",
      "content": "Обнаружен объект типа 'автомобиль' на кооординах 55.7558, 37.6173",
      "confidence": 0.95,
      "priority": "high"
    },
    {
      "timestamp": "2026-02-23T10:32:30.123Z",
      "type": "decision",
      "content": "Решено снизить высоту из-за сильного ветра (7.5 м/с)",
      "reasoning": "Ветер превышает пороговые значения",
      "outcome": "successful"
    }
  ]
}
```

### GET /api/v1/memory/long_term/search
Поиск в долгосрочной памяти

**Запрос:**
```bash
curl "http://localhost:8000/api/v1/memory/long_term/search?query=автомобиль&type=detection&limit=10"
```

**Ответ (200 OK):**
```json
{
  "query": "автомобиль",
  "type": "detection",
  "total_results": 42,
  "results": [
    {
      "id": "MEM_2341",
      "timestamp": "2026-02-22T14:30:00.000Z",
      "title": "Обнаружен красный автомобиль",
      "description": "Красный седан, марка Toyota, припаркован на улице",
      "location": {"latitude": 55.7558, "longitude": 37.6173},
      "confidence": 0.96,
      "tags": ["vehicle", "car", "red", "sedan"],
      "associated_photo": "photo_id_2341"
    }
  ]
}
```

### POST /api/v1/memory/add_experience
Добавить опыт в память

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/memory/add_experience \
  -H "Content-Type: application/json" \
  -d '{
    "experience_type": "successful_mission",
    "mission_id": "MISSION_042",
    "duration_seconds": 2700,
    "observations": {
      "wind_speed_avg": 5.2,
      "temperature_avg": 15.2,
      "battery_consumption_percent": 45
    },
    "decisions": [
      "Снизили высоту при усилении ветра",
      "Оптимизировали маршрут для экономии батареи"
    ],
    "outcomes": {
      "success": true,
      "objectives_completed": 12,
      "anomalies": 1
    },
    "lessons_learned": [
      "Сильный ветер требует снижения высоты в 15:30-15:45",
      "Маршрут можно оптимизировать на 5% для этого района"
    ]
  }'
```

**Ответ (201 Created):**
```json
{
  "success": true,
  "experience_id": "EXP_2342",
  "stored_at": "2026-02-23T10:32:45.123Z",
  "indexed": true
}
```

## Субагент и AI

### GET /api/v1/sub_agent/ask
Вопрос к субагенту GPT-4o

**Запрос:**
```bash
curl "http://localhost:8000/api/v1/sub_agent/ask?question=Какой сейчас статус дрона и рекомендуемы следующие действия?"
```

**Ответ (200 OK):**
```json
{
  "question": "Какой сейчас статус дрона и рекомендуемы следующие действия?",
  "response": "Статус дрона: Готов к полёту. Батарея: 78%. Сигнал: Сильный. На основе текущих условий я рекомендую: 1) Планы из-за ветра высоту на 40м вместо 50м. 2) Использовать маршрут с оптимизацией энергии. 3) Проверить наличие обновлений модели обнаружения объектов.",
  "confidence": 0.92,
  "processing_time_ms": 1234,
  "sources": ["current_telemetry", "mission_history", "learned_patterns"]
}
```

### POST /api/v1/sub_agent/analyze_decision
Анализ решения субагентом

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/sub_agent/analyze_decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Снизить высоту полета с 50м до 40м",
    "reason": "Усиливающийся ветер до 7.5 м/с",
    "context": {
      "current_altitude": 50,
      "wind_speed": 7.5,
      "battery": 65,
      "mission_remaining_percent": 30
    },
    "alternative_options": [
      "Вернуться домой",
      "Ждать улучшения погоды"
    ]
  }'
```

**Ответ (200 OK):**
```json
{
  "decision_analysis": {
    "option": "Снизить высоту полета с 50м до 40м",
    "recommendation": "APPROVE",
    "confidence": 0.94,
    "risks": ["Может потребоваться дополнительное время на миссию"],
    "benefits": ["Повышение стабильности", "Снижение нагрузки на моторы"],
    "estimated_impact": "Время миссии +5%, Стабильность +15%"
  },
  "alternatives_ranking": [
    {
      "option": "Снизить высоту полета",
      "score": 0.94
    },
    {
      "option": "Ждать улучшения погоды",
      "score": 0.45
    },
    {
      "option": "Вернуться домой",
      "score": 0.32
    }
  ]
}
```

### POST /api/v1/sub_agent/generate_mission
Генерация миссии субагентом

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/sub_agent/generate_mission \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Обследовать вреемебную зону вокруг координат 55.7558, 37.6173 площадью 500x500 метров, найти все припаркованные машины и сделать фото",
    "drone_type": "quadcopter",
    "weather_conditions": {
      "wind_speed": 5,
      "visibility_km": 10,
      "temperature": 15
    },
    "constraints": {
      "max_altitude": 120,
      "max_mission_time_minutes": 45,
      "battery_safety_percent": 20
    }
  }'
```

**Ответ (201 Created):**
```json
{
  "mission_generated": true,
  "mission_id": "AI_GEN_001",
  "mission_name": "Обследование припаркованных автомобилей",
  "mission_type": "object_detection_survey",
  "waypoints_count": 18,
  "estimated_duration_minutes": 35,
  "objectives": [
    "Картографирование территории",
    "Обнаружение припаркованных транспортных средств",
    "Сбор фотоматериала"
  ],
  "generated_at": "2026-02-23T10:32:45.123Z"
}
```

## Отчеты и история

### POST /api/v1/mission/generate_report
Сгенерировать отчёт о миссии

**Запрос:**
```bash
curl -X POST http://localhost:8000/api/v1/mission/generate_report \
  -H "Content-Type: application/json" \
  -d '{
    "mission_id": "MISSION_042",
    "format": "detailed_narrative",
    "language": "ru",
    "include_sections": [
      "summary",
      "timeline",
      "detections",
      "decisions",
      "telemetry",
      "lessons_learned",
      "recommendations"
    ]
  }'
```

**Ответ (200 OK):**
```json
{
  "report_id": "REPORT_2342",
  "mission_id": "MISSION_042",
  "generated_at": "2026-02-23T10:32:45.123Z",
  "report_text": "ОТЧЁТ О ВЫПОЛНЕНИИ МИССИИ ОБСЛЕДОВАНИЕ РАЙОНА А\n\nДата: 23 февраля 2026\nВремя: 09:00-09:45 МСК\nДлительность: 45 минут\n\nХОД ВЫПОЛНЕНИЯ:\n\n09:00 - Взлёт с координат 55.7558, 37.6173\n- Высота достигнута: 50 метров\n- Статус: успешно\n\n09:15 - Обнаружен объект: красный автомобиль\n- Координаты: 55.7560, 37.6175\n- Тип: седан\n- Марка: предположительно Toyota\n- Уверенность: 96%\n- Действие: фотографирование\n\n09:32 - Обнаружено усиление ветра (7.5 м/с)\n- Решение: снизить высоту до 40 метров\n- Причина: обеспечение стабильности полёта\n- Результат: стабильность восстановлена\n\n09:45 - Завершение миссии\n- Статус: успешно\n- Все задачи выполнены\n- Объектов обнаружено: 8\n- Фотографий сделано: 73\n\nСТАТИСТИКА:\n\nМетеорология:\n- Минимальная температура: 14.5 C\n- Максимальная температура: 16.2 С\n- Среднее значение ветра: 5.2 м/с\n- Влажность: 58-65%\n\nПотребление энергии:\n- Начальный уровень батареи: 95%\n- Конечный уровень батареи: 50%\n- Потреблено: 45%\n- Эффективність: хорошо\n\nОБНАРУЖЕННЫЕ ОБЪЕКТЫ:\n\n1. Красный седан Toyota (координаты: 55.7560, 37.6175, уверенность: 96%)\n2. Белый внедорожник (координаты: 55.7562, 37.6180, уверенность: 92%)\n3. Серебристый хэтчбек (координаты: 55.7564, 37.6185, уверенность: 88%)\n...\n\nРЕКОМЕНДАЦИИ:\n\n1. В будущих миссиях в этом районе в 15:00-16:00 рекомендуется снизить высоту полёта на 10 метров\n2. Предложить модель обнаружения объектов для улучшения распознавания припаркованных коммерческих транспортных средств\n3. Учитывая положительные результаты, рекомендуется повторить обследование на той же территории через 7 дней\n",
  "report_url": "https://api.example.com/reports/REPORT_2342.pdf"
}
```

### GET /api/v1/events/log
Получить журнал событий

**Запрос:**
```bash
curl "http://localhost:8000/api/v1/events/log?start_time=2026-02-23T08:00:00Z&end_time=2026-02-23T12:00:00Z&event_type=DETECTION,DECISION&limit=50"
```

**Ответ (200 OK):**
```json
{
  "total_events": 234,
  "limit": 50,
  "events": [
    {
      "timestamp": "2026-02-23T10:31:10.123Z",
      "event_type": "DETECTION",
      "mission_id": "MISSION_042",
      "description": "Обнаружен красный автомобиль",
      "details": {
        "object_type": "vehicle",
        "specifics": "sedan",
        "color": "red",
        "confidence": 0.96,
        "location": {"latitude": 55.7560, "longitude": 37.6175}
      },
      "severity": "info"
    },
    {
      "timestamp": "2026-02-23T10:32:15.123Z",
      "event_type": "DECISION",
      "mission_id": "MISSION_042",
      "description": "Решено снизить высоту полёта",
      "details": {
        "reason": "Усиливающийся ветр",
        "from_altitude": 50,
        "to_altitude": 40,
        "decision_confidence": 0.94
      },
      "severity": "warning"
    }
  ]
}
```

## WebSocket реал-тайм

### WebSocket /ws/telemetry
Подключение к потоку реал-тайм телеметрии

**JavaScript пример:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/telemetry');

ws.onopen = (event) => {
  console.log('Connected to telemetry stream');
};

ws.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  console.log('Altitude:', telemetry.altitude);
  console.log('Battery:', telemetry.battery);
  console.log('Speed:', telemetry.speed);
  // Обновить UI в реальном времени
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log('Disconnected from telemetry stream');
};
```

**Сообщение WebSocket:**
```json
{
  "timestamp": "2026-02-23T10:32:46.123Z",
  "altitude": 45.5,
  "latitude": 55.7558,
  "longitude": 37.6173,
  "speed": 5.2,
  "heading": 90,
  "battery": 78,
  "wind_speed": 3.5,
  "temperature": 15.2,
  "gps_satellites": 12,
  "mission_progress_percent": 45
}
```

### WebSocket /ws/events
Подключение к потоку событий

**Python пример:**
```python
import asyncio
import websockets
import json

async def subscribe_to_events():
    async with websockets.connect('ws://localhost:8000/ws/events') as ws:
        while True:
            event = await ws.recv()
            data = json.loads(event)
            print(f"Event: {data['event_type']}")
            print(f"Description: {data['description']}")
            print(f"Timestamp: {data['timestamp']}")
            print("---")
```

**Сообщение WebSocket:**
```json
{
  "event_id": "EVT_234",
  "timestamp": "2026-02-23T10:31:10.123Z",
  "event_type": "DETECTION",
  "mission_id": "MISSION_042",
  "description": "Обнаружен объект",
  "severity": "info",
  "data": {
    "object_type": "vehicle",
    "confidence": 0.96,
    "location": {"latitude": 55.7560, "longitude": 37.6175}
  }
}
```

## Коды ошибок

### Стандартные HTTP коды

| Код | Описание | Пример |
|-----|---------|--------|
| 200 | OK | Успешный запрос |
| 201 | Created | Ресурс создан |
| 204 | No Content | Успешно, без содержимого |
| 400 | Bad Request | Неверный формат запроса |
| 401 | Unauthorized | Требуется аутентификация |
| 403 | Forbidden | Доступ запрещен |
| 404 | Not Found | Ресурс не найден |
| 409 | Conflict | Конфликт (напр., миссия уже выполняется) |
| 429 | Too Many Requests | Слишком много запросов |
| 500 | Internal Server Error | Ошибка сервера |
| 502 | Bad Gateway | Сервер недоступен |
| 503 | Service Unavailable | Сервис временно недоступен |

### Ошибка 400 - Bad Request
```json
{
  "error": "bad_request",
  "message": "Invalid mission parameters",
  "details": {
    "field": "altitude",
    "reason": "Must be between 10 and 120 meters"
  }
}
```

### Ошибка 409 - Conflict
```json
{
  "error": "mission_already_running",
  "message": "Cannot start new mission while one is already executing",
  "current_mission": "MISSION_042",
  "suggestion": "Stop the current mission first or wait for it to complete"
}
```

### Ошибка 500 - Server Error
```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred",
  "error_id": "ERR_2341",
  "timestamp": "2026-02-23T10:32:45.123Z"
}
```

## Примеры использования

### Пример 1: Полный цикл миссии

```bash
#!/bin/bash

API="http://localhost:8000/api/v1"

# 1. Проверить статус
echo "1. Проверка статуса агента..."
curl $API/agent/status

# 2. Инициализировать агента
echo -e "\n2. Инициализация агента..."
curl -X POST $API/agent/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "drone_type": "quadcopter",
    "simulator_enabled": true
  }'

# 3. Получить список инструментов
echo -e "\n3. Список инструментов..."
curl $API/tools

# 4. Генерировать миссию через субагент
echo -e "\n4. Генерация миссии..."
curl -X POST $API/sub_agent/generate_mission \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Обследовать район",
    "drone_type": "quadcopter"
  }'

# 5. Запустить миссию
echo -e "\n5. Запуск миссии..."
curl -X POST $API/mission/start \
  -H "Content-Type: application/json" \
  -d '{
    "mission_id": "TEST_001",
    "mission_type": "survey"
  }'

# 6. Мониторить в реальном времени
echo -e "\n6. Мониторинг телеметрии (5 секунд)..."
timeout 5s curl --no-buffer $API/telemetry/stream || true

# 7. Получить статус миссии
echo -e "\n7. Статус миссии..."
curl $API/mission/status

# 8. Генерировать отчёт
echo -e "\n8. Генерация отчёта..."
curl -X POST $API/mission/generate_report \
  -H "Content-Type: application/json" \
  -d '{
    "mission_id": "TEST_001",
    "format": "pdf"
  }'
```

### Пример 2: Интеграция с Bash скриптом

```bash
#!/bin/bash

source config.sh

# Функция для выполнения команды
execute_command() {
  local cmd=$1
  local params=$2
  
  curl -X POST $API/command \
    -H "Content-Type: application/json" \
    -d "{
      \"command\": \"$cmd\",
      \"parameters\": $params
    }"
}

# Выполнить последовательность команд
echo "Начинаем миссию..."
execute_command "arm" '{"check_battery": true}'
sleep 2
execute_command "takeoff" '{"altitude": 50}'
sleep 3
execute_command "goto" '{"x": 100, "y": 100, "z": 50}'
sleep 5
execute_command "land" '{}'

echo "Миссия завершена!"
```

---

**Версия:** 3.0.0  
**Обновлено:** 23 февраля 2026  
**Поддержка:** support@cobaai.com
