# import mysql.connector
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd
import pymysql


load_dotenv()
api_key = os.getenv("API_KEY")

# Set API key as environment variable
os.environ['OPENAI_API_KEY'] = api_key

client = OpenAI()

# Funcion para transformar lenguaje natural a sintaxis SQL
def promt_to_sql(pregunta, table_str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"Eres un asistente que convierte preguntas en consultas SQL, solamente retornaras la sintaxis SQL correspondiente a la consulta. Sin decoradores solo el texto. Haz las querys teniendo en cuenta que la DB es una MariaDB. Las caracteristicas de la tabla estan en formato diccionario, con key = table_name, value = table_schema, pueden ser unica o varias. IMPORTANTE: NUNCA HARAS QUERYS QUE ELIMINEN O MODIFIQUEN DATOS, SOLO CONSULTAS SELECT. Estas son las caracteristica {table_str}"},
            {"role": "user", "content": pregunta}
        ]
    )

    sql_query = response.choices[0].message.content.strip()
    return sql_query

def conn_db():
    conn_str = os.getenv("CONNECTION_STRING")
    # Create a connection to the database
    engine = create_engine(conn_str)
    return engine

def execute_query(query):
    # Connect to the database
    engine = conn_db()
    df = pd.read_sql(query, engine)
    return df

def table_schema(tables_names:list):
    # Connect to the database
    engine = conn_db()
    table_sch = {}
    for table_name in tables_names:
        # Get the schema of the database
        query_sche = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"

        df = pd.read_sql(query_sche, engine)
        table_schema = ', '.join(f"{row['COLUMN_NAME']}: {row['DATA_TYPE']}" for index, row in df.iterrows())
        table_sch[table_name] = table_schema

    return table_sch


tables_to_look = ["leads", "leads_lk_pedidos_1_c", "lk_pedidos_cstm"]

table_sch = table_schema(tables_to_look)
pregunta = "Quiero saber el id del lider que tenga a las 10 personas mas vendieron y el valor de ventas, teniendo como limite inferior ventas de 400000 en los ciclos mayores a 202310, con pedidos mayores a 3. Y sabiendo que la tabla leads tiene el id del lider, la tabla leads_lk_pedidos_1_c es una tabla relacional que los leads que se relacionan con cada id de lk, tambien como dato adicional el id de lk_pedidos_cstm tiene este formato id-ciclo."
query = promt_to_sql(pregunta, table_sch)

result = execute_query(query)

print(result)
