import requests
from datetime import datetime
import json
import os
import schedule
import time

# Configurar el token y el ID del canal de Slack
token = "some_token"
channel_id = "some_channel"  # Reemplaza con el ID del canal correcto

# Configurar los encabezados de la solicitud
headers = {
    "Authorization": f"Bearer {token}"
}

# DEFINICION DE FUNCIONES
# Función para almacenar y leer el último timestamp
def get_last_timestamp(file_path="last_timestamp.json"):
    try:
        with open(file_path, 'r', encoding = 'utf-8') as f:
            data = json.load(f)
            return data.get('last_timestamp', None)
    except FileNotFoundError:
        return None

def save_last_timestamp(timestamp, file_path="last_timestamp.json"):
    with open(file_path, 'w', encoding = 'utf-8') as f:
        json.dump({'last_timestamp': timestamp}, f)

# Función para extraer mensajes del canal de Slack
def fetch_messages(oldest_timestamp=None, oldest = None, latest = None):
    url = f"https://slack.com/api/conversations.history?channel={channel_id}"

    if oldest_timestamp:
        url += f"&oldest={oldest_timestamp}"
    if oldest:
        oldest_ts = datetime.strptime(oldest, "%Y-%m-%d %H:%M:%S").timestamp()
        url += f"&oldest={oldest_ts}"
    if latest:
        latest_ts = datetime.strptime(latest, "%Y-%m-%d %H:%M:%S").timestamp()
        url += f"&latest={latest_ts}"

    response = requests.get(url, headers=headers)

    # Verificar si la solicitud fue exitosa
    if response.status_code != 200:
        print("Error al obtener mensajes:", response.status_code, response.text)
        return []

    data = response.json()

    # Verificar si la respuesta contiene 'messages'
    if not data.get('ok'):
        print("Error:", data.get('error'))
        return []

    return data["messages"]

# Función para obtener respuestas de un hilo
def fetch_thread_messages(thread_ts):
    url = f"https://slack.com/api/conversations.replies?channel={channel_id}&ts={thread_ts}"
    response = requests.get(url, headers=headers)

    # Verificar si la solicitud fue exitosa
    if response.status_code != 200:
        print("Error al obtener mensajes del hilo:", response.status_code, response.text)
        return []

    data = response.json()

    # Verificar si la respuesta contiene 'messages'
    if not data.get('ok'):
        print("Error:", data.get('error'))
        return []

    # Ignorar el primer mensaje ya que es el mensaje principal
    return data["messages"] # return data["messages"][1:]


# Función para obtener la información del usuario
def get_user_info(user_id):
    url = f"https://slack.com/api/users.info?user={user_id}"
    response = requests.get(url, headers=headers)

    # Verificar si la solicitud fue exitosa
    if response.status_code != 200:
        print(f"Error al obtener información del usuario {user_id}:", response.status_code, response.text)
        return None

    data = response.json()

    # Verificar si la respuesta contiene 'user'
    if not data.get('ok'):
        print(f"Error al obtener información del usuario {user_id}:", data.get('error'))
        return None

    return data["user"]

# Función para verificar si un mensaje es una pregunta
def is_question(message_text):
    return message_text.endswith('?') or any(word in message_text.lower() for word in ['qué', 'cuál', 'dónde', 'cuándo', 'por qué', 'cómo'])

# Función para verificar si un mensaje contiene archivos
def contains_files(message):
    return 'files' in message or 'attachments' in message

# Función para procesar y almacenar mensajes en un archivo histórico
def process_and_store_messages(messages, history_file="message_history.json"):
    user_cache = {}
    historical_data = []

    # Leer el archivo histórico si existe
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding = 'utf-8') as f:
            historical_data = json.load(f)

    # Procesar y almacenar los mensajes
    for message in messages:
        user_id = message.get('user')
        client_msg_id = message.get('client_msg_id')
        text = message.get('text')
        if text.strip() == '':
          continue  # Ignorar mensajes vacios
        timestamp = message.get('ts')

        # Convertir el timestamp a un formato legible
        dt_object = datetime.fromtimestamp(float(timestamp))
        formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')

        # Obtener información del usuario, utilizando el cache si ya se ha consultado
        if user_id not in user_cache:
            user_info = get_user_info(user_id)
            if user_info:
                user_cache[user_id] = user_info.get('real_name', 'Unknown User')
            else:
                user_cache[user_id] = 'Unknown User'

        user_name = user_cache[user_id]

        # Identificar tipo de mensaje
        message_type = "other"
        if is_question(text):
            message_type = "question"
        elif 'thread_ts' in message:
            message_type = "thread_start"
        elif contains_files(message):
            message_type = "files"
            # continue  # Ignorar mensajes con imágenes

        # Agregar el mensaje al archivo histórico
        historical_data.append({
            'user_id': user_id,
            'client_msg_id': client_msg_id,
            'user_name': user_name,
            'text': text,
            'timestamp': formatted_time,
            'type': message_type,
            'thread_start_msg_id': None
        })

        # Si el mensaje tiene un hilo, obtener los mensajes del hilo
        if 'thread_ts' in message:
            thread_messages = fetch_thread_messages(message['thread_ts'])
            thread_start_msg_id = thread_messages[0].get('client_msg_id')
            for thread_message in thread_messages[1:]:
                user_id = thread_message.get('user')
                client_msg_id = thread_message.get('client_msg_id')
                text = thread_message.get('text')
                if text.strip() == '':
                  continue # Ignorar mensajes vacios
                timestamp = thread_message.get('ts')

                # Convertir el timestamp a un formato legible
                dt_object = datetime.fromtimestamp(float(timestamp))
                formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')

                # Obtener información del usuario, utilizando el cache si ya se ha consultado
                if user_id not in user_cache:
                    user_info = get_user_info(user_id)
                    if user_info:
                        user_cache[user_id] = user_info.get('real_name', 'Unknown User')
                    else:
                        user_cache[user_id] = 'Unknown User'

                user_name = user_cache[user_id]

                # Identificar tipo de mensaje en el hilo
                message_type = "other"
                if is_question(text):
                    message_type = "question"
                elif contains_files(thread_message):
                    message_type = "files"
                    # continue  # Ignorar mensajes con imágenes
                else:
                    message_type = "response"

                # Agregar el mensaje del hilo al archivo histórico
                historical_data.append({
                    'user_id': user_id,
                    'client_msg_id': client_msg_id,
                    'user_name': user_name,
                    'text': text,
                    'timestamp': formatted_time,
                    'type': message_type,
                    'thread_start_msg_id': thread_start_msg_id
                })

    # Guardar el archivo histórico actualizado
    with open(history_file, 'w', encoding = 'utf-8') as f:
        json.dump(historical_data, f, indent=4)

# Eliminacion de mensajes duplicados
def remove_duplicates(history_file="message_history.json"):
    try:
        # Leer el archivo histórico
        with open(history_file, 'r', encoding = 'utf-8') as f:
            historical_data = json.load(f)
    except FileNotFoundError:
        print(f"Archivo {history_file} no encontrado.")
        return

    # Utilizar un conjunto para rastrear los mensajes únicos
    unique_messages = []
    seen_messages = set()

    for message in historical_data:
        message_tuple = (message['user_id'], message['client_msg_id'], message['user_name'], message['text'],
                         message['timestamp'], message['type'], message['thread_start_msg_id'])
        if message_tuple not in seen_messages:
            seen_messages.add(message_tuple)
            unique_messages.append(message)

    # Guardar el archivo histórico actualizado sin duplicados
    with open(history_file, 'w') as f:
        json.dump(unique_messages, f, indent=4)

    print(f"Se eliminaron duplicados. {len(historical_data) - len(unique_messages)} mensajes eliminados.")

# Función principal para ejecutar el proceso completo
def main():
    # Extraer y procesar los mensajes
    last_timestamp = get_last_timestamp()  # Obtener el último timestamp procesado
    messages = fetch_messages(oldest_timestamp=last_timestamp)  # Extraer mensajes desde el último timestamp
    if messages:
        process_and_store_messages(messages)  # Procesar y almacenar los mensajes
        # Guardar el timestamp del último mensaje procesado
        save_last_timestamp(messages[0]['ts'])
    # Eliminar duplicados del archivo histórico
    remove_duplicates()

# Configurar la tarea programada para ejecutarse al final de cada dia
schedule.every(1).minutes.do(main)

# Mantener el script en ejecución
while True:
    schedule.run_pending()
    time.sleep(10)