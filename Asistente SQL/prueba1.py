#pip install langchain openai sqlalchemy python-dotenv langchain-openai langchain-experimental pymysql faiss-cpu
import os
import ast
import re
from operator import itemgetter
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI

# Configura la API key de OpenAI como variable de entorno
os.environ['OPENAI_API_KEY'] = os.getenv("API_KEY")

# Función para conectar a la base de datos
def connect_db():
    conn_str = os.getenv("CONNECTION_STRING")
    engine = create_engine(conn_str)
    return engine


# Crear el motor de la base de datos
db_engine = connect_db()

# Especificar las tablas a incluir
db = SQLDatabase(engine=db_engine, include_tables=["lk_pedidos_cstm"])

# Configurar el modelo de lenguaje
llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0.2,
        max_tokens=1000,
    )

# Crear el SQLDatabaseChain
db_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=True)

# Función para obtener valores únicos de una consulta y procesarlos
# def query_as_list(db, query):
#     res = db.run(query)
#     res = [el for sub in ast.literal_eval(res) for el in sub if el]
#     res = [re.sub(r"\b\d+\b", "", string).strip() for string in res]
#     return res

def query_as_list(db, query):
    res = db.run(query)

    try:
        # Try to parse the result into a list of elements
        res = ast.literal_eval(res)
    except Exception as e:
        print("Error parsing result:", e)
        res = []

    # Flatten the list of tuples into a single list of elements
    res = [str(el).strip() for sub in res for el in sub if el]

    return res

# Assuming `db` is already defined and connected
# proper_nouns = query_as_list(db, "SELECT DISTINCT id_c FROM lk_pedidos_cstm LIMIT 1000")
proper_nouns = query_as_list(db, "SELECT DISTINCT id_c FROM lk_pedidos_cstm LIMIT 1000")
proper_nouns += query_as_list(db, "SELECT DISTINCT ciclo_c FROM lk_pedidos_cstm LIMIT 1000")

# Print the first 5 elements
print(proper_nouns[:5])

# Check if proper_nouns is None or empty
if proper_nouns is None:
    print("Error: `proper_nouns` is None")
elif len(proper_nouns) == 0:
    print("Error: `proper_nouns` is empty")
else:
    print("Proper nouns:", proper_nouns[:5])


print(type(proper_nouns))

# Obtener valores únicos de las columnas relevantes
# proper_nouns = query_as_list(db, "SELECT DISTINCT id_c FROM lk_pedidos_cstm LIMIT 1000")
# proper_nouns += query_as_list(db, "SELECT DISTINCT ciclo_c FROM lk_pedidos_cstm LIMIT 1000")
# proper_nouns += query_as_list(db, "SELECT DISTINCT valor_venta_sin_iva_c FROM lk_pedidos_cstm")

# print(proper_nouns[:5])

# Inicializar HuggingFaceEmbeddings
model_name = "symanto/sn-xlm-roberta-base-snli-mnli-anli-xnli"
embedding_hf = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': False}
)

# # Crear y configurar el vector store
vector_db = FAISS.from_texts(proper_nouns, embedding_hf)
retriever = vector_db.as_retriever(search_kwargs={})

# Crear y configurar el vector store usando FAISS


##HASTA AQUI ESTAMOS BN
print("Punto de control 1")

# embeddings = embedding_hf.embed_documents(proper_nouns)
print("Punto de control 2")

# embeddings = np.array(embeddings)

# index = faiss.IndexFlatL2(embeddings.shape[1])
print("Punto de control 3")

# index.add(embeddings)
print("Punto de control 4")

# Guardar el índice FAISS
print("Punto de control 5")

# faiss.write_index(index, 'faiss_index.bin')
print("Punto de control 6")

# Cargar el índice FAISS
# index = faiss.read_index('faiss_index.bin')
# index_to_docstore_id = {i: str(i) for i in range(len(proper_nouns))}

# Convertir el índice en un vectorstore
print("Punto de control 7")
# vectorstore = FAISS(
#     embedding_function=embedding_hf,
#     index=index,
#     docstore=proper_nouns,
#     index_to_docstore_id=index_to_docstore_id
# )
print("Punto de control 8")


# retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
# retriever = vectorstore.as_retriever(search_kwargs={})

print("Punto de control 9")



# Definir el sistema de prompt
system = """Eres un experto en SQL. Dada una pregunta de entrada, crea una consulta SQL sintácticamente correcta para ejecutar. A menos que se especifique lo contrario, no devuelvas más de {top_k} filas.\n\nAquí está la información relevante de la tabla: {table_info}\n\nAquí hay una lista no exhaustiva de posibles valores de características. Si filtras en un valor de característica, asegúrate de verificar su ortografía contra esta lista primero:\n\n{proper_nouns}"""

print("Punto de control 10")
# Crear el template de prompt
prompt = ChatPromptTemplate.from_messages([("system", system), ("human", "{input}")])

print("Punto de control 11")
# Crear la cadena de consulta SQL
query_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, prompt=prompt)

print("Punto de control 12")
# Crear la cadena de recuperación de valores
retriever_chain = (
    itemgetter("question")
    | retriever
    | (lambda docs: "\n".join(doc.page_content for doc in docs))
)
print("Punto de control 13")
# Crear la cadena completa
chain = RunnablePassthrough.assign(proper_nouns=retriever_chain) | query_chain
print("Punto de control 14")
# Probar la cadena con y sin recuperación de valores
inputs = {
    "query": "¿Quiero ver los ids de pedidos que el valor de pedido en 202408 está en 0?",
    "proper_nouns": proper_nouns
}
print(proper_nouns)


print("Punto de control 16")

query_without_retrieval = query_chain.invoke(inputs)
print("Punto de control 17")

print("Query without retrieval:", query_without_retrieval)

print("Punto de control 18")
print(db.run(query_without_retrieval))

print("Punto de control 19")


query_with_retrieval = chain.invoke(inputs)

print('20')
print("Query with retrieval:", query_with_retrieval)
print(db.run(query_with_retrieval))