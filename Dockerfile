FROM python:3-slim

WORKDIR /warning

ADD . /warning

#RUN pip install -r requirements.txt

EXPOSE 9090

CMD ["python", "server.py", "127.0.0.1", "9090"]
