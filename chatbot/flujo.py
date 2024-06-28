# Importación de librerías necesarias
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import time
from openai import OpenAI
import io
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import FileNotUploadedError
import pandas as pd
import datetime
from slack_sdk.errors import SlackApiError
import re
import json

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# FUNCIONES OPENIA
# Asistente y vector store IDs para OpenAI
ASSISTANT_ID = "asst_iREYxHnwpYv37MoysD1NnNod" # En produccion deben ir como variables de entorno
VECTOR_STORE_ID = "vs_CceSKFPaCVBlN7T3n8fxcOqR" # En produccion deben ir como variables de entorno

# Configuración del cliente de OpenAI con la clave API
client = OpenAI(api_key="sk-proj-QxtMQWDJPfRkJsN4ooDcT3BlbkFJbTsDMFLZcdnAedAwcX3e") # En produccion deben ir como variables de entorno

# FUNCIONES ORM FLASK

"""
# Inicialización de la aplicación Flask y configuración de la base de datos
app_flask = Flask(__name__)
app_flask.config['SQLALCHEMY_DATABASE_URI'] = '***' # En produccion deben ir como variables de entorno
db = SQLAlchemy(app_flask)

# Modelos de Datos de prueba
# Estos modelos deben adaptarse a la base de datos real antes de usarse en producción

class Registro(db.Model):
    __tablename__ = 'registros'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    ventas = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    contrasena = db.Column(db.String(80), nullable=False)

"""




def consultar_ventas(nombre, fecha_inicio, fecha_final, contrasena):
    """
    Función para consultar las ventas totales de un usuario en un rango de fechas específico.
    Esta es una función de prueba y debe ser actualizada para su uso en producción.

    Parámetros:
    nombre (str): Nombre del usuario.
    fecha_inicio (str): Fecha de inicio en formato 'YYYY-MM-DD'.
    fecha_final (str): Fecha final en formato 'YYYY-MM-DD'.
    contrasena (str): Contraseña del usuario.

    Retorna:
    str: Ventas totales en el rango de fechas o un mensaje de error.
    
    print('Se llamó a consultar_ventas')

    # Ajustar fecha_final para incluir todo el día especificado
    fecha_final = datetime.datetime.strptime(fecha_final, '%Y-%m-%d') + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
    
    # Comprobar la contraseña del usuario
    usuario = Usuario.query.filter_by(nombre=nombre).first()
    if not usuario or usuario.contrasena != contrasena:
        return 'Nombre de usuario o contraseña incorrectos'
    
    # Realizar la consulta de ventas
    ventas_totales = db.session.query(func.sum(Registro.ventas)).filter(
        Registro.nombre == nombre,
        Registro.timestamp >= fecha_inicio,
        Registro.timestamp <= fecha_final
    ).scalar()

    print(f'Se consultaron correctamente: {ventas_totales}')
    
    return f'Ventas totales: {ventas_totales}' if ventas_totales else 'Ventas totales: 0'

    """



# FUNCIONES SLACK

# Inicializa tu aplicación con el token de bot y el manejador de socket mode
app = App(token="xoxb-1690660427493-7363773808497-ExShlXcGtToPOfKQ5omvWuc0")

SUPERVISOR_USER_ID = "U06LZ2LCD6H" #En produccion debe ser un diccionario que contenga que supervisor corresponde a que liker
APPROVAL_EMOJI = "white_check_mark" #Emoji de aprobacion por parte del supervisor
CHANNEL_ID_BOT = '' #Necesario que lo pase leo, en produccion debe ser un diccionario con el id del supervisor y su respectivo chanelid con el bot
LIKERS_PERMITIDOS =[
    "U01LQ9N5WJJ",
    "U01M2V299EH",
    "U04HCJ0CE2X",
    "U0475KXJU20",
    "U01L6UJGRSS",
    "U01MB9DQF9B"
]

# Almacenamiento para los estados de los hilos
threads_slack = {}
threads_openia = {}

@app.message(".*")
def message_handler(message, say, logger):
    """
    Función manejadora de mensajes en Slack.
    Esta función se encarga de redirigir los mensajes al manejador correspondiente
    según si el mensaje proviene del supervisor o de otro usuario.

    Parámetros:
    message (dict): El mensaje recibido en Slack.
    say (func): Función para enviar mensajes en Slack.
    logger (Logger): Logger para registrar información y errores.
    """
    user_id = message['user']
    thread_ts = message.get('thread_ts')  # Obtener el thread_ts del mensaje
    # Verifica si el mensaje es del supervisor
    if user_id == SUPERVISOR_USER_ID:
        supervisor_escribe(message, say, logger,thread_ts)
    else:
        handle_liker_message(message, say)


def supervisor_escribe(message, say, logger,thread_ts):
    """
    Función que maneja los mensajes escritos por el supervisor.
    Esta función verifica el historial de conversaciones y maneja las correcciones
    proporcionadas por el supervisor a las respuestas generadas por el asistente de OpenAI.

    Parámetros:
    message (dict): El mensaje recibido en Slack.
    say (func): Función para enviar mensajes en Slack.
    logger (Logger): Logger para registrar información y errores.
    """
    
    # Obtener el historial de conversaciones del canal del bot
    result = app.client.conversations_replies(channel=CHANNEL_ID_BOT, ts=thread_ts) #app.client.conversations_history(channel=CHANNEL_ID_BOT)
    conversation_history = result["messages"][1]['text']
    
    # Extraer el ID del usuario del historial de conversación
    user_id = re.search(r'^([^:]+)', conversation_history).group(1)
    
    # Si el supervisor vuelve a escribir y el mensaje anterior no tiene el ID del usuario
    if user_id in threads_slack:
        # Asegúrate de que el mensaje fue originalmente enviado al supervisor para aprobación
        if threads_slack[user_id]['waiting_for_approval']:
            # El supervisor proporciona una corrección
            correction = message['text']

            # Ejecutar el thread con el asistente para obtener la respuesta.
            # Crear un thread en OpenAI y obtener la respuesta.
            thread_openia = client.beta.threads.retrieve(threads_openia[user_id]['thread_id'])
            
            thread_message = client.beta.threads.messages.create(
                thread_openia.id,
                role="user",
                content=correction,
            )

            run = client.beta.threads.runs.create(thread_id=thread_openia.id, assistant_id=ASSISTANT_ID)
            while run.status != "completed":
                run = client.beta.threads.runs.retrieve(thread_id=thread_openia.id, run_id=run.id)
                time.sleep(1)

            # Obtener el último mensaje del thread de OpenAI.
            message_response = client.beta.threads.messages.list(thread_id=thread_openia.id)
            messages = message_response.data
            latest_message = messages[0]
            tentative_response = latest_message.content[0].text.value

            # Actualizar la respuesta tentativa en el diccionario threads_slack
            threads_slack[user_id]['tentative_response'] = tentative_response 
            threads_slack[user_id]['waiting_for_approval'] = True

            # Enviar la respuesta actualizada al canal de Slack
            say(text=f"{user_id}: - Respuesta tentativa actualizada: {tentative_response}\nPor favor aprueba con: {APPROVAL_EMOJI}: o realice una correccion nuevamente.", thread_ts=thread_ts)
            logger.info("Supervisor correction handled and waiting for approval.")


def append_string_to_file(file_path, string_to_append):
    with open(file_path, 'a') as file:
        file.write('\n' + string_to_append + '\n')

@app.event("reaction_added")
def handle_reaction_added_events(body, say, logger):
    """
    Función que maneja los eventos de reacciones añadidas en Slack.
    Si la reacción es el emoji de aprobación, se envía la respuesta aprobada al usuario que la solicitó.

    Parámetros:
    body (dict): El cuerpo del evento recibido en Slack.
    say (func): Función para enviar mensajes en Slack.
    logger (Logger): Logger para registrar información y errores.
    """
    event = body['event']
    #print(event)

    user_id = event['user']
    reaction = event['reaction']
    item = event['item']
    channel_id = event['item']['channel']
    ts_id = event['item']['ts']

    # Llamar al método conversations.history usando el WebClient para obtener el mensaje original
    result = app.client.conversations_history(
        channel=channel_id,
        inclusive=True,
        oldest=ts_id,
        limit=1
    )

    message = result["messages"][0]['text']
    #print(message)

    #print(re.search(r'^([^:]+)', message).group(1))

    #print(threads_slack)

    # Verificar si la reacción es el emoji de aprobación y si es en un thread que estamos manejando
    if reaction == APPROVAL_EMOJI and re.search(r'^([^:]+)', message).group(1) in threads_slack:
        #print('entro al if')
        # Obtener el user_id del mensaje original
        user_id = re.search(r'^([^:]+)', message).group(1)

        # Asegurarse de que el mensaje fue originalmente enviado al supervisor para aprobación
        if threads_slack[user_id]['waiting_for_approval']:
            # Obtener la respuesta aprobada y el thread_slack_id del liker
            response = threads_slack[user_id]['tentative_response']
            liker_thread_slack_id = threads_slack[user_id]['liker_thread_ts']

            # Enviar la respuesta aprobada al liker
            app.client.chat_postMessage(
                channel=user_id,
                text=f"Respuesta aprobada por el supervisor {user_id}: {response}",
                thread_ts=liker_thread_slack_id
            )
            append_string_to_file('correcciones_supervisor.txt', f"Respuesta aprobada por el supervisor {user_id}: {response}")
            # Opcionalmente, limpiar el estado del thread
            del threads_slack[user_id]
            logger.info("Approved response sent to liker.")
    else:
        logger.info(f"Reaction {reaction} added by {user_id} but no action taken.")




def handle_liker_message(message, say):
    """
    Función que maneja los mensajes del 'liker' en Slack.
    Si el mensaje requiere una acción, se invoca la función correspondiente.
    Si no, se envía la respuesta tentativa al supervisor para su aprobación.

    Parámetros:
    message (dict): El mensaje recibido en Slack.
    say (func): Función para enviar mensajes en Slack.
    """
    
    user_id = message['user']
    
    thread_slack_id = message['ts']
    consulta_basedatos = False
    
    # Guardar el estado inicial del 'thread' en el diccionario threads_slack.
    threads_slack[user_id] = {
        'liker_thread_ts': thread_slack_id,
        'liker_user_id': user_id
    }

    # Extraer el contenido del mensaje del 'liker'.
    liker_message_text = message['text']

    # Si el liker no tiene permitido hablar con el bot detiene la ejecucion
    if user_id not in LIKERS_PERMITIDOS:
        say(text='Aun no tienes permitido interactuar con nuestro bot.', thread_ts=threads_slack[user_id]['liker_thread_ts'])
        return
    
    # Crear un thread en OpenAI con el mensaje del 'liker'.
    thread_openia = client.beta.threads.create(
        messages=[
            {"role": "user", "content": liker_message_text}
        ]
    )

    tool_outputs = []
    # Ejecutar el thread con el asistente para obtener la respuesta.
    run = client.beta.threads.runs.create(thread_id=thread_openia.id, assistant_id=ASSISTANT_ID)
    while run.status != "completed":
        # Consultar el estado del run hasta que se complete.
        run = client.beta.threads.runs.retrieve(thread_id=thread_openia.id, run_id=run.id)
        print(f"🏃 Estado de la corrida: {run.status}")

        # Si el estado del run requiere una acción, marcar consulta_basedatos como True.
        if run.status == 'requires_action':
            consulta_basedatos = True
            # Recorrer cada herramienta en la sección de acción requerida.
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                # Verificar si la herramienta requerida es "consultar_ventas".
                if tool.function.name == "consultar_ventas":
                    # Extraer los argumentos necesarios para la consulta de ventas.
                    nombre = json.loads(tool.function.arguments)["nombre"]
                    fecha_inicio = json.loads(tool.function.arguments)["fecha_inicio"]
                    fecha_final = json.loads(tool.function.arguments)["fecha_final"]
                    contrasena = json.loads(tool.function.arguments)["contrasena"]

                    # Ejecutar la función consultar_ventas con los argumentos extraídos.
                    with app_flask.app_context():
                        result = consultar_ventas(nombre, fecha_inicio, fecha_final, contrasena)
                    # Agregar el resultado de la herramienta a tool_outputs.
                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": result
                    })

            if tool_outputs:
                try:
                    # Enviar los resultados de las herramientas a OpenAI y continuar el run.
                    run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                        thread_id=thread_openia.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                    print("Tool outputs submitted successfully.")
                except Exception as e:
                    print("Failed to submit tool outputs:", e)
            else:
                print("No tool outputs to submit.")

        time.sleep(1)

    # Obtener el último mensaje del thread de OpenAI después de completar el run.
    message_response = client.beta.threads.messages.list(thread_id=thread_openia.id)
    messages = message_response.data
    latest_message = messages[0]
    tentative_response = latest_message.content[0].text.value
    
    # Actualizar el diccionario threads_slack con la respuesta tentativa y marcarla como esperando aprobación.
    threads_slack[user_id]['tentative_response'] = tentative_response
    threads_slack[user_id]['waiting_for_approval'] = True

    # Guardar el ID del thread de OpenAI en threads_openia.
    threads_openia[user_id] = {
        'thread_id': thread_openia.id
    }
    print(tentative_response)
    
    # Enviar la respuesta tentativa al supervisor para su aprobación si no es una consulta a la base de datos.
    if consulta_basedatos:
        # Si es una consulta a la base de datos, enviar la respuesta directamente al thread del 'liker'.
        say(text=tentative_response, thread_ts=threads_slack[user_id]['liker_thread_ts'])
    else:
        try:
            # Si no es una consulta a la base de datos, enviar la respuesta tentativa al supervisor para aprobación.
            app.client.chat_postMessage(
                channel=SUPERVISOR_USER_ID,
                text=f"{user_id}: hizo la siguiente pregunta: {liker_message_text}\nRespuesta tentativa: {tentative_response}\nPor favor aprueba con: {APPROVAL_EMOJI} o realice una correccion.",
                thread_ts=thread_slack_id
            )
        except SlackApiError as e:
            print(f"Error sending message: {e}")










# Start your app
if __name__ == "__main__":
    SocketModeHandler(app,"xapp-1-A07A7T15TD2-7345447999506-eee009a417c1705f27ff0acd4fafb6f2b472f79dc29fdea98bad6f9bfc99e49a").start()