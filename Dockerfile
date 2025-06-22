FROM python:3.10-alpine

WORKDIR /app

RUN mkdir -p /app/data
RUN mkdir -p /app/logs

VOLUME ["/app/data", "/app/logs"]

COPY requirements.txt .
COPY get_leagues_ranking.py .


RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "get_leagues_ranking.py"]
