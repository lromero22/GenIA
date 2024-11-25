import httpx
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()

class InputData(BaseModel):
    input: str

@app.post("/researcher/")
async def get_users(data: InputData):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://service_1:8000/researcher/",
            json=data.model_dump(),
            timeout=60 
        )
    return response.json()

@app.post("/coder/")
async def get_products(data: InputData):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://service_2:8000/products/",
            json=data.model_dump(),
            timeout=60
        )
    return response.json()

@app.post("/test/")
async def get_products(data: InputData):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://service_3:8000/test/",
            json=data.model_dump(),
            timeout=300
        )
    return response.json()