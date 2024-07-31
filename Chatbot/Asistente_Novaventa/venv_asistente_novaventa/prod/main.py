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

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# FUNCIONES OPENIA
# Asistente y vector store IDs para OpenAI
ASSISTANT_ID = "assistant_id" # En produccion deben ir como variables de entorno
VECTOR_STORE_ID = "vector_store_id" # En produccion deben ir como variables de entorno

# Configuración del cliente de OpenAI con la clave API
client = OpenAI(api_key="openai_api_key") # En produccion deben ir como variables de entorno

# FUNCIONES ORM FLASK



#def consultar_ventas(nombre, fecha_inicio, fecha_final, contrasena):
# Inicializa tu aplicación con el token de bot y el manejador de socket mode
slack_token = "slack_bot_id"
app = App(token = slack_token)

#En produccion debe ser un diccionario que contenga que supervisor corresponde a que liker
SUPERVISOR_USER_ID = {"U01M3018BTP":'U06LZ2LCD6H',
                        "U01MB9DQF9B":'U06LZ2LCD6H',
                        "U02GPR4Q53N":'U06LZ2LCD6H',
                        "U038KKVH4MU":'U06LZ2LCD6H',
                        "U03P9SFSR1P":'U06LZ2LCD6H',
                        "U03V2JYN88M":'U06LZ2LCD6H',
                        "U059YRK763H":'U06LZ2LCD6H',
                        "U05HCERJB8D":'U06LZ2LCD6H',
                        "U05KFL9AP3N":'U06LZ2LCD6H',
                        "U05QK7ZCXE0":'U06LZ2LCD6H',
                        "U05QVD2BVG9":'U06LZ2LCD6H',
                        "U06A0C0D1NF":'U06LZ2LCD6H',
                        "U06KSP5257V":'U06LZ2LCD6H',
                        "U06Q21KTC3V":'U06LZ2LCD6H',
                        "U07A0S73FM3":'U06LZ2LCD6H',
                        "U07A3KB887M":'U06LZ2LCD6H',
                        "U07AGCX5G1F":'U06LZ2LCD6H',
                        "U07ASGG0LN4":'U06LZ2LCD6H',
                        "U078K3FE1MF":'U06LZ2LCD6H',
                        "U01L6UJGRSS":'U06LZ2LCD6H',
                        "U01L71AMFPG":'U06LZ2LCD6H',
                        "U01LQ9N5WJJ":'U06LZ2LCD6H',
                        "U01M2V299EH":'U06LZ2LCD6H',
                        "U01MB9DQF9B":'U06LZ2LCD6H',
                        "U04229KLR6E":'U06LZ2LCD6H',
                        "U0475KXJU20":'U06LZ2LCD6H',
                        "U04HCJ0CE2X":'U06LZ2LCD6H',
                        "U06SGR43U1G":'U06LZ2LCD6H',
                      } #"U06LZ2LCD6H"
APPROVAL_EMOJI = "white_check_mark" #Emoji de aprobacion por parte del supervisor
#CHANNEL_ID_BOT = 'D07C74UCTA4' #Necesario que lo pase leo, en produccion debe ser un diccionario con el id del supervisor y su respectivo chanelid con el bot
LIKERS_PERMITIDOS =[
    "U01L6UJGRSS",
"U01L71AMFPG",
"U01M2V299EH",
"U01M3018BTP",
"U01MB9DQF9B",
"U02GPR4Q53N",
"U038KKVH4MU",
"U03P9SFSR1P",
"U03V2JYN88M",
"U04229KLR6E",
"U0475KXJU20",
"U04HCJ0CE2X",
"U059YRK763H",
"U05HCERJB8D",
"U05KFL9AP3N",
"U05QK7ZCXE0",
"U05QVD2BVG9",
"U06A0C0D1NF",
"U06KSP5257V",
"U06Q21KTC3V",
"U06SGR43U1G",
"U078K3FE1MF",
"U07A0S73FM3",
"U07A3KB887M",
"U07AGCX5G1F",
"U07ASGG0LN4",
"U01LQ9N5WJJ"
 #ID de Juanjo para hacer pruebas    
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

        # Actualizar la respuesta tentativa en el diccionario threads_slack
        
        threads_slack[key]['tentative_response'] = correction 
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
    supervisor_user_id = event['user']
    reaction = event['reaction']
    item = event['item']
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
            # Obtener el user_id del mensaje original
            #user_id = re.search(r'\bU\w+\b', message).group()
            # Asegurarse de que el mensaje fue originalmente enviado al supervisor para aprobación
            if threads_slack[key]['waiting_for_approval']:
                # Obtener la respuesta aprobada y el thread_slack_id del liker
                response = threads_slack[key]['tentative_response']
                response = re.sub('【.*?†source】', '', response) # Limpieza de posibles referencias de archivos por el asistente
                liker_thread_slack_id = threads_slack[key]['liker_thread_ts']

                # Enviar la respuesta aprobada al liker
                app.client.chat_postMessage(
                    channel=user_id,
                    text=f"Respuesta aprobada por el supervisor {users_info[supervisor_user_id]} - {supervisor_user_id} : {response}",
                    thread_ts=liker_thread_slack_id
                )
                fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if threads_slack[key]['update_response']:
                    append_string_to_file('preguntas_totales.txt', f"{fecha_actual}|{threads_slack[key]['pregunta']}|{response}|Corregida")    
                    append_string_to_file('correcciones_supervisor.txt', f"{fecha_actual} - Pregunta: {threads_slack[key]['pregunta']} - Respuesta: {response}")
                else:
                    append_string_to_file('preguntas_totales.txt', f"{fecha_actual}|{threads_slack[key]['pregunta']}|{response}|Sin_correccion")        
                    
                # Opcionalmente, limpiar el estado del thread
                del threads_slack[key]
                logger.info("Approved response sent to liker.")
        else:
            logger.info(f"Reaction {reaction} added by {users_info[supervisor_user_id]} but no action taken.")
    else:
        logger.error(f"No messages found for channel {channel_id} with timestamp {ts_id}.")


def es_saludo(mensaje):
    saludos = ["¡Hola! ¿En qué puedo ayudarte hoy?", 
               "Estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?",
                "Estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?",
                "¡De nada! Estoy aquí para ayudarte en lo que necesites. Si tienes alguna otra pregunta o necesitas más información, no dudes en decírmelo. ¡Estoy aquí para asistirte!",
                "¡De nada! Estoy aquí para ayudarte en lo que necesites. ¿Hay algo más en lo que pueda asistirte hoy?",
                "¡De nada! Estoy aquí para ayudarte. ¿Hay algo más en lo que pueda asistirte?"
                ]
    for saludo in saludos:
        if saludo in mensaje:
            return True
    return False

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
    #consulta_basedatos = False
    key=user_id+"-"+thread_slack_id
    # Guardar el estado inicial del 'thread' en el diccionario threads_slack.
    liker_message_text = message['text']
    threads_slack[key] = {
        'liker_thread_ts': thread_slack_id,
        'liker_user_id': user_id,
        'pregunta': liker_message_text
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
    print(tentative_response)
    pattern = r'【.*?†source】'
    #if re.search(pattern, tentative_response) is None and not tentative_response.startswith("No se encontró"):
    #if re.search(pattern, tentative_response) is None and not tentative_response.startswith("No se encontró"):
    if re.search(pattern, tentative_response) is None and len(tentative_response) < 50:
        app.client.chat_postMessage(
                    channel=user_id,
                    text=f"{tentative_response}",
                    thread_ts=thread_slack_id
                )
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        append_string_to_file('preguntas_totales.txt', f"{fecha_actual}|{threads_slack[key]['pregunta']}|{tentative_response}|Bot")
        del threads_slack[key]
    else:
        tentative_response = re.sub('【.*?†source】', '', tentative_response) # Limpieza de las referencias de los archivos
        # Actualizar el diccionario threads_slack con la respuesta tentativa y marcarla como esperando aprobación.
        threads_slack[key]['tentative_response'] = tentative_response
        threads_slack[key]['waiting_for_approval'] = True
        threads_slack[key]['update_response']= False
        # Guardar el ID del thread de OpenAI en threads_openia.
        threads_openia[user_id] = {
            'thread_id': thread_openia.id
        }       
        
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