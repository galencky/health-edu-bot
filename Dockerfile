# === Dockerfile ===
FROM python:3.11-slim

# 1) Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy app source
COPY . .

# 3) Runtime settings
ENV PORT=10001
EXPOSE 10001

CMD ["uvicorn", "main:app", "--host", "192.168.0.109", "--port", "10001"]

