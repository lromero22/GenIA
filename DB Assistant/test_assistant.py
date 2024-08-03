# import mysql.connector
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd
import pymysql
import time


load_dotenv()

# Configuration for the OpenAI client
client = OpenAI()

# Function to prompt the user for the SQL
def prompt_to_sql(question):
    try:
        # Create a thread with the user's question
        thread_openai = client.beta.threads.create(
            messages=[
                {"role": "user", "content": question}
            ]
        )

        # Run the thread with the assistant
        run = client.beta.threads.runs.create(thread_id=thread_openai.id, assistant_id=os.getenv('ASSISTANT_ID'))
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread_openai.id, run_id=run.id)

        # Get the latest message from the assistant
        message_response = client.beta.threads.messages.list(thread_id=thread_openai.id)
        messages = message_response.data

        if not messages:
            raise ValueError("No messages returned from the assistant.")

        latest_message = messages[0]
        sql_query = latest_message.content[0].text.value
        # The sql_query is formatted as a markdown sql string, so we need to remove the markdown characters
        sql_query = sql_query.replace('```sql\n', '').replace('```', '').strip()

        return sql_query
    except Exception as e:
        print(f"An error ocurred: {e}")
        return None


def conn_db():
    conn_str = os.getenv("CONNECTION_STRING")
    # Create a connection to the database
    engine = create_engine(conn_str)
    return engine

def query_engine(query):
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

def execute_query():
    # Esta función simula la ejecución de la consulta SQL
    print("Executing query...")
    try:
        result = query_engine(query)
        print(result)
    except Exception as e:
        if "Can't connect to MySQL" in str(e):
            print("There was an error connecting to the database. Please check the connection")
            print(e)
            exit()
        else:
            print(e)
            query = prompt_to_sql(f"There was an error with the query, please try again. {e}")
            result = query_engine(query)

def main():
    # step 1: Get the question from the user
    # question = "Traeme el nombre, identificación o cédula, usuario o liker que lo tiene asignado, ciclo y valor del pedido de los leads o novaempresarios para el ciclo 202409"

    question = input("Enter the question: ")

    query = prompt_to_sql(question)
    
    # Step 2: Ask the user if they want to execute the query
    answer = input("Do you want to execute the query? (s/n): ").strip().lower()
    
    # Step 3: Wait for user decision
    if answer == 's':
        execute_query()
    elif answer == 'n':
        print(f"SQL Query: \n{query}")
    else:
        print("Invalid option. Please enter 's' to execute the query or 'n' to show the query.")

if __name__ == "__main__":
    main()
