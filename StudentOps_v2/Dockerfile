FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -u 10001 -m student
COPY app.py .
COPY templates templates
RUN mkdir -p instance && chown -R student:student /app
USER student
EXPOSE 5000
CMD ["gunicorn","--bind","0.0.0.0:5000","--access-logfile","-","app:app"]
