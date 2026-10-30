# 1. Базовый образ. Берём официальный Python версии 3.11 на основе Linux.
FROM python:3.11-slim

# 2. Рабочая папка. Внутри контейнера создается папка /app, все последующие команды выполняются в ней.
WORKDIR /app

# 3. Копируем список зависимостей и READme из вашей локальной папки в папку /app внутри контейнера.
COPY requirements.txt .
COPY READme.md .

# 4. Обновляем системные пакеты (убирает уязвимости ОС)
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Обновляем утилиты, на которые жалуется Trivy
RUN pip install --no-cache-dir \
    pip==26.2.2 \
    setuptools==84.2.1 \
    wheel==0.48.0 

# ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 

# 5. Копируем только нужные файлы (не копируем .git, .env и прочий мусор)
COPY app.py .
COPY templates/ ./templates/

# 6. Документируем порт. Это подсказка для Docker, что приложение внутри слушает порт 8080.
EXPOSE 8080

# 7. Команда запуска. Запускает ваш Python-скрипт при старте контейнера.
# Флаг --host=0.0.0.0 обязателен, чтобы Flask слушал запросы не только внутри себя, но и снаружи.
CMD ["python", "app.py", "--host=0.0.0.0", "--port=8080"]
