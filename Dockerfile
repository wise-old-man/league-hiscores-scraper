FROM python:3.10

WORKDIR /app

COPY requirements.txt .
COPY hiscores_scrapper.py .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "hiscores_scrapper.py"]
