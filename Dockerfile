FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 IMPORTA_DB=/data/importa.db
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# La app corre sin privilegios de root y solo escribe en el volumen de datos.
RUN mkdir -p /data && useradd -r -u 10001 importa && chown -R importa:importa /app /data
USER importa
VOLUME ["/data"]
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
