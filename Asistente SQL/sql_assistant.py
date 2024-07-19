# pip install langchain openai sqlalchemy python-dotenv langchain-openai langchain-experimental pymysql python-dotenv langchain-community tiktoken

import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from sqlalchemy import create_engine
from langchain_openai import OpenAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains import create_sql_query_chain
from langchain.chains.sql_database.prompt import SQL_PROMPTS
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate, MessagesPlaceholder, ChatPromptTemplate, SystemMessagePromptTemplate
import tiktoken
from langchain_community.vectorstores import Chroma
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain_community.agent_toolkits import create_sql_agent

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
llm = OpenAI(temperature=0, verbose=True)
db_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=True, return_direct=True, return_sql=False)

##Examples
examples = [
    {"input": "Dame el Id de Lucy Yohana Cespedes Ramos", "query": "SELECT id FROM leads WHERE leads.last_name='Lucy Yohana Cespedes Ramos';"},
    {
        "input": "cual es el nombre de quien llamo a Lucy Yohana Cespedes Ramos, su estatus y en que fechas",
        "query": "SELECT leads.last_name, users.user_name, calls.date_entered, calls.created_by, calls.status FROM leads JOIN calls on calls.parent_id=leads.id JOIN users on users.id=calls.created_by WHERE leads.id='10002d2b-c3db-6e82-1fd9-64dcfb3d016d';",
    },
    {
        "input": "Total de pedidos realizados por Lucy Yohana Cespedes Ramos",
        "query": "SELECT COUNT(lk_pedidos.id) as total_pedidos FROM leads JOIN leads_lk_pedidos_1_c ON leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida = leads.id JOIN lk_pedidos ON lk_pedidos.id = leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos';",
    },
    {
        "input": "Detalles de los pedidos con valor superior a 1000 sin IVA de Lucy Yohana Cespedes Ramos",
        "query": "SELECT lk_pedidos.id, lk_pedidos.name, lk_pedidos_cstm.valor_venta_sin_iva_c FROM leads JOIN leads_lk_pedidos_1_c ON leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida = leads.id JOIN lk_pedidos ON lk_pedidos.id = leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb JOIN lk_pedidos_cstm ON lk_pedidos_cstm.id_c = lk_pedidos.id WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos' AND lk_pedidos_cstm.valor_venta_sin_iva_c > 1000;",
    },
    {
        "input": "Fecha del último pedido de Lucy Yohana Cespedes Ramos",
        "query": "SELECT MAX(lk_pedidos.date_entered) as ultimo_pedido FROM leads JOIN leads_lk_pedidos_1_c ON leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida = leads.id JOIN lk_pedidos ON lk_pedidos.id = leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos';",
    },
    {
        "input": "¿Quién es el vendedor asignado a Lucy Yohana Cespedes Ramos?",
        "query": "SELECT users.user_name FROM leads JOIN users ON leads.assigned_user_id = users.id WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos';",
    },
    {
        "input": "¿Cuál es el presupuesto total gastado por Lucy Yohana Cespedes Ramos en todos los ciclos?",
        "query": "SELECT SUM(lk_pedidos_cstm.presupuesto_c) as total_presupuesto FROM leads JOIN leads_lk_pedidos_1_c ON leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida = leads.id JOIN lk_pedidos ON lk_pedidos.id = leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb JOIN lk_pedidos_cstm ON lk_pedidos_cstm.id_c = lk_pedidos.id WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos';",
    },
    {
        "input": "Dame los pedidos y presupuesto por ciclo de Lucy Yohana Cespedes Ramos",
        "query": "SELECT lk_pedidos_cstm.ciclo_c, lk_pedidos.name, lk_pedidos_cstm.presupuesto_c FROM leads JOIN leads_lk_pedidos_1_c ON leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida = leads.id JOIN lk_pedidos ON lk_pedidos.id = leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb JOIN lk_pedidos_cstm ON lk_pedidos_cstm.id_c = lk_pedidos.id WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos';",
    },
    {
        "input": "¿Cuántos pedidos realizó Lucy Yohana Cespedes Ramos en el ciclo 202311?",
        "query": "SELECT lk_pedidos_cstm.pedidos_realizados_c FROM leads JOIN leads_lk_pedidos_1_c ON leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida = leads.id JOIN lk_pedidos ON lk_pedidos.id = leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb JOIN lk_pedidos_cstm ON lk_pedidos_cstm.id_c = lk_pedidos.id WHERE leads.last_name = 'Lucy Yohana Cespedes Ramos' AND lk_pedidos_cstm.ciclo_c = 202311;",
    },
    {
        "input": "Dame los clientes potenciales del departamento de Antioquia",
        "query": "SELECT leads.last_name, leads.phone_mobile FROM leads WHERE leads.department = 'Antioquia';",
    },
    {
        "input": "Dame los pedidos realizados por Lucy Yohana Cespedes Ramos en el ciclo 202311",
        "query": 'SELECT COUNT(*) FROM "Employee"',
    },
    {
        "input": "Dame todos los vendedores y sus clientes asignados",
        "query": 'SELECT users.user_name, leads.last_name FROM leads JOIN users ON leads.assigned_user_id = users.id;',
    },
    {
        "input": "Dame el total de pedidos por ciclo en el año 2024",
        "query": 'SELECT lk_pedidos_cstm.ciclo_c, COUNT(lk_pedidos.id) as total_pedidos FROM lk_pedidos JOIN lk_pedidos_cstm ON lk_pedidos_cstm.id_c = lk_pedidos.id WHERE lk_pedidos.name like "2024%" GROUP BY lk_pedidos_cstm.ciclo_c',
    },
    #Aqui estan las querys de likeU
    {
        "input": "Pedidos Vs Cilos de Lucy Yohana Cespedes Ramos",
        "query": 'SELECT last_name, lk_pedidos.name FROM leads JOIN leads_lk_pedidos_1_c on leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida=leads.id JOIN lk_pedidos on lk_pedidos.id=leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb WHERE leads.id = "10002d2b-c3db-6e82-1fd9-64dcfb3d016d" AND lk_pedidos.name!="" ORDER BY "lk_pedidos","name" ASC;',
    },
    {
        "input": "Cual es el valor sin iva de Lucy Yohana Cespedes Ramos en todos los periodos",
        "query": 'SELECT last_name, lk_pedidos.name, lk_pedidos_cstm.valor_venta_sin_iva_c FROM leads JOIN leads_lk_pedidos_1_c on leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida=leads.id JOIN lk_pedidos on lk_pedidos.id=leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb JOIN lk_pedidos_cstm on lk_pedidos_cstm.id_c=lk_pedidos.id WHERE leads.id = "10002d2b-c3db-6e82-1fd9-64dcfb3d016d" AND lk_pedidos.name!="" ORDER BY "lk_pedidos","name" ASC;',
    },
    ##important
     {
         "input": "Traeme el Nombre , identificacion o cedula , usuario o liker lo tiene asignado, ciclo y valor del pedido de los leads o novaempresarios para el ciclo 202409",
         "query": 'SELECT leads.last_name , leads_cstm.identificacion_c ,users.user_name,lk_pedidos.name, lk_pedidos_cstm.valor_venta_sin_iva_c FROM leads  JOIN leads_cstm on leads_cstm.id_c=leads.id join users on users.id=leads.assigned_user_id JOIN leads_lk_pedidos_1_c on leads_lk_pedidos_1_c.leads_lk_pedidos_1leads_ida=leads.id  JOIN lk_pedidos on lk_pedidos.id=leads_lk_pedidos_1_c.leads_lk_pedidos_1lk_pedidos_idb  JOIN lk_pedidos_cstm on lk_pedidos_cstm.id_c=lk_pedidos.id  WHERE lk_pedidos.name="202409";',
        
    }
]

###Vectore store con FAISS
example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples,
    OpenAIEmbeddings(),
    FAISS,
    k=2,
    input_keys=["input"],
)

# Define a simple example prompt

prefix = """Eres un experto en MySQL. Dada una pregunta de entrada, crea una consulta MySQL sintácticamente correcta para ejecutar. 
A menos que se especifique lo contrario, no devuelvas más de {top_k} filas.
A continuación, se presentan varios ejemplos de preguntas y sus consultas SQL correspondientes:\n\n"""

example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")
prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=PromptTemplate.from_template(
        "User input: {input}\nSQL query: {query}"
    ),
    prefix=prefix,
    suffix="",
    input_variables=["input", "dialect", "top_k"],
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
        "input": "Traeme el Nombre , cedula , usuario o liker lo tiene asignado, ciclo y valor del pedido de los leads o novaempresarios para el ciclo 202408, no limites la respuesta",
        "top_k": 5,
        "dialect": "MySQL",
        "agent_scratchpad": [],
    }
)
# print(prompt_val.to_string())

#############################################
##Crear agente SQL
# print('Hola mundo')
# agent = create_sql_agent(
#     llm=llm,
#     db=db,
#     prompt=full_prompt,
#     verbose=True,
#     agent_type="openai-tools",
# )


# Test the agent
# response = agent.invoke({
#     "input": "Traeme el Nombre , identificacion o cedula , usuario o liker lo tiene asignado, ciclo y valor del pedido de los leads o novaempresarios para el ciclo 202409, no limites la respuesta",
#     "top_k": 5,
#     "dialect": "MySQL",
#     "agent_scratchpad": [],
# })
##################################################

# print(formatted_prompt)
# Contar los tokens del prompt formateado
#Modelos disponibles ['gpt2', 'r50k_base', 'p50k_base', 'p50k_edit', 'cl100k_base', 'o200k_base']
# enc = tiktoken.get_encoding("gpt2")
# num_tokens = len(enc.encode(formatted_prompt))

# TOKEN_LIMIT = 5000
# return_direct = num_tokens > TOKEN_LIMIT

####################################################
###Answer to CSV

def save_to_file(data, filename):
    with open(filename, 'w') as file:
        for item in data:
            file.write(f"{item}")

####################################################
query_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=True, return_direct=True, return_sql=False)



# print(prompt_val.to_string())
sql_query = query_chain.invoke(prompt_val)

print(sql_query["result"])
print(sql_query)







## Definicion de tablas
# context = db.get_context()

# prompt_with_context = chain.get_prompts()[0].partial(table_info=context["table_info"])
# print(prompt_with_context.pretty_repr()[:1500])

#######Hacer la QA para SQL
##AAA

###



# print(db.get_usable_table_names())
# print(SQLDatabase.get_table_info(["leads_lk_pedidos_1_c"]))
# result = db_chain.invoke("Traeme todos los registros de la tabla leads")


# result = chain.invoke({"question": "Dame el saldo actual del primer registro de la tabla leads"})
##Funciones con python por promp
# save_to_file(result['result'], 'combined_results.txt')
# print(result)

# print(result['result'])
