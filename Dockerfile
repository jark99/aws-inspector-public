FROM python:3-alpine

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY vuln_detector.py .

CMD ["python vuln_detector.py"]