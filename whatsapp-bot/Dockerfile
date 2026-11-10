FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
COPY business.example.json .
ENV BUSINESS_FILE=/data/business.json DB_PATH=/data/bot.db
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "bot.main:build_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
