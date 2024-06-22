# %pip install langchain openai sqlalchemy

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_openai import OpenAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain

load_dotenv()

# Set API key as environment variable
os.environ['OPENAI_API_KEY'] = os.getenv("API_KEY")

def conn_db():
    conn_str = os.getenv("CONNECTION_STRING")
    # Create a connection to the database
    engine = create_engine(conn_str)
    return engine

db_engine = conn_db()

db = SQLDatabase(engine=db_engine, include_tables=["leads", "leads_lk_pedidos_1_c", "lk_pedidos_cstm"])
llm = OpenAI(temperature=0, verbose=True)
db_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=True)

result = db_chain.invoke("Quiero saber el id del lider que tenga a las 10 personas mas vendieron y el valor de ventas, teniendo como limite inferior ventas de 400000 en los ciclos mayores a 202310, con pedidos mayores a 3. Y sabiendo que la tabla leads tiene el id del lider, la tabla leads_lk_pedidos_1_c es una tabla relacional que los leads que se relacionan con cada id de lk.")

print(result['result'])