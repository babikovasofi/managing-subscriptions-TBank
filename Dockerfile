FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Генерируем датасет, обучаем модель, инициализируем БД
RUN python -m data.generator.generate
RUN python -m ml.models.train
RUN python -m api.init_db

# Запускаем API
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
