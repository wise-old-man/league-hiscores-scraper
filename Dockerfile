FROM python:3.10-alpine

WORKDIR /app

RUN mkdir -p /app/data
RUN mkdir -p /app/logs

VOLUME ["/app/data", "/app/logs"]

COPY requirements.txt .
COPY hiscores_scrapper.py .


RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "hiscores_scrapper.py"]
