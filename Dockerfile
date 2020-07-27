FROM python:3-alpine

RUN apk add build-base libffi-dev openssl-dev

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN mkdir /db

COPY requirements.txt setup.py /usr/src/app/
RUN mkdir /usr/src/app/ureader
COPY ureader /usr/src/app/ureader
RUN pip install --no-cache-dir -e .

COPY config.py /usr/src/app/
RUN mkdir /usr/src/app/instance
COPY instance/ /usr/src/app/instance

EXPOSE 5000

ENV FLASK_APP=ureader

CMD [ "flask", "run", "--host", "0.0.0.0" ]
