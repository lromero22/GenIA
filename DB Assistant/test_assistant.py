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
            {"role": "system", "content": f"You're and AI assistant that will help me create SQL queries based on the following table schema: {table_str}"},
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

def table_schema(table_name):
    # Connect to the database
    engine = conn_db()
    # Get the schema of the database
    query_sche = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"

    df = pd.read_sql(query_sche, engine)
    table_schema = df.to_string(index=False, header=False)
    table_sch = "Table Schema: " + table_schema
    return table_sch


table_sch = table_schema("lk_pedidos_cstm")
pregunta = "I need to know the total amount of orders that were placed in the last 30 days."
query = promt_to_sql(pregunta, table_sch)

result = execute_query(query)
