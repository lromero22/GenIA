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
from datetime import datetime
from slack_sdk.errors import SlackApiError
import re
import json
import mysql.connector

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# FUNCIONES OPENIA
# Asistente y vector store IDs para OpenAI
ASSISTANT_ID = "openai_assitant_id" # En produccion deben ir como variables de entorno
VECTOR_STORE_ID = "openai_vector_store_id" # En produccion deben ir como variables de entorno

# Configuración del cliente de OpenAI con la clave API
client = OpenAI(api_key="openai_api_key") # En produccion deben ir como variables de entorno

# Inicializa tu aplicación con el token de bot y el manejador de socket mode
slack_token = "slack_app_id"
app = App(token = slack_token)

#En produccion debe ser un diccionario que contenga que supervisor corresponde a que liker
SUPERVISOR_USER_ID = {"U06SGR43U1G": 'U07BNLU9KT2'
                      } #"U06LZ2LCD6H"
APPROVAL_EMOJI = "white_check_mark" #Emoji de aprobacion por parte del supervisor
#CHANNEL_ID_BOT = 'D07C74UCTA4' #Necesario que lo pase leo, en produccion debe ser un diccionario con el id del supervisor y su respectivo chanelid con el bot
LIKERS_PERMITIDOS =[
    "U06SGR43U1G" #ID de Juanjo para hacer pruebas
]

# Diccionario con los ID de usuarios y sus respectivos nombres
import requests
users_info = {}
headers = {
        'Authorization': f'Bearer {slack_token}'
    }
for id in LIKERS_PERMITIDOS + list(SUPERVISOR_USER_ID.values()):
    response = requests.get('https://slack.com/api/users.info', headers = headers, params = {'user': id})
    user_info = response.json().get("user")
    users_info[id] = user_info["profile"].get("real_name")

# ID del Asistente de OpenAI en Slack (Aplicación de Slack)
slack_id_assistant = 'U07DXQYJMRP' # Solución simplista

# ------------------------------------------------------------------------------------------------------------------------------------
# FUNCIONES PARA INSERTAR Y ACTUALIZAR LA INFORMACION DE LOS MENSAJES EN LA BASE DE DATOS MySQL
# Función para insertar un mensaje en la base de datos
def insert_message(values, user, password, host, database):
    """ 
    Funcion para insertar la informacion de los mensajes del diccionario threads_slack

    values (tuple): Tupla con los respectivos valores a insertar en la base de datos con el historico de mensajes.
    user (string): Usuario de la base de datos.
    password (string): Contrasena de la base de datos
    host (string): Servidor de la base de datos
    database (string): Nombre de la base de datos
    """

    # Configuración de la conexión
    db_config = {
        'user': user,
        'password': password,
        'host': host,
        'database': database
    }

    # Crear la conexión
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    consulta = """
        INSERT INTO messages (liker_thread_ts, liker_user_id, liker, question, question_date, tentative_response, update_response, correction, id_supervisor_who_solves, supervisor_who_solves, id_supervisor_who_approves, supervisor_who_approves, response_date, required_correction, required_approval)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    cursor.execute(consulta, values)
    conn.commit()

    # Cerrar la conexión
    cursor.close()
    conn.close()

# Función para actualizar un mensaje en la base de datos
def update_message(liker_thread_ts, threads_slack, user, password, host, database):
    # Configuración de la conexión
    db_config = {
        'user': user,
        'password': password,
        'host': host,
        'database': database
    }

    # Crear la conexión
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    
    sql = "UPDATE messages SET "
    fields = []
    values = []

    if threads_slack["tentative_response"] is not None:
        fields.append("tentative_response = %s")
        values.append(threads_slack['tentative_response'])
    if threads_slack["update_response"] is not None:
        fields.append("update_response = %s")
        values.append(threads_slack['update_response'])
    if threads_slack["correction"] is not None:
        fields.append("correction = %s")
        values.append(threads_slack['correction'])
    if threads_slack["id_supervisor_who_solves"] is not None:
        fields.append("id_supervisor_who_solves = %s")
        values.append(threads_slack['id_supervisor_who_solves'])
    if threads_slack["supervisor_who_solves"] is not None:
        fields.append("supervisor_who_solves = %s")
        values.append(threads_slack['supervisor_who_solves'])
    if threads_slack["id_supervisor_who_approves"] is not None:
        fields.append("id_supervisor_who_approves = %s")
        values.append(threads_slack['id_supervisor_who_approves'])
    if threads_slack["supervisor_who_approves"] is not None:
        fields.append("supervisor_who_approves = %s")
        values.append(threads_slack['supervisor_who_approves'])
    if threads_slack["response_date"] is not None:
        fields.append("response_date = %s")
        values.append(threads_slack['response_date'])
    if threads_slack["required_correction"] is not None:
        fields.append("required_correction = %s")
        values.append(threads_slack['required_correction'])
    if threads_slack["required_approval"] is not None:
        fields.append("required_approval = %s")
        values.append(threads_slack['required_approval'])

    if not fields:
        raise ValueError("No fields to update")

    sql += ", ".join(fields) + " WHERE liker_thread_ts = %s"
    values.append(liker_thread_ts)

    # cursor.execute(sql, tuple(values))
    cursor.execute(sql, tuple(values))
    conn.commit()

    # Cerrar la conexión
    cursor.close()
    conn.close()

# Credenciales de la base de datos
db_credentials = {
    'user': 'root',
    'password': 'Rustinpeace4+',
    'host': 'localhost',
    'database': 'sakila'
}
# ------------------------------------------------------------------------------------------------------------------------------------

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
    if user_id in SUPERVISOR_USER_ID.values():
        supervisor_escribe(message, say, logger, thread_ts)
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

    # Se puede extraer el canal del bot desde el message. Tambien el id del supervisor
    bot_channel_id = message.get('channel')
    # supervisor_user_id = message.get('user')

    # Obtener el historial de conversaciones del canal del bot
    result = app.client.conversations_replies(channel=bot_channel_id, ts=thread_ts) #app.client.conversations_history(channel=CHANNEL_ID_BOT)
    conversation_history = result["messages"][0]['text']
    # Extraer el ID del usuario del historial de conversación
    pattern = r'\|(.*?)\|'
    key = re.findall(pattern,  conversation_history)
    #user_id = re.search(r'\bU\w+\b', conversation_history).group()
    key=key[0]
    info_msj=key.split("-")
    user_id=info_msj[0]
    correction = message['text']
    # Enviar la corrección al hilo del empleado que hizo la pregunta
    try:
        """ app.client.chat_postMessage(
            channel=channel_bot,
            text=f"Corrección del supervisor: {correction}",
            thread_ts=thread_ts
        ) """

        # Anadir la respuesta corregida al diccionario threads_slack
        threads_slack[key]['correction'] = correction 
        threads_slack[key]['waiting_for_approval'] = True
        threads_slack[key]['update_response']= True
        
        say(text=f"{users_info[user_id]} - |{key}| - Respuesta tentativa actualizada: {correction}\nPor favor aprueba con: :{APPROVAL_EMOJI}: o realice una correccion nuevamente.", thread_ts=thread_ts)
        logger.info(f"Corrección enviada al empleado {users_info[user_id]} en el canal {bot_channel_id}.")
    except Exception as e:
        logger.error(f"Error enviando la corrección: {e}")

def append_string_to_file(file_path, string_to_append):
    with open(file_path, 'a') as file:
        file.write('\n' + string_to_append + '\n')

@app.event("reaction_added")
def handle_reaction_added_events(body, logger):
    """
    Función que maneja los eventos de reacciones añadidas en Slack.
    Si la reacción es el emoji de aprobación, se envía la respuesta aprobada al usuario que la solicitó.

    Parámetros:
    body (dict): El cuerpo del evento recibido en Slack.
    say (func): Función para enviar mensajes en Slack.
    logger (Logger): Logger para registrar información y errores.
    """
    event = body['event']
    supervisor_user_id = event['user']
    reaction = event['reaction']
    # slack_id_assistant = body['authorizations'][0]['user_id'] # ID del Asistente de OpenAI en Slack
    channel_id = event['item']['channel']
    ts_id = event['item']['ts']

    message = None
    # Intentar obtener el mensaje del hilo
    try:
        result = app.client.conversations_replies(
            channel=channel_id,
            ts=ts_id
        )
        if result["messages"]:
            message = result["messages"][0]['text']
    except Exception as e:
        logger.error(f"Error fetching thread messages: {e}")

    # Si no se encontraron mensajes en el hilo, intentar obtener el mensaje del canal principal
    if not message:
        try:
            result = app.client.conversations_history(
                channel=channel_id,
                inclusive=True,
                oldest=ts_id,
                limit=1
            )
            if result["messages"]:
                message = result["messages"][0]['text']
        except Exception as e:
            logger.error(f"Error fetching channel messages: {e}")

    if message:
        
        pattern = r'\|(.*?)\|'
        key = re.findall(pattern,  message)
        key=key[0]
        
        info_msj=key.split("-")
        user_id=info_msj[0]
        # Verificar si la reacción es el emoji de aprobación y si es en un thread que estamos manejando
        if reaction == APPROVAL_EMOJI and key in threads_slack:
            # Asegurarse de que el mensaje fue originalmente enviado al supervisor para aprobación
            if threads_slack[key]['waiting_for_approval']:
                # NOTA: En este punto, tendría sentido setear el waiting for approval a False porque con las condiciones
                # dadas la pregunta ha sido resuelta, sin embargo, tampoco tiene algun tipo de efecto en los pasos a seguir
                
                # Se Agrega especifica el supervisor que aprobo la correcion (quien uso el emoji de aprobacion)
                threads_slack[key]['id_supervisor_who_approves'] = supervisor_user_id
                threads_slack[key]['supervisor_who_approves'] = users_info[supervisor_user_id]
                
                # Verificar de donde se saca la respuesta a enviar al liker: la tentativa o la corregida                    
                if threads_slack[key]['update_response']:
                    response = threads_slack[key]['correction']
                    # Identificacion del supervisor que responde la duda
                    threads_slack[key]['id_supervisor_who_solves'] = supervisor_user_id
                    threads_slack[key]['supervisor_who_solves'] = users_info[supervisor_user_id]
                    threads_slack[key]['response_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    threads_slack[key]['required_correction'] = True
                else:
                    response = threads_slack[key]['tentative_response']     
                    threads_slack[key]['id_supervisor_who_solves'] = slack_id_assistant
                    threads_slack[key]['supervisor_who_solves'] = 'Asistente OpenAI'
                    threads_slack[key]['response_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    threads_slack[key]['required_correction'] = False
                response = re.sub('【.*?†source】', '', response) # Limpieza de posibles referencias de archivos por el asistente

                # Si entro a esta parte del flujo, es porque necesito algún tipo de aprobacion
                threads_slack[key]['required_approval'] = True
                liker_thread_slack_id = threads_slack[key]['liker_thread_ts']

                # Enviar la respuesta aprobada al liker
                app.client.chat_postMessage(
                    channel=user_id,
                    text=f"Respuesta aprobada por el supervisor {users_info[supervisor_user_id]} - {supervisor_user_id} : {response}",
                    thread_ts=liker_thread_slack_id
                )
                fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if threads_slack[key]['update_response']:
                    append_string_to_file('preguntas_totales.txt', f"{fecha_actual}|{threads_slack[key]['question']}|{response}|Corregida")    
                    append_string_to_file('correcciones_supervisor.txt', f"{fecha_actual} - Pregunta: {threads_slack[key]['question']} - Respuesta: {response}")
                else:
                    append_string_to_file('preguntas_totales.txt', f"{fecha_actual}|{threads_slack[key]['question']}|{response}|Sin_correccion")        

                # Tupla para agregar a la posterior base de datos MySQL
                del threads_slack[key]['waiting_for_approval']
                row = threads_slack[key]
                row = tuple(row.values())
                liker_thread_ts = threads_slack[key]['liker_thread_ts']
                update_message(liker_thread_ts, threads_slack[key], db_credentials['user'], db_credentials['password'], db_credentials['host'], db_credentials['database'])
                # Opcionalmente, limpiar el estado del thread
                del threads_slack[key]
                logger.info("Approved response sent to liker.")
        else:
            logger.info(f"Reaction {reaction} added by {users_info[supervisor_user_id]} but no action taken.")
    else:
        logger.error(f"No messages found for channel {channel_id} with timestamp {ts_id}.")

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
    key = user_id + "-" + thread_slack_id
    # Guardar el estado inicial del 'thread' en el diccionario threads_slack.
    liker_message_text = message['text']
    threads_slack[key] = {
        'liker_thread_ts': thread_slack_id,
        'liker_user_id': user_id,
        'liker': users_info[user_id],
        'question': liker_message_text,
        'question_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tentative_response': None,
        'waiting_for_approval': None, # Esta key es usada en el flujo de manejo de mensajes pero NO HACE PARTE DE LA BD
        'update_response': None,
        'correction': None,
        'id_supervisor_who_solves': None,
        'supervisor_who_solves': None,
        'id_supervisor_who_approves': None,
        'supervisor_who_approves': None,
        'response_date': None,
        'required_correction': None,
        'required_approval': None
    }

    # Extraer el contenido del mensaje del 'liker'.
    # Si el liker no tiene permitido hablar con el bot detiene la ejecucion
    if user_id not in LIKERS_PERMITIDOS:
        say(text='Aun no tienes permitido interactuar con nuestro bot.', thread_ts=threads_slack[key]['liker_thread_ts'])
        return
    
    # Crear un thread en OpenAI con el mensaje del 'liker'.
    thread_openia = client.beta.threads.create(
        messages=[
            {"role": "user", "content": liker_message_text}
        ]
    )

    # Ejecutar el thread con el asistente para obtener la respuesta.
    run = client.beta.threads.runs.create(thread_id=thread_openia.id, assistant_id=ASSISTANT_ID)
    while run.status != "completed":
        # Consultar el estado del run hasta que se complete.
        run = client.beta.threads.runs.retrieve(thread_id=thread_openia.id, run_id=run.id)
        print(f"🏃 Estado de la corrida: {run.status}")
        #time.sleep(1)

    # Obtener el último mensaje del thread de OpenAI después de completar el run.
    message_response = client.beta.threads.messages.list(thread_id=thread_openia.id)
    messages = message_response.data
    latest_message = messages[0]
    tentative_response = latest_message.content[0].text.value
    tentative_response = re.sub('【.*?†source】', '', tentative_response) # Limpieza de las referencias de los archivos
    threads_slack[key]['tentative_response'] = tentative_response # Se anade la respuesta tentativa de una vez

    print(tentative_response)
    pattern = r'【.*?†source】'
    if re.search(pattern, tentative_response) is None and len(tentative_response) < 75:
        app.client.chat_postMessage(
                    channel=user_id,
                    text=f"{tentative_response}",
                    thread_ts=thread_slack_id
                )
        
        # Keys adicionales necesarias en threads_slack
        threads_slack[key]['waiting_for_approval'] = False
        threads_slack[key]['update_response'] = False
        threads_slack[key]['id_supervisor_who_solves'] = slack_id_assistant
        threads_slack[key]['supervisor_who_solves'] = 'Asistente_OpenAI'
        threads_slack[key]['response_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        threads_slack[key]['required_correction'] = False
        threads_slack[key]['required_approval'] = False

        # Tupla para agregar a la posterior base de datos MySQL
        del threads_slack[key]['waiting_for_approval']
        row = threads_slack[key]
        row = tuple(row.values())
        insert_message(row, db_credentials['user'], db_credentials['password'], db_credentials['host'], db_credentials['database'])
        # Opcionalmente, limpiar el estado del thread
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        append_string_to_file('preguntas_totales.txt', f"{fecha_actual}|{threads_slack[key]['question']}|{tentative_response}|Bot")
        del threads_slack[key]
    else:
        # Actualizar el diccionario threads_slack con la respuesta tentativa y marcarla como esperando aprobación.
        threads_slack[key]['waiting_for_approval'] = True
        threads_slack[key]['update_response'] = False
        # Guardar el ID del thread de OpenAI en threads_openia.
        threads_openia[user_id] = {
            'thread_id': thread_openia.id
        }

        # Creacion de la fila a insertar en la base de datos (se debe excluir la key 'waiting_for_approval')
        copy = threads_slack[key].copy() # Copia del diccionario threads_slack[key] para insertar la fila en la BD
        del copy['waiting_for_approval']
        
        row = copy
        row = tuple(row.values())
        del copy # Eliminacion de la copia del diccionario threads_slack

        # Insertar el mensaje en la base de datos
        insert_message(row, db_credentials['user'], db_credentials['password'], db_credentials['host'], db_credentials['database'])

        # Enviar la respuesta tentativa al supervisor para su aprobación si no es una consulta a la base de datos.
        try:
            # Si no es una consulta a la base de datos, enviar la respuesta tentativa al supervisor para aprobación.
            app.client.chat_postMessage(
                channel=SUPERVISOR_USER_ID.get(user_id),
                text=f"{users_info[user_id]} - |{key}| hizo la siguiente pregunta: {liker_message_text}\nRespuesta tentativa: {tentative_response}\nPor favor aprueba con: :{APPROVAL_EMOJI}: o realice una correccion.",
                thread_ts=thread_slack_id
            )
        except SlackApiError as e:
            print(f"Error sending message: {e}")










# Start your app
if __name__ == "__main__":
    SocketModeHandler(app,"socket_token").start()