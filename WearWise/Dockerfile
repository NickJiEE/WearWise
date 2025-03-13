FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./wardrobe /code/wardrobe
COPY ./wardrobe/sample /code/wardrobe/sample

ENV PYTHONPATH=/code/wardrobe

CMD ["uvicorn", "wardrobe.main:app", "--host", "0.0.0.0", "--port", "6543", "--reload"]
