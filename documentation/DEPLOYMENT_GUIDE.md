# 🚀 Полное руководство по развертыванию COBA AI Drone Agent v3

Всеобъемлющее пошаговое руководство по развертыванию системы во всех конфигурациях.

**Оглавление:**
1. [Требования](#требования)
2. [Быстрый старт](#быстрый-старт)
3. [Windows развертывание](#windows)
4. [Linux развертывание](#linux)
5. [macOS развертывание](#macos)
6. [Docker развертывание](#docker)
7. [Облачное развертывание](#облачное-развертывание)
8. [Разработка локально](#разработка-локально)

---

## Требования

### Минимальные требования
- **ОС**: Windows 10+, Ubuntu 20.04+, macOS 11+
- **Python**: 3.8+
- **RAM**: 8 GB минимум (16 GB рекомендуется)
- **GPU** (опционально): NVIDIA с CUDA 11.8+ для ускорения ML
- **Место на диске**: 5 GB для системы + 10 GB для симуляторов

### Рекомендуемые требования
- **ОС**: Ubuntu 22.04 LTS или Windows 11
- **CPU**: Intel i7/Ryzen 7+ или выше
- **GPU**: NVIDIA RTX 2080+ / A100+ (для UE5)
- **RAM**: 32 GB
- **Место**: SSD 20 GB+
- **Интернет**: 10 Mbps (для облачных функций)

---

## Быстрый старт

### 1. Клонирование проекта

```bash
git clone https://github.com/IamOw1/coba_drone_agent_v3.git
cd coba_drone_agent_v3
```

### 2. Создание виртуального окружения

#### Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### 3. Установка зависимостей

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

А### 4. Конфигурация

```bash
cp .env.example .env
# Отредактируйте .env и добавьте свои параметры
nano .env
```

### 5. Запуск

```bash
# Опция 1: Запустить всё вместе
python main.py all

# Опция 2: Запустить отдельные компоненты
python main.py agent       # Только агент
python main.py api         # REST API
python main.py dashboard   # Streamlit дашборд
python main.py simulator   # Симулятор (AirSim)

# Или используйте скрипт запуска
chmod +x run.sh
./run.sh all
```

---

## Windows

### Метод 1: Установка вручную

#### Шаг 1: Установка Python
```
1. Скачайте Python 3.10+ с python.org
2. При установке ОБЯЗАТЕЛЬНО отметьте "Add Python to PATH"
3. Проверьте установку:
   python --version
```

#### Шаг 2: Клонирование репозитория
```cmd
# Используя Git
git clone https://github.com/IamOw1/coba_drone_agent_v3.git
cd coba_drone_agent_v3

# Или скачайте ZIP с GitHub и распакуйте
```

#### Шаг 3: Создание виртуального окружения
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### Шаг 4: Установка зависимостей
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

#### Шаг 5: Конфигурация
```cmd
copy .env.example .env
# Отредактируйте .env в любом текстовом редакторе
notepad .env
```

#### Шаг 6: Запуск
```cmd
# Запустить всё
python main.py all

# Или отдельные компоненты
python main.py api         # API на http://localhost:8000
python main.py dashboard   # Дашборд на http://localhost:8501
```

### Метод 2: Использование batch скрипта

```batch
@echo off
title COBA AI Drone Agent v3

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Запуск всех компонентов
start "Agent" python main.py agent
start "API" python main.py api
start "Dashboard" python main.py dashboard

echo All components started. Opening dashboard...
timeout /t 3
start http://localhost:8501
```

Сохраните как `run_all.bat` и запустите двойным кликом.

### Установка реального дрона на Windows

```cmd
# 1. Установите драйверы
# - Скачайте драйвер MAVLink для вашего автопилота
# - Установите драйвер USB

# 2. Подключите дрон через USB/Serial

# 3. Проверьте порт в диспетчере устройств
# - Должен быть вида COM3, COM4 и т.д.

# 4. Обновите config.yaml
# hardware:
#   mavlink:
#     port: COM3
#     baudrate: 57600

# 5. Запустите с поддержкой реального дрона
python main.py real_drone
```

---

## Linux

### Ubuntu 20.04+ / Debian

#### Шаг 1: Установка зависимостей системы
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    build-essential \
    git \
    curl \
    libopencv-dev \
    libssl-dev \
    libffi-dev
```

#### Шаг 2: Клонирование проекта
```bash
git clone https://github.com/IamOw1/coba_drone_agent_v3.git
cd coba_drone_agent_v3
```

#### Шаг 3: Python окружение
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

#### Шаг 4: Установка зависимостей Python
```bash
pip install -r requirements.txt
```

#### Шаг 5: Конфигурация
```bash
cp .env.example .env
nano .env
```

#### Шаг 6: Запуск

##### Вариант 1: Прямой запуск
```bash
# Всё вместе
python main.py all

# Отдельные компоненты в разных терминалах
python main.py agent &
python main.py api &
python main.py dashboard &
```

##### Вариант 2: Systemd сервис

Создайте `/etc/systemd/system/coba-agent.service`:
```ini
[Unit]
Description=COBA AI Drone Agent v3
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/coba_drone_agent_v3
EnvironmentFile=/home/ubuntu/coba_drone_agent_v3/.env
ExecStart=/home/ubuntu/coba_drone_agent_v3/venv/bin/python main.py all
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск сервиса:
```bash
sudo systemctl daemon-reload
sudo systemctl enable coba-agent
sudo systemctl start coba-agent
sudo systemctl status coba-agent
```

##### Вариант 3: Screen сессия (для фонового запуска)
```bash
# Установка screen
sudo apt-get install -y screen

# Запуск в фоне
screen -d -m -S coba_agent python main.py all

# Просмотр логов
screen -r coba_agent

# Выход из screen: Ctrl+A, потом D
```

#### Работа с реальным дроном на Linux

```bash
# 1. Проверьте USB устройства
ls /dev/ttyUSB*

# 2. Дайте права доступа
sudo chmod 666 /dev/ttyUSB0

# 3. Добавьте пользователя в группу dialout
sudo usermod -a -G dialout $USER
# Требуется перезагрузка

# 4. Отредактируйте config.yaml
hardware:
  mavlink:
    port: /dev/ttyUSB0
    baudrate: 57600

# 5. Запустите
source venv/bin/activate
python main.py all
```

---

## macOS

### Установка для Intel

```bash
# 1. Установка Homebrew (если ещё нет)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Зависимости
brew install python@3.10 git opencv

# 3. Клонирование
git clone https://github.com/IamOw1/coba_drone_agent_v3.git
cd coba_drone_agent_v3

# 4. Виртуальное окружение
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# 5. Зависимости Python
pip install -r requirements.txt

# 6. Конфигурация
cp .env.example .env
nano .env

# 7. Запуск
python main.py all
```

### Установка для Apple Silicon (M1/M2/M3)

```bash
# 1. Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Зависимости (arm64 версии)
brew install python@3.10 git
brew install --HEAD opencv

# 3-7. Как выше

# ВНИМАНИЕ: Некоторые пакеты требуют Rosetta работают через эмуляцию:
softwareupdate --install-rosetta

# Если numpy/torch дают ошибки, переустановите:
pip install --force-reinstall --no-binary numpy numpy==1.24.0
pip install torch torchvision torchaudio
```

### Использование реального дрона на macOS

```bash
# 1. Найдите USB порт
ls /dev/cu.* /dev/tty.*

# 2. Установите драйверы (если требуется)
# Для Arduino: CH340 driver
# Для FTDI: FTDI VCP driver

# 3. config.yaml
hardware:
  mavlink:
    port: /dev/cu.usbserial-14220  # ваш порт
    baudrate: 57600

# 4. Запуск
source venv/bin/activate
python main.py all
```

---

## Docker

### Установка Docker

#### Windows / macOS
Скачайте Docker Desktop: https://www.docker.com/products/docker-desktop

#### Linux
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo bash get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### Сборка Docker образа

```bash
# Из репозитория COBA
docker build -t coba-ai-drone:latest .

# С кастомным тегом
docker build -t myregistry/coba-ai-drone:v3.0 .
```

### Запуск Docker контейнера

#### Вариант 1: Все компоненты
```bash
docker run -d \
  --name coba-ai \
  -p 8000:8000 \
  -p 8501:8501 \
  -v /path/to/data:/app/data \
  -e OPENAI_API_KEY=your_key_here \
  coba-ai-drone:latest
```

#### Вариант 2: Docker Compose (рекомендуется)

Создайте `docker-compose.yml`:
```yaml
version: '3.8'

services:
  agent:
    image: coba-ai-drone:latest
    container_name: coba-agent
    command: python main.py agent
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    networks:
      - coba-net
    restart: unless-stopped

  api:
    image: coba-ai-drone:latest
    container_name: coba-api
    command: python main.py api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    networks:
      - coba-net
    depends_on:
      - agent
    restart: unless-stopped

  dashboard:
    image: coba-ai-drone:latest
    container_name: coba-dashboard
    command: python main.py dashboard
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    networks:
      - coba-net
    depends_on:
      - agent
    restart: unless-stopped

networks:
  coba-net:
    driver: bridge
```

Запуск:
```bash
docker-compose up -d
```

Просмотр логов:
```bash
docker-compose logs -f
```

Остановка:
```bash
docker-compose down
```

### Docker с GPU поддержкой

```bash
docker run -d \
  --name coba-ai \
  --gpus all \
  -p 8000:8000 \
  -p 8501:8501 \
  coba-ai-drone:latest
```

Убедитесь, что установлены:
- NVIDIA Docker runtime: https://github.com/NVIDIA/nvidia-docker

---

## Облачное развертывание

### AWS Deployment

#### 1. Создание EC2 инстанса
```bash
# Выберите:
# - AMI: Ubuntu 22.04 LTS
# - Тип: t3.xlarge или p3.2xlarge (с GPU)
# - Хранилище: 30 GB gp3
# - Security Group: откройте порты 8000, 8501, 22
```

#### 2. Подключение и установка
```bash
ssh -i your-key.pem ubuntu@your-instance-ip

# На инстансе:
sudo apt-get update && sudo apt-get upgrade -y

# Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo bash get-docker.sh
sudo usermod -aG docker ubuntu

# Клонируйте проект
git clone https://github.com/IamOw1/coba_drone_agent_v3.git
cd coba_drone_agent_v3

# Запустите Docker Compose
docker-compose up -d
```

#### 3. Получение доступа
- API: http://ваш-instance-ip:8000/docs
- Dashboard: http://ваш-instance-ip:8501

### Google Cloud Run (Serverless)

```bash
# 1. Установка gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# 2. Сборка и загрузка образа
gcloud builds submit --tag gcr.io/your-project/coba-ai

# 3. Развертывание
gcloud run deploy coba-ai \
  --image gcr.io/your-project/coba-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your_key
```

### Azure Container Instances

```bash
# 1. Создание ресурс группы
az group create --name cobaGroup --location eastus

# 2. Развертывание контейнера
az container create \
  --resource-group cobaGroup \
  --name coba-ai \
  --image coba-ai-drone:latest \
  --ports 8000 8501 \
  --environment-variables OPENAI_API_KEY=your_key
```

---

## Разработка локально

### С VS Code

#### 1. Установка расширений
- Python
- Pylance
- Docker
- REST Client

#### 2. Настройка .vscode/settings.json
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.pylintPath": "${workspaceFolder}/venv/bin/pylint",
    "python.formatting.provider": "black",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

#### 3. Конфигурация запуска .vscode/launch.json
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Main Script",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "args": ["all"]
        },
        {
            "name": "Python: API",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "args": ["api"]
        }
    ]
}
```

### С PyCharm

1. Откройте проект в PyCharm
2. Конфигурируйте interpreter: Settings → Project → Python Interpreter
3. Выберите venv из папки проекта
4. Запуск: Run → Run 'main' (Shift+F10)

### Тестирование

```bash
# Запуск тестов
pytest tests/

# С покрытием
pytest --cov=agent tests/

# Только unit тесты
pytest tests/unit/

# Только интеграционные тесты
pytest tests/integration/
```

### Форматирование и проверка кода

```bash
# Форматирование (black)
black .

# Lint проверка (pylint)
pylint agent/ api/ tools/

# Type check (mypy)
mypy agent/ api/ tools/

# Все вместе
black . && pylint agent/ && mypy agent/
```

---

## 🔍 Проверка установки

После установки запустите проверку:

```bash
python check_system.py
```

Результат должен быть:
```
✅ Python 3.8+
✅ PyTorch установлен
✅ FastAPI установлен
✅ Streamlit установлен
✅ Все зависимости установлены
✅ Конфигурация валидна
🎉 СИСТЕМА ГОТОВА К РАБОТЕ
```

---

## 📞 Решение проблем

### Проблема: "Permission denied" при запуске на Linux
**Решение**:
```bash
chmod +x main.py run.sh
```

### Проблема: Port already in use
**Решение**:
```bash
# Найти процесс на порту 8000
lsof -i :8000

# Убить процесс
kill -9 <PID>

# Или используйте другой порт в config.yaml
```

### Проблема: Out of Memory
**Решение**:
```bash
# Уменьшьте размер моделей в config.yaml
# Отключите GPU обучение
# Используйте меньший размер батча
```

### Проблема: Не работает GPU
**Решение**:
```bash
# Проверьте CUDA
nvidia-smi

# Переустановите torch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 📚 Дополнительные ресурсы

- [Документация API](./API_FULL_REFERENCE.md)
- [Инструкции по симуляторам](./SIMULATORS_INTEGRATION.md)
- [Архитектура системы](./architecture/ARCHITECTURE.md)
- [Разработка](./developer_guides/)

---

**Успешного развертывания! 🚀**

Если у вас есть вопросы, создайте issue на GitHub.
