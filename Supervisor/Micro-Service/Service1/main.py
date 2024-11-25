from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import httpx

app = FastAPI()

# Modelo para manejar la entrada
class InputData(BaseModel):
    input: str

def retriever(data: InputData):


    return data.input

model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    )

loader = DirectoryLoader(
			'.',
			glob='**/*.pdf',
			loader_cls=PyPDFLoader
	 )

pages = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
)

splits = text_splitter.split_documents(pages)

embeddings = OpenAIEmbeddings()
vector_store = Chroma.from_documents(
    embedding=embeddings,
    documents = splits
)

retriever = vector_store.as_retriever()


prompt_template = ChatPromptTemplate.from_template(
    "Responde esta pregunta: {input} con el contexto dado {context}"
)



@app.post("/researcher/")
async def products_endpoint(data: InputData):
    try:
        # Recuperar el contexto relevante del PDF
        context_docs = retriever.invoke(data.input)
        context = " ".join([doc.page_content for doc in context_docs])

        # Crear el prompt con el contexto y la pregunta del usuario
        prompt_with_context = prompt_template.partial(context=context, input={"input": data.input})
        runnable_chain = prompt_with_context | model

        # Obtener la respuesta del modelo
        result = runnable_chain.invoke({"context": context, "input": data.input})

        return {"response": result.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))