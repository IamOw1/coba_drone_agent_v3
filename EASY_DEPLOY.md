# 🚀 Упрощенное развертывание (EXE + Docker)

## Цель
Сделать запуск проекта максимально простым — одним кликом.

---

## Вариант 1: Создание EXE файла (для Windows)

### Что получится
Файл `COBA_AI_Drone_Agent.exe` — запускается двойным кликом, не требует Python.

### Как создать

#### Шаг 1: Установите PyInstaller
```bash
pip install pyinstaller
```

#### Шаг 2: Создайте файл `main.spec`
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/config.yaml', 'config'),
        ('web_interface/*', 'web_interface'),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'streamlit',
        'torch',
        'openai',
        'yaml',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='COBA_AI_Drone_Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Создайте иконку
)
```

#### Шаг 3: Соберите EXE
```bash
pyinstaller main.spec --onefile
```

#### Шаг 4: Результат
Файл `dist/COBA_AI_Drone_Agent.exe` — готов к распространению!

### Как пользователю запустить
1. Скачать `COBA_AI_Drone_Agent.exe`
2. Создать файл `.env` рядом с EXE
3. Добавить `OPENAI_API_KEY=ваш_ключ`
4. Двойной клик по EXE
5. Открыть браузер: http://localhost:8501

---

## Вариант 2: Docker (для всех платформ)

### Что получится
Контейнер, который работает везде одинаково.

### Файл `Dockerfile`
```dockerfile
FROM python:3.11-slim

# Установка зависимостей
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание директорий
RUN mkdir -p data/{missions,models,logs,maps,memory,state,backups,reports}

# Порты
EXPOSE 8000 8501

# Запуск
CMD ["python", "main.py", "all"]
```

### Файл `docker-compose.yml`
```yaml
version: '3.8'

services:
  coba-ai-drone:
    build: .
    ports:
      - "8000:8000"
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
```

### Как запустить (для пользователя)

#### Шаг 1: Установите Docker
- Windows/Mac: https://www.docker.com/products/docker-desktop
- Linux: `sudo apt install docker.io docker-compose`

#### Шаг 2: Создайте файл `.env`
```
OPENAI_API_KEY=sk-ваш-ключ
```

#### Шаг 3: Запустите
```bash
docker-compose up -d
```

#### Шаг 4: Откройте браузер
```
http://localhost:8501
```

#### Шаг 5: Остановка
```bash
docker-compose down
```

---

## Вариант 3: Установщик (Inno Setup для Windows)

### Что получится
Файл `Setup.exe` — как обычная программа.

### Как создать

#### Шаг 1: Скачайте Inno Setup
https://jrsoftware.org/isdl.php

#### Шаг 2: Создайте скрипт `setup.iss`
```pascal
[Setup]
AppName=COBA AI Drone Agent
AppVersion=2.0
DefaultDirName={autopf}\COBA_AI_Drone
DefaultGroupName=COBA AI Drone Agent
OutputDir=.
OutputBaseFilename=COBA_AI_Drone_Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\COBA_AI_Drone_Agent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config\config.yaml"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "web_interface\*"; DestDir: "{app}\web_interface"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\COBA AI Drone Agent"; Filename: "{app}\COBA_AI_Drone_Agent.exe"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\COBA AI Drone Agent"; Filename: "{app}\COBA_AI_Drone_Agent.exe"

[Run]
Filename: "{app}\COBA_AI_Drone_Agent.exe"; Description: "Запустить COBA AI Drone Agent"; Flags: postinstall skipifsilent
```

#### Шаг 3: Соберите установщик
1. Откройте Inno Setup
2. Откройте `setup.iss`
3. Нажмите Build → Compile

### Как пользователю установить
1. Скачать `COBA_AI_Drone_Setup.exe`
2. Запустить
3. Следовать мастеру установки
4. Запустить с ярлыка на рабочем столе

---

## Вариант 4: Портативная версия

### Структура папки
```
COBA_AI_Drone_Portable/
├── COBA_AI_Drone.exe      # Главный файл
├── config/
│   └── config.yaml        # Настройки
├── data/                   # Данные (создается автоматически)
├── .env                    # API ключи
└── README.txt              # Инструкция
```

### Как пользоваться
1. Распаковать архив
2. Отредактировать `.env` (вставить ключ)
3. Запустить `COBA_AI_Drone.exe`
4. Открыть браузер: http://localhost:8501

---

## Вариант 5: Онлайн-версия (SaaS)

### Идея
Пользователь заходит на сайт, регистрируется, управляет дроном через веб.

### Архитектура
```
Пользователь → Браузер → Наш сервер → Дрон
```

### Преимущества
- Не нужно ничего устанавливать
- Работает с любого устройства
- Автоматические обновления
- Централизованное управление флотом

### Недостатки
- Требуется интернет
- Подписка
- Задержка (latency)

---

## 💡 Рекомендации

### Для тестирования (разработчикам)
```bash
# Docker — быстро и чисто
docker-compose up -d
```

### Для распространения (пользователям)
```
# Windows: Inno Setup установщик
COBA_AI_Drone_Setup.exe
```

### Для портативности
```
# ZIP архив с EXE
COBA_AI_Drone_Portable.zip
```

---

## 📦 Что выложить на GitHub Releases

1. `COBA_AI_Drone_Setup.exe` — установщик для Windows
2. `COBA_AI_Drone_Portable.zip` — портативная версия
3. `docker-compose.yml` — для Docker
4. `Source code` — исходники

---

## 🎯 Итоговая таблица

| Вариант | Сложность создания | Удобство для пользователя | Платформа |
|---------|-------------------|---------------------------|-----------|
| EXE (PyInstaller) | Средняя | Высокое | Windows |
| Docker | Низкая | Среднее | Все |
| Inno Setup | Средняя | Очень высокое | Windows |
| Портативная | Низкая | Высокое | Windows |
| SaaS | Высокая | Очень высокое | Все |

---

## 🚀 Быстрый старт для пользователя (идеальный сценарий)

### Windows
1. Скачать `COBA_AI_Drone_Setup.exe`
2. Установить (Next → Next → Finish)
3. Ввести OpenAI ключ при первом запуске
4. Готово! 🎉

### Mac/Linux
1. Скачать `docker-compose.yml`
2. Создать `.env` с ключом
3. Запустить `docker-compose up -d`
4. Готово! 🎉

---

**Минимум действий — максимум результата! 🚁**
