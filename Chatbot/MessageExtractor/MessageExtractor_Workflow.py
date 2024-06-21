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
if messages:
    Functions.process_and_store_messages(messages)  # Procesar y almacenar los mensajes
    # Guardar el timestamp del último mensaje procesado
    Functions.save_last_timestamp(messages[0]['ts'])

# Eliminar duplicados del archivo histórico
Functions.remove_duplicates()