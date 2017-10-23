FROM python:3-slim

WORKDIR /warning

ADD . /warning

#RUN pip install -r requirements.txt

CMD ["python", "server.py"]
