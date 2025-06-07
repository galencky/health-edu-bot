FROM python:3.11-slim

# 1) install deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) copy source (root of repo → /app)
COPY . .

# 3) runtime settings
ENV PORT=10001
EXPOSE 10001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10001"]
