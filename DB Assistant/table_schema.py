import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pymysql

load_dotenv()

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
        table_sch[table_name] = []
        for _, row in df.iterrows():
            column_name = row['COLUMN_NAME']
            data_type = row['DATA_TYPE']
            table_sch[table_name].append(f"- {column_name}: Esta columna es de tipo {data_type}")

    return table_sch

for table_name, schema in table_schema(["lk_pedidos"]).items():
    print(f"Tabla: {table_name}")
    print("\n".join(schema))
    print("\n")