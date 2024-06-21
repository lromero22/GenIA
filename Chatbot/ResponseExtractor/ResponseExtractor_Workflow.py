# Importación de la librerias necesarias
import requests
from datetime import datetime
import json
import os

# Importacion de las funciones estrictamente necesarias
import Functions

# Extraer y procesar los mensajes
last_timestamp = Functions.get_last_timestamp()  # Obtener el último timestamp procesado
messages = Functions.fetch_messages(oldest_timestamp=last_timestamp)  # Extraer mensajes desde el último timestamp
messages_w_checkmark = Functions.get_messages_with_checkmark(messages) # Extraccion de mensajes con checkmarks
if messages_w_checkmark:
    Functions.process_and_store_messages(messages_w_checkmark)  # Procesar y almacenar los mensajes
    # Guardar el timestamp del último mensaje procesado
    Functions.save_last_timestamp(messages_w_checkmark[0]['ts'])

# Eliminar duplicados del archivo histórico
Functions.remove_duplicates()