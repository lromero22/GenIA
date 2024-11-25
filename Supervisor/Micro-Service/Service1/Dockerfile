FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./main.py /app/main.py
COPY ./langchain.pdf /app/langchain.pdf

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]