FROM python:3.9-slim

RUN mkdir /app

COPY src /app
COPY .env /app/.env
COPY requirements.txt /app

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 32000

CMD [ "python", "main.py" ]