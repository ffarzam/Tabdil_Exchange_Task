FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN pip install --upgrade pip

COPY requirements.txt /code/

RUN pip install -r requirements.txt

COPY . /code/

EXPOSE 8000

CMD python manage.py makemigrations --noinput && \
    python manage.py migrate --noinput && \
    gunicorn -b 0.0.0.0:8000 config.wsgi:application --reload
#    python manage.py runserver 0.0.0.0:8000



