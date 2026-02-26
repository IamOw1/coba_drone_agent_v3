FROM python:3.12-slim

# рабочая директория
WORKDIR /app

# установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копирование проекта
COPY . .

# создаём папки для данных (чтобы они были на месте в контейнере)
RUN mkdir -p data/{missions,models,logs,maps,memory,state,backups,reports,detections}

# проброс портов
EXPOSE 8000 8501

# переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1

# точка входа
CMD ["python", "main.py", "all"]
