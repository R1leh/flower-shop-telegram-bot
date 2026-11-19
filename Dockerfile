FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для сборки Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создание директорий для данных и бэкапов
RUN mkdir -p data/photos backup

CMD ["python", "main.py"]
