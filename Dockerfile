# Discord metrics bot
FROM python:3.12-slim

WORKDIR /app

# Install Python deps first (cache-friendly)
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Copy source
COPY src/ /app/src/

# Runtime env (overridable by docker-compose/.env)
ENV PROM_PORT=9108
ENV TICK_SECONDS=5

# Expose metrics port (optional, doc only)
EXPOSE 9108

# Run the bot
CMD ["python", "/app/src/bot.py"]
