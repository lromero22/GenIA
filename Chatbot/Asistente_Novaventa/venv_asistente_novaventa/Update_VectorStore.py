# Conexion a la API de OpenAI
from openai import OpenAI
client = OpenAI(api_key = "some_openai_api_key")

# Recuperacion de todos los archivos cargado en la API
Files = client.files.list()
for file in Files:
    if file.filename == "correcciones_supervisor.txt":
        old_file_id = file.id # Obtencion del ID del archivo con las correcciones del supervisor que va a ser borrado (antiguo)
        break

# ID del vector store existente
vector_store_id = "some_vector_store_id"

# Eliminacion del archivo del vector store
try:
    delete_response = client.beta.vector_stores.files.delete(
        vector_store_id = vector_store_id,
        file_id = old_file_id
    )
except Exception:
    print("File already removed from the Vector Store")

# Eliminacion del archivo de la API de OpenAI
try:
    delete_file = client.files.delete(file_id = old_file_id)
except Exception:
    print("File already removed from the OpenAI API")

# Subir el archivo nuevo a la API de OpenAI
file = client.files.create(
    file = open("correcciones_supervisor.txt", "rb"),
    purpose = 'fine-tune'
)

# Nuevo ID del archivo con las correciones del supervisor (nuevo)
new_file_id = file.id

# Agregar el archivo al vector store
# Crear el vector_store_file
vector_store_file_response = client.beta.vector_stores.files.create(
    vector_store_id = vector_store_id,
    file_id = new_file_id
)