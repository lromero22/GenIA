def QandA(archivo, pregunta, respuesta):
    """
    Agrega una pregunta y su respuesta a un archivo de texto.
    
    :param archivo: str, nombre del archivo donde se guardarán las preguntas y respuestas.
    :param pregunta: str, la pregunta a agregar.
    :param respuesta: str, la respuesta a agregar.
    """
    with open(archivo, 'a', encoding = 'utf-8') as f:
        f.write(f"Pregunta: {pregunta}\n")
        f.write(f"Respuesta: {respuesta}\n")
        f.write("\n")  # Añade una línea en blanco para separar las entradas

# Ejemplo de uso
archivo = 'QA.txt'
pregunta = input("Introduce la pregunta: ") # Cambiar el input por la pregunta hecha por el usuario
respuesta = input("Introduce la respuesta: ") # Cambiar el input por la respuesta corregida/chequeada por el supervisor

QandA(archivo, pregunta, respuesta)
