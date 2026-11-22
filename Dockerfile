FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY public public
COPY sql sql
COPY config.py run.py wsgi.py ./

CMD ["python", "-m", "flask", "--app", "run", "run", "--host=0.0.0.0"]

