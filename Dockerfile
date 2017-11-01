FROM python:3-slim

WORKDIR /warning

ADD . /warning

#RUN pip install -r requirements.txt

#EXPOSE 9090

CMD ["python", "warning.py"]
