# pip install langchain openai sqlalchemy python-dotenv langchain-openai langchain-experimental pymysql python-dotenv langchain-community tiktoken jq

import json
import os
import csv
import ast
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import TokenTextSplitter
from sqlalchemy import create_engine
from langchain_openai import ChatOpenAI, OpenAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains import create_sql_query_chain
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


load_dotenv()

# Set API key as environment variable
os.environ['OPENAI_API_KEY'] = os.getenv("API_KEY")


list(SQL_PROMPTS)


def conn_db():
    conn_str = os.getenv("CONNECTION_STRING")
    engine = create_engine(conn_str)
    return engine

db_engine = conn_db()

##call cstm, calls, leads_cstm
db = SQLDatabase(engine=db_engine, include_tables=["leads", "lk_pedidos_cstm", "leads_lk_pedidos_1_c"])
# db = SQLDatabase(engine=db_engine)
llm1 = ChatOpenAI(temperature=0, verbose=True)
llm = OpenAI(temperature=0, verbose=True)
query_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=False, return_direct=True, use_query_checker=False, return_sql=False)

# Traeme el Nombre , cedula , usuario o liker lo tiene asignado, ciclo y valor del pedido de los leads o novaempresarios para el ciclo 202408, No limites la respuesta
human_input = "Traeme el Nombre , cedula , usuario o liker lo tiene asignado, ciclo y valor del pedido de los leads o novaempresarios para el ciclo 202408, No limites la respuesta"
########################################################       
# Define el esquema JSON para extraer tablas y campos
# json_schema = {
#     "title": "Table",
#     "description": "Tables and fields in SQL database.",
#     "type": "object", ##Error a
#     "properties": {
#         "table_name": {
#             "type": "string",
#             "description": "Name of the table in the database.",
#         },
#         "fields": {
#             "type": "array",
#             "items": {
#                 "type": "string",
#                 "description": "Field names in the table.",
#             },
#         },
#     },
#     "required": ["table_name", "fields"],
# }
########################################################
# Convertir JSON a documentos
loader = JSONLoader(
    file_path='utils\contexto_tablas.json',
    # jq_schema='.modulos | to_entries | map({table_name: .key, fields: (.value.campos | keys)})',
    # is_content_key_jq_parsable=True,
    jq_schema='.modulos',
    text_content=False)

table_names = loader.load()
pprint(table_names)

tables_model_prefix = """Devuelve solo los nombres de la tablas SQL y los campos que SON relevantes para la pregunta del usuario, especifica muy bien a que tabla correponde cada campo.
No debes inventar datos, solo elegir con repecto al mensaje human cuales son las tablas donde se podira encontrar esta data basado en el siguiente JSON:

{tables_names}

No limites tu respuesta"""

prompt_tables = PromptTemplate(
    template=tables_model_prefix,
    input_variables=["input" ,"tables_names"]
)

full_prompt_tables = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(prompt=prompt_tables),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

# structured_llm = llm1.with_structured_output(json_schema)

prompt_val_tables = full_prompt_tables.invoke(
    {
        "input": human_input,
        "tables_names": table_names,
        "agent_scratchpad": [],
    }
)

# print(prompt_val_tables.to_string())

# with get_openai_callback() as cb:
#     tables_response = llm.invoke(prompt_val_tables)
#     print(f"Total tokens used: {cb.total_tokens}")
#     print(f"Prompt tokens used: {cb.prompt_tokens}")
#     print(f"Completion tokens used: {cb.completion_tokens}")
#     print(f"Total cost: ${cb.total_cost:.5f}")

# tables_response = structured_llm.invoke(prompt_val_tables)
tables_response = llm.invoke(prompt_val_tables)
print(tables_response)


##########################################################
###COntext automatico de la BD
# context = db.get_context()
# print(list(context))
# print(context["table_names"])

##############################################################
###Vectore store con FAISS para los ejemplos
with open('utils\query_examples.json', 'r') as file:
    query_examples = json.load(file)

example_selector = SemanticSimilarityExampleSelector.from_examples(
    query_examples,
    OpenAIEmbeddings(),
    FAISS,
    k=2,
    input_keys=["input"],
)
 ########################################################       
# Define a simple example prompt
sql_model_prefix = """Eres un experto en {dialect}. Dada una pregunta de entrada, crea una consulta {dialect} sintácticamente correcta para ejecutar. 
A menos que se especifique lo contrario, no devuelvas más de {top_k} filas.
Aquí está la información relevante de las tabla: {table_info}
A continuación, se presentan varios ejemplos de preguntas y sus consultas SQL correspondientes:\n\n"""

example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")

prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=example_prompt,
    prefix=sql_model_prefix,
    suffix="",
    input_variables=["input", "dialect", "top_k", "table_info"],
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
        "top_k": 5,
        "dialect": "MariaDB",
        "table_info": tables_response,
        "agent_scratchpad": [],
    }
)
print(prompt_val.to_string())

#############################################
##Crear agente SQL

####################################################
# Function to save LLM response to CSV
def save_response_to_csv(response, filename='llm_response.csv'):
    # Verificar si la respuesta es una cadena y convertirla a una lista de tuplas
    if isinstance(response, str):
        response = ast.literal_eval(response)

    # Verificar el número máximo de columnas en la respuesta
    max_columns = max(len(row) for row in response)
    headers = [f'Column{i+1}' for i in range(max_columns)]

    with open(filename, 'w', newline='') as output_file:
        csv_writer = csv.writer(output_file)
        # Escribir la fila de encabezado
        csv_writer.writerow(headers)
        # Escribir los datos
        csv_writer.writerows(response)

########################################################
###Primera cadena, Cosulta a la SQL
sql_query = query_chain.invoke(prompt_val)
# print(sql_query["result"])



##########################################################
#Callback para tokens del input, tokens del output, total de tokens y costo de los tokens
with get_openai_callback() as cb:
    sql_query = query_chain.invoke(prompt_val)
    print(f"Total tokens used: {cb.total_tokens}")
    print(f"Prompt tokens used: {cb.prompt_tokens}")
    print(f"Completion tokens used: {cb.completion_tokens}")
    print(f"Total cost: ${cb.total_cost:.5f}")


print("FIN DE LA PRIMERA CADENA")

########################################################
#Segunda Cadena, Pasar o no el contexto al LLM

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
        "response_query": sql_query["result"],
        "agent_scratchpad": [],
    }
)

####################################################
####Funcion para contar Tokens
total_tokens_used = 0

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

tokens = encoding.encode(prompt_val_llm.to_string())
total_tokens = len(tokens)

# with get_openai_callback() as cb:
#     llm_response = llm.invoke(prompt_val_llm)
#     print(f"Total tokens used: {cb.total_tokens}")
#     print(f"Prompt tokens used: {cb.prompt_tokens}")
#     print(f"Completion tokens used: {cb.completion_tokens}")
#     print(f"Total cost: ${cb.total_cost:.5f}")

# print(f"Total tokens in sql_query['result']: {total_tokens}")
####################################################
###Validacion de tokens y respuesta
try:
    llm_response = llm.invoke(prompt_val_llm)
    print(llm_response)
except Exception as e:
    # En caso de error, guarda la respuesta en un CSV y muestra el resultado
    save_response_to_csv(sql_query["result"])
    print(sql_query["result"])
#########################################################
##Respuestas, tokens y metadata
# sql_query = query_chain.invoke(prompt_val)

# save_response_to_csv(sql_query["result"])
# print(type(sql_query["result"]))

# with get_openai_callback() as cb:
#     sql_query = query_chain.invoke(prompt_val)
#     print(f"Total tokens used: {cb.total_tokens}")
#     print(f"Prompt tokens used: {cb.prompt_tokens}")
#     print(f"Completion tokens used: {cb.completion_tokens}")
#     print(f"Total cost: ${cb.total_cost:.5f}")



##Estructura de la respuesta 
# sql_query["result"] 
# sql_query["query"]