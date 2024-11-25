import json 
import os
import csv
import ast
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import TokenTextSplitter
from sqlalchemy import create_engine
from langchain_openai import ChatOpenAI, OpenAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains.sql_database.prompt import SQL_PROMPTS
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate, MessagesPlaceholder, ChatPromptTemplate, SystemMessagePromptTemplate
import tiktoken
from langchain_community.vectorstores import Chroma
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_community.callbacks.manager import get_openai_callback
from pprint import pprint 
from langchain_community.document_loaders import JSONLoader
import openai
from langsmith import traceable
from langsmith import Client
import logging
from langsmith.run_helpers import get_current_run_tree



logging.basicConfig(level=logging.INFO)

load_dotenv()

# Set API key as environment variable
os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")
os.environ['LANGCHAIN_API_KEY'] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = "Asistente SQL V1"

app = FastAPI()

# Modelo para manejar la entrada
class InputData(BaseModel):
    input: str

client = Client()
list(SQL_PROMPTS)

# Conexión a la base de datos
def conn_db():
    conn_str = os.getenv("CONNECTION_STRING")
    engine = create_engine(conn_str)
    return engine


db_engine = conn_db()
db = SQLDatabase(engine=db_engine, include_tables=["leads", "lk_pedidos_cstm", "leads_lk_pedidos_1_c"])

@traceable
def invoke_Chatopenai(prompt):
    run = get_current_run_tree()
    print(f"format_prompt Run Id: {run.id}")
    print(f"format_prompt Trace Id: {run.trace_id}")
    llm1 = ChatOpenAI(temperature=0, verbose=True, model="gpt-4o-mini")
    return llm1.invoke(prompt)

llm = OpenAI(temperature=0, verbose=True)

@traceable
def execute_sql_query(llm, db, prompt_val, verbose=False, return_direct=True, use_query_checker=False, return_sql=False):
    query_chain = SQLDatabaseChain.from_llm(
        llm=llm,
        db=db,
        verbose=verbose,
        return_direct=return_direct,
        use_query_checker=use_query_checker,
        return_sql=return_sql
    )
    sql_query = query_chain.invoke(prompt_val)
    return sql_query


def generate_first_prompt(file_path, human_input):
    loader = JSONLoader(
        file_path=file_path,
        jq_schema='.modulos',
        text_content=False
    )

    table_names = loader.load()

    tables_model_prefix = """Devuelve solo los nombres de las tablas SQL y los campos que SON relevantes para la pregunta del usuario, especifica muy bien a qué tabla corresponde cada campo.
    No debes inventar datos, solo elegir con respecto al mensaje humano cuáles son las tablas donde se podría encontrar esta data basado en el siguiente JSON:

    {tables_names}

    No limites tu respuesta"""

    prompt_tables = PromptTemplate(
        template=tables_model_prefix,
        input_variables=["input", "tables_names"]
    )

    full_prompt_tables = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=prompt_tables),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    prompt_val_tables = full_prompt_tables.invoke(
        {
            "input": human_input,
            "tables_names": table_names,
            "agent_scratchpad": [],
        }
    )

    return prompt_val_tables


def generate_second_prompt(human_input, tables_response, dialect="MariaDB"):
    example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")
    sql_model_prefix = """Eres un experto en {dialect}. Dada una pregunta de entrada, crea una consulta {dialect} sintácticamente correcta para ejecutar.
Aquí está la información relevante de las tabla: {table_info}
A continuación, se presentan varios ejemplos de preguntas y sus consultas SQL correspondientes:\n\n"""
    ###Vectore store con FAISS para los ejemplos
    with open('Data/query_examples.json', 'r') as file:
        query_examples = json.load(file)

    example_selector = SemanticSimilarityExampleSelector.from_examples(
        query_examples,
        OpenAIEmbeddings(),
        FAISS,
        k=1,
        input_keys=["input"],
    )

    prompt = FewShotPromptTemplate(
        example_selector=example_selector,
        example_prompt=example_prompt,
        prefix=sql_model_prefix,
        suffix="",
        input_variables=["input", "dialect", "table_info"],
    )

    full_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    prompt_val = full_prompt.invoke(
        {
            "input": human_input,
            "dialect": dialect,
            "table_info": tables_response,
            "agent_scratchpad": [],
        }
    )

    return prompt_val

def generate_third_prompt(human_input, sql_query_result):
    llm_model_prefix = """Eres parte de una cadena de LangChain y recibirás una respuesta de una consulta a una base de datos SQL en el siguiente formato: [(columna1, columna2, ...), (columna1, columna2, ...), ...].
    Quiero que proceses esta información y respondas a la pregunta del de la mejor manera posible, sin rebundar en detalles, centrate en dar un respuesta lo mas ligera posible pero sin inventar ningun dato, utilizando únicamente la información disponible en la respuesta sin inventar datos, la pregunta es: {input}
    Aquí está la respuesta de la consulta: {response_query}\n\n"""

    prompt_llm = PromptTemplate(
        template=llm_model_prefix,
        input_variables=["response_query"]
    )

    full_prompt_llm = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=prompt_llm),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    prompt_val_llm = full_prompt_llm.invoke(
        {
            "input": human_input,
            "response_query": sql_query_result,
            "agent_scratchpad": [],
        }
    )

    return prompt_val_llm

def save_response_to_csv(response, filename='llm_response.csv'):
    if isinstance(response, str):
        response = ast.literal_eval(response)

    max_columns = max(len(row) for row in response)
    headers = [f'Column{i+1}' for i in range(max_columns)]

    with open(filename, 'w', newline='') as output_file:
        csv_writer = csv.writer(output_file)
        csv_writer.writerow(headers)
        csv_writer.writerows(response)


@app.post("/products/")
async def query_endpoint(data: InputData):
    try:
        human_input = data.input

        # Generar el primer prompt
        file_path = 'Data/contexto_tablas.json'
        prompt_val_tables = generate_first_prompt(file_path, human_input)
        tables_response = invoke_Chatopenai(prompt_val_tables)

        # Generar el segundo prompt
        prompt_val = generate_second_prompt(human_input, tables_response)

        # Ejecutar la consulta SQL
        sql_query = execute_sql_query(llm, db, prompt_val)

        # Generar el tercer prompt
        prompt_val_llm = generate_third_prompt(human_input, sql_query["result"])

        # Contar tokens
        total_tokens_used = 0
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = encoding.encode(prompt_val_llm.to_string())
        total_tokens = len(tokens)

        # Validar tokens y obtener la respuesta del modelo
        try:
            llm_response = invoke_Chatopenai(prompt_val_llm)
            return {"response": llm_response}
        except Exception as e:
            save_response_to_csv(sql_query["result"])
            return {"response": sql_query["result"]}
    except Exception as e:
        print('Error:', e)
        raise HTTPException(status_code=500, detail=str(e))





