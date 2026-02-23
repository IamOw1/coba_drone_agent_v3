# 📚 Интеграция с симуляторами

Полное руководство по настройке и использованию всех 5 поддерживаемых симуляторов для COBA AI Drone Agent v3.

## 📋 Содержание

1. [AirSim](#airsim)
2. [Grid Simulator](#grid)
3. [SIMNET](#simnet)
4. [SkyRover](#skyrover)
5. [Unreal Engine 5+](#unreal-engine)
6. [Переключение между симуляторами](#переключение)

---

## AirSim

### Что это?
- **Разработчик**: Microsoft
- **Язык**: C++ с Python API
- **Платформа**: Windows, Linux, macOS
- **Особенности**: Быстрое моделирование, интеграция с Unreal Engine, реалистичная физика
- **Скорость**: Самый быстрый из всех (можно ускорить в 5-10 раз)

### Установка

#### 1. Установка Unreal Engine 4.27+ или 5.x
```bash
# Скачайте с https://www.unrealengine.com/download
# Или установите через Epic Games Launcher
```

#### 2. Клонирование и сборка AirSim
```bash
git clone https://github.com/Microsoft/AirSim.git
cd AirSim
./build.sh  # Linux/Mac
# или build.cmd на Windows
```

#### 3. Создание проекта в UE
```bash
cd AirSim/UE4Project
# Откройте в Unreal Engine и скомпилируйте
```

#### 4. Python пакет
```bash
pip install airsim
```

### Конфигурация

Добавьте в `config/config.yaml`:
```yaml
simulators:
  airsim:
    enabled: true
    host: localhost
    port: 41451
    vehicle_name: "Drone1"
    start_location:
      x: 0
      y: 0
      z: 0
```

### Использование

```python
from sim.simulator_manager import SimulatorManager, SimulatorType

# Инициализация
manager = SimulatorManager(config)
await manager.initialize(SimulatorType.AIRSIM)

# Базовые команды
await manager.arm_drone()
await manager.takeoff(50)  # Взлёт на 50 метров
await manager.move_to(100, 100, 50, speed=10)
await manager.land()

# Получение телеметрии
telemetry = manager.get_telemetry()
print(f"Позиция: {telemetry['position']}")
print(f"Батарея: {telemetry.get('battery', {}).get('remaining_percent')}")
```

### Примеры скриптов

#### Полёт по квадрату
```python
async def fly_square(manager):
    await manager.arm_drone()
    await manager.takeoff(50)
    
    # Полёт к углам квадрата
    points = [(100, 100, 50), (100, -100, 50), 
              (-100, -100, 50), (-100, 100, 50)]
    
    for point in points:
        await manager.move_to(*point, speed=5)
    
    await manager.land()
```

#### Получение изображений с камеры
```python
# AirSim позволяет получать изображения разных типов:
# - RGB
# - Segmentation (сегментация сцены)
# - Optical flow
# - Depth

from airsim import Image as AirSimImage

client = airsim.MultirotorClient()
responses = client.simGetImages([
    airsim.ImageRequest(0, airsim.ImageType.Scene),
    airsim.ImageRequest(0, airsim.ImageType.DepthPlanar)
])
```

---

## Grid Simulator

### Что это?
- **Разработчик**: JSC Radiuss (Россия)
- **Особенности**: Высокая точность физики, поддержка MAVLink, русская документация
- **Платформа**: Windows, Linux
- **Применение**: Реалистичное моделирование для исследований

### Установка

#### 1. Загрузка Grid Simulator
```bash
# Скачайте с https://grid.radiuss.io или свяжитесь с разработчиком

# Или установите через пакет (если доступен)
pip install grid-sdk
```

#### 2. Запуск симулятора
```bash
/path/to/grid/simulator --headless --listen 0.0.0.0:4446
```

### Конфигурация

```yaml
simulators:
  grid:
    enabled: true
    host: localhost
    port: 4446
    vehicle_name: "Drone1"
    mavlink_port: 14550
    protocol: mavlink
```

### Использование

```python
from sim.simulator_manager import SimulatorManager, SimulatorType

manager = SimulatorManager(config)
await manager.initialize(SimulatorType.GRID)

# Команды
await manager.arm_drone()
await manager.takeoff(100)  # Взлёт на 100 м
await manager.move_to(200, 200, 100, speed=5)

# Grid-специфичные команды
await manager.grid_set_yaw(45)  # Установить курс 45 градусов

# Получение телеметрии
telemetry = manager.get_telemetry()
```

### Особенности

- **MAVLink протокол**: Полная совместимость с PX4, Ardupilot
- **Реализм физики**: Учитывает ветер, турбулентность, эффекты ротора
- **Множество дронов**: Поддержка роевого моделирования
- **Сохранение логов**: Автоматическая запись всех команд и телеметрии

---

## SIMNET

### Что это?
- **Тип**: Облачная платформа
- **Доступ**: REST API + WebSocket
- **Особенности**: Не требует локальной установки, реальные метеоусловия
- **Применение**: Большие группы дронов, облачные вычисления

### Установка

#### 1. Регистрация
```
1. Перейти на https://simnet.cloud
2. Создать аккаунт
3. Получить API ключ
```

#### 2. Конфигурация

```yaml
simulators:
  simnet:
    enabled: true
    api_url: https://api.simnet.cloud
    api_key: "YOUR_API_KEY_HERE"
    project_id: "project_123"
    drone_id: "drone_1"
    scenario: "urban_delivery"
```

### Использование

```python
manager = SimulatorManager(config)
await manager.initialize(SimulatorType.SIMNET)

# Работа со сценариями
scenarios = await manager.simnet_get_scenarios()
print(f"Доступные сценарии: {scenarios}")

# Смена сценария
await manager.simnet_set_weather({
    'wind_speed': 5,
    'wind_direction': 90,
    'temperature': 25,
    'visibility': 1000
})

# Стандартные команды
await manager.takeoff(50)
await manager.move_to(500, 500, 50)
```

### Примеры сценариев в SIMNET

- `urban_delivery` - доставка в городе
- `rural_operations` - операции на природе
- `mountain_crossing` - полёт в горах
- `coastal_surveillance` - наблюдение над побережьем
- `custom_scenario` - пользовательский сценарий

### Преимущества облачного моделирования

```python
# 1. Множество дронов одновременно
await manager.simnet_multi_drone_mission([
    {'drone_id': 'drone_1', 'mission': mission1},
    {'drone_id': 'drone_2', 'mission': mission2},
    {'drone_id': 'drone_3', 'mission': mission3},
])

# 2. Реальные метеоусловия
weather = await manager.simnet_get_weather()  # Получить текущую погоду

# 3. Запись и публикация результатов
await manager.simnet_save_and_share_results()
```

---

## SkyRover

### Что это?
- **Тип**: Гибридная платформа (наземный + воздушный)
- **Интерфейс**: USB/Bluetooth/Serial
- **Особенности**: Модульная архитектура, поддержка реальных датчиков
- **Применение**: Тестирование на реальном оборудовании

### Установка

#### 1. Физическое подключение
```
1. Подключите SkyRover через USB
2. Проверьте порт: /dev/ttyUSB0 (Linux) или COM3 (Windows)
3. Установите драйверы (если требуется)
```

#### 2. Python библиотека
```bash
pip install pyserial
```

### Конфигурация

```yaml
simulators:
  skyrover:
    enabled: true
    port: /dev/ttyUSB0  # или COM3 на Windows
    baudrate: 115200
    vehicle_id: 1
    mode: air_mode  # или ground_mode, hover
```

### Использование

```python
manager = SimulatorManager(config)
await manager.initialize(SimulatorType.SKYROVER)

# Смена режима
await manager.skyrover_set_mode('air_mode')

# Воздушный режим
await manager.arm_drone()
await manager.takeoff(20)
await manager.move_to(50, 50, 20)

# Переключение в наземный режим
await manager.skyrover_set_mode('ground_mode')

# Наземное движение
await manager.skyrover_move_forward(distance=100, speed=1.0)
```

### Особенности SkyRover

```python
# Управление отдельными моторами
await manager.skyrover_set_motor_speed(motor_id=0, speed=2500)

# Калибровка
await manager.skyrover_calibrate_imu()

# Получение статуса батареи
battery_status = manager.get_telemetry()['battery']
print(f"Напряжение: {battery_status['voltage']}V")
```

---

## Unreal Engine 5+

### Что это?
- **Версия**: UE 5.0 и выше
- **Графика**: Nanite (максимальная реалистичность)
- **Интерфейс**: HTTP REST API + WebSocket
- **Особенности**: Photo-realistic, динамическое окружение, камеры высокого разрешения

### Установка

#### 1. Скачайте Unreal Engine 5
```bash
# С официального сайта https://www.unrealengine.com/
# Или используйте Epic Games Launcher
```

#### 2. Создание проекта дрона в UE5

```bash
# Создайте новый проект
# Выберите: Blank Project → 3D → С C++

# Добавьте мой плагин для дронов (или используйте готовый):
cd Plugins
git clone https://github.com/yourusername/DronePlugin.git
cd ..

# Скомпилируйте проект
./GenerateProjectFiles.sh
make
```

#### 3. Запуск сервера симулятора

```bash
# В Unreal Editor:
# Tools → Launch Drone Server → Start

# Или через командную строку:
/path/to/ue5/project/Binaries/Linux/ProjectName \
  -http_port=8000 \
  -ws_port=8001 \
  -headless
```

### Конфигурация

```yaml
simulators:
  unreal_engine:
    enabled: true
    host: localhost
    http_port: 8000
    websocket_port: 8001
    drone_id: 0
    start_location: [0, 0, 100]
    graphics_quality: Ultra  # Low, Medium, High, Ultra
```

### Использование

```python
manager = SimulatorManager(config)
await manager.initialize(SimulatorType.UNREAL_ENGINE)

# Базовые команды
await manager.takeoff(50)
await manager.move_to(100, 100, 50)
await manager.land()

# UE-специфичные команды
await manager.ue_set_graphics_quality('High')

# Захват видео
frame = await manager.ue_capture_camera()  # Получить текущий кадр
await manager.ue_take_screenshot('screenshot.png')

# Запись видео
await manager.ue_record_video(duration=30, filename='flight.mp4')

# Программное создание препятствий
await manager.ue_spawn_obstacle(x=200, y=200, z=50, model='Building_01')
```

### Примеры UE-специфичного кода

#### Фото-реалистичный полёт с записью
```python
async def photo_mission():
    manager = SimulatorManager(config)
    await manager.initialize(SimulatorType.UNREAL_ENGINE)
    
    # Установка оптимальных граф параметров
    await manager.ue_set_graphics_quality('Ultra')
    
    # Запись видео
    await manager.ue_record_video(duration=120, filename='output.mp4')
    
    # Полёт
    await manager.arm_drone()
    await manager.takeoff(100)
    
    # Делаем скриншоты на разных позициях
    for i, (x, y) in enumerate([(100,100), (200,200), (300,300)]):
        await manager.move_to(x, y, 100)
        await manager.ue_take_screenshot(f'screenshot_{i}.png')
    
    await manager.land()
```

#### Динамическое окружение
```python
async def dynamic_environment():
    # Изменение погоды во время полёта
    await manager.set_weather({
        'temperature': 25,
        'wind_speed': 5,
        'visibility': 1000
    })
    
    # Добавление препятствий
    for i in range(3):
        await manager.ue_spawn_obstacle(
            x=i * 100,
            y=i * 100,
            z=50,
            model='TreeForest_01'
        )
    
    # Полёт между препятствиями
    await manager.move_to(250, 250, 75)
```

---

## Переключение между симуляторами

### Динамическое переключение

```python
async def switch_test():
    manager = SimulatorManager(config)
    
    # Начинаем с AirSim
    await manager.initialize(SimulatorType.AIRSIM)
    print(f"Активный: {manager.get_active_simulator()}")
    
    # Выполняем миссию
    await manager.takeoff(50)
    await manager.move_to(100, 100, 50)
    
    # Переключаемся на Grid
    await manager.switch_simulator(SimulatorType.GRID)
    print(f"Активный: {manager.get_active_simulator()}")
    
    # Выполняем ту же миссию в Grid
    await manager.takeoff(100)
    await manager.move_to(100, 100, 100)
```

### Сравнение симуляторов

```python
async def compare_simulators():
    simulators = [
        SimulatorType.AIRSIM,
        SimulatorType.GRID,
        SimulatorType.UNREAL_ENGINE,
    ]
    
    manager = SimulatorManager(config)
    
    for sim in simulators:
        info = manager.get_simulator_info(sim)
        print(f"\n{info['name']}:")
        print(f"  Описание: {info['description']}")
        print(f"  Возможности: {', '.join(info['features'])}")
        
        await manager.initialize(sim)
        
        # Выполняем тест
        await manager.takeoff(50)
        telemetry = manager.get_telemetry()
        print(f"  Телеметрия: {telemetry['position']}")
        
        await manager.land()
        await manager.disconnect()
```

### Список доступных симуляторов в коде

```python
# Получить список всех доступных симуляторов
available = manager.get_available_simulators()
print(f"Доступно симуляторов: {available}")
# Output: ['airsim', 'grid', 'simnet', 'skyrover', 'unreal_engine']

# Информация обо всех
await manager.print_simulator_status()
```

---

## 🔧 Решение проблем

### AirSim не запускается
```bash
# Проверьте, что Unreal Engine установлен
which UE4Editor  # или UE5Editor

# Пересоберите AirSim
cd AirSim && ./build.sh
```

### Grid не подключается
```bash
# Проверьте, что Grid запущен
netstat -an | grep 4446

# Запустите Grid вручную
/path/to/grid/simulator --listen 0.0.0.0:4446
```

### SIMNET требует Internet
- Убедитесь, что у вас есть доступ в Интернет
- Проверьте API ключ в конфигурации
- Свяжитесь с поддержкой SIMNET

### SkyRover не подключается к USB
```bash
# Linux: проверьте порт
ls /dev/ttyUSB*

# Измените права
sudo chmod 666 /dev/ttyUSB0

# Перезагрузитесь
sudo systemctl restart udev
```

### Unreal Engine медленно запускается
- Установите более свежую видеокарту NVIDIA (RTX) для лучшей поддержки
- Уменьшите качество графики: `graphics_quality: Low`
- Запустите в headless режиме (без GUI)

---

## 📊 Рекомендации по использованию

| Случай использования | Рекомендуемый симулятор |
|---|---|
| Быстрое прототипирование | **AirSim** |
| Исследование физики | **Grid** |
| Облачные вычисления | **SIMNET** |
| Реальное оборудование | **SkyRover** |
| Максимальный реализм | **Unreal Engine 5+** |
| Тестирование логики | Любой |

---

## 📞 Поддержка и ресурсы

- **AirSim**: https://github.com/Microsoft/AirSim
- **Grid**: https://grid.radiuss.io/
- **SIMNET**: https://simnet.cloud
- **SkyRover**: https://skyrover.io/
- **Unreal Engine**: https://www.unrealengine.com/

---

**Последнее обновление**: 23 февраля 2026  
**Версия**: 1.0
