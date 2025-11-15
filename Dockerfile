# syntax=docker/dockerfile:1

FROM ubuntu:jammy
WORKDIR /
COPY . .
RUN apt update && apt upgrade -y
RUN apt install -y python3.11 pip
RUN pip install requests==2.31.0 websockets==12.0 asyncio==3.4.3 simpleobsws==1.4.0
CMD ["python3", "main.py"]
