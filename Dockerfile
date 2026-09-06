FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
ENV JSGENT_USER=admin
ENV JSGENT_PASS=jsGENT-2026
ENV JSGENT_SECRET=change-me-in-production
ENV MUSE_API_BASE=https://api.opencode.ai/v1
# MUSE_API_KEY and MUSE_MODEL set via hosting env
EXPOSE 8000
CMD ["sh","-c","uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
