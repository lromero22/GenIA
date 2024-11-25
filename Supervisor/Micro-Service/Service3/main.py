from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import httpx
from langgraph.graph import END, StateGraph, START
from langchain_core.runnables import RunnableLambda
from typing_extensions import TypedDict

app = FastAPI()

# Definir el prompt para el modelo
messages = [
    SystemMessage(content="Dada la conversación anterior, ¿quién debería actuar a continuación?"
                    "Si se menciona LangChain en la pregunta, seleccione 'LangChain'. Si se menciona Geologia, seleccione 'Researcher'."
                    "¿O deberíamos TERMINAR? Si no hay suficiente información, seleccione 'Researcher' por defecto.")
]

contex = [{"role": "system", "content": "Contexto inicial: El trabajador es Researcher. Researcher se encarga de investigar."}]


prompt = ChatPromptTemplate.from_messages(messages)
model = ChatOpenAI(model="gpt-4o-mini")

# Modelo para manejar la entrada
class InputData(BaseModel):
    input: str

# Definir el esquema de estado
class GraphState(TypedDict):
    input: str
    context: list
    next_action: str
    agent_response: dict

async def call_agent_1(state: GraphState) -> GraphState:
    """Llamar al agente de búsqueda de información y añadir la respuesta al estado."""
    input_data = state["input"]
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post("http://service_1:8000/researcher/", json={"input": input_data})
        response.raise_for_status()
        state["agent_response"] = response.json()

    return state

async def call_agent_2(state: GraphState) -> GraphState:
    """Llamar al agente de búsqueda de información y añadir la respuesta al estado."""
    input_data = state["input"]
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post("http://service_2:8000/products/", json={"input": input_data})
        response.raise_for_status()
        state["agent_response"] = response.json()

    return state




#######################################################################################################################
def decide_next_action(state: GraphState) -> GraphState:
    """Decidir el siguiente agente basado en la respuesta del modelo."""
    input_data = state["input"]
    context = state["context"]
    prompt_with_input = prompt.partial(input={"input": input_data}, options=["FINISH", "Researcher", "LangChain"], members=["Researcher", "LangChain"])
    runnable_chain = prompt_with_input | model
    result = runnable_chain.invoke({"input": input_data, "context": context})
    next_action = result.content.strip()  # Eliminar espacios en blanco
    state["next_action"] = next_action
    return state

def update_context(state: GraphState) -> GraphState:
    """Actualizar el contexto con la respuesta del agente."""
    context = state["context"]
    agent_response = state["agent_response"]
    context.append({"role": "agent", "content": agent_response})
    state["context"] = context
    # Actualizar next_action a "FINISH" después de procesar la respuesta del agente
    state["next_action"] = "FINISH"
    return state

async def workflow_logic(state: GraphState) -> GraphState:
    """Lógica del flujo de trabajo para manejar las transiciones."""
    while state["next_action"] != "FINISH":
        state = decide_next_action(state)
        if state["next_action"] == "Researcher":
            state = await call_agent_2(state)
            state = update_context(state)
        # elif state["next_action"] == "LangChain":
        #     state = await call_agent_1(state)
        #     state = update_context(state)
        else:
            state["context"].append({"role": "system", "content": f"El modelo respondió: {state['next_action']}. Proporcione más información."})
    return state

# Definir el flujo de trabajo con langgraph
workflow = StateGraph(state_schema=GraphState)
workflow.add_node("workflow_logic", RunnableLambda(workflow_logic))

# Definir los bordes del flujo
workflow.add_edge(START, "workflow_logic")
workflow.add_edge("workflow_logic", END)

compiled_workflow = workflow.compile()

@app.post("/test/")
async def supervisor_endpoint(data: InputData):
    try:
        state: GraphState = {
            "input": data.input,
            "context": contex,
            "next_action": "",
            "agent_response": {}
        }
        state = await compiled_workflow.ainvoke(state)  # Usar el método ainvoke en lugar de invoke
        return {"response": state["context"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))