FROM python:3.12-slim
WORKDIR /code
RUN pip install --no-cache-dir httpx==0.28.1
COPY simulator.py .
CMD ["python", "-u", "simulator.py"]
