FROM python:3.11-alpine AS base

WORKDIR /label-studio-tests

# Upgrade setuptools to delete the vulnerability
RUN pip install -U setuptools

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT [ "python3" ]
CMD [ "label_studio_test.py" ]