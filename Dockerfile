FROM python:3.10-slim

WORKDIR /mededbot

# Install required packages for SSL/TLS and update certs
RUN apt update && apt install -y ca-certificates && update-ca-certificates

COPY smtp_test.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
