FROM python:3.9.16-alpine
ADD requirements.txt /app/requirements.txt
RUN python -m venv /env
RUN /env/bin/pip install --upgrade pip
RUN /env/bin/pip install -r /app/requirements.txt
ADD . /app
WORKDIR /app
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH
CMD ["/env/bin/python", "main.py"]
