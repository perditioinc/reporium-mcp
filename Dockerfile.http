FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-http.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-http.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "http_server:app", "--host", "0.0.0.0", "--port", "8080"]
