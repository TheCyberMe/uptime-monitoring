FROM python:3.13.5

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY webhook_receiver.py .
COPY prometheus.yml .

EXPOSE 5000 5001

CMD ["python", "webhook_receiver.py"]

