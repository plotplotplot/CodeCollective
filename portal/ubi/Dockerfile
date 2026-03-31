FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
ENV PYTHONPATH=/app

# Make manage.py easily accessible
RUN chmod +x /app/manage.py && ln -sf /app/manage.py /usr/local/bin/ubi-admin

EXPOSE 8000

CMD ["uvicorn", "ubi:app", "--host", "0.0.0.0", "--port", "8000"]
