FROM python:3.10-slim

WORKDIR /mededbot

# Install only the runtime TLS stack, then clean up apt cache
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      ca-certificates \
      openssl \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Copy in your test script & deps list
COPY requirements.txt ./

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application
COPY . .

EXPOSE 10000

CMD ["uvicorn","main:app","--host","0.0.0.0","--port","10000"]
