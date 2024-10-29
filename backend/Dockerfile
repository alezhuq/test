FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY .env /code/
COPY . /code/
EXPOSE 8000
# RUN chmod +x entrypoint.sh
# CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD [ "entrypoint.sh"]

