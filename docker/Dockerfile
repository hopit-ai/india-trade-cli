FROM python:3.12-slim

# Install Node.js for React build
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python deps
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir passlib[bcrypt]

# Build React web app
RUN cd macos-app && npm install && npm run build:web

EXPOSE 8765

CMD ["uvicorn", "web.api:app", "--host", "0.0.0.0", "--port", "8765"]
