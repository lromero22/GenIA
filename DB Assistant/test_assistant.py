# import mysql.connector
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
# import passwd


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Set API key as environment variable
os.environ['OPENAI_API_KEY'] = api_key

client = OpenAI()

# Funcion para transformar lenguaje natural a sintaxis SQL
def natlang_to_sql(pregunta, table_str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"Eres un asistente que convierte preguntas en consultas SQL, solamente retornaras la sintaxis SQL correspondiente a la consulta. {table_str}"},
            {"role": "user", "content": pregunta}
        ]
    )

    sql_query = response.choices[0].message.content.strip()
    return sql_query

# Ejemplo con tabla lk_pedidos_cstm
table_str = """
La tabla lk_pedidos_cstm tiene las siguientes columnas: id_c, ciclo_c, valor_venta_sin_iva_c. El campo ciclo_c es un VARCHAR con estructura año-mes, por ejemplo, 202401 
donde 2024 representa el año y el 01 representa el ciclo.
"""

pregunta = "Necesito todos los pedidos del ciclo 3"
natlang_to_sql(pregunta, table_str)

print()