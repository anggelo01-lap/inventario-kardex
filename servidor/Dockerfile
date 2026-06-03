FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Permisos de ejecución al entrypoint
RUN chmod +x punto_entrada.sh

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["sh", "punto_entrada.sh"]
