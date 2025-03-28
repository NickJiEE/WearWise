FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./wardrobe /code/wardrobe

ENV PYTHONPATH=/code/wardrobe

EXPOSE 80
CMD ["uvicorn", "wardrobe.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]