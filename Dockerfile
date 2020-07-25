FROM python:3-alpine

RUN apk add build-base libffi-dev openssl-dev

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN mkdir /db

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ /usr/src/app

EXPOSE 5000

CMD [ "python", "./run.py" ]
