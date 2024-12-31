import streamlit as st
from openai import OpenAI
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler
import threading


load_dotenv()

# Configuración de la clave API de OpenAI
client = OpenAI(api_key=os.getenv('API_KEY'))

ESG_TRI_ASSISTANT_ID = os.getenv('ESG_TRI_ASSISTANT_ID')

# logo_path = os.path.join(os.getcwd(), "/assets/nfoque_advisory_services_logo.jpg")

# def crear_asssitant():
#     instructions = "Vas a recibir un archivo xlsx con la siguiente estructura de columnas:\n - Columna 1: Tipo\n - Columna 2: Bloque\n - Columna 3: Subbloque\n - Columna 4: Definición\n - Columna 5: Valor\n\n\
#         Recibirás un documento (generalmente en formato pdf) que contiene la información necesaria para completar la colunma 'Valor' de cada una de las filasde tu archivo xlsx. Tu tarea es **analizar exhaustivamente**\
#          el documento proporcionado y completar la columna 'Valor' de tu archivo xlsx con la información que encuentres en el documento.\n\n### Instrucciones\n1. **Lee con atención el documento que se te proporcione**\n\
#             - Analiza todo el contenido, tablas, anexos, notas al pie y cualquier otra sección que pueda contener la información relevante.\n\n\
#         2. **Para cada una de las filas del archivo xlsx:**\n\
#                 - Identifica la 'Definición' o el significado que se corresponde con el 'Tipo', 'Bloque' y 'Subbloque'.\n\
#                 - Busca en el documento la información específica que responda o complete esa 'Definición'. \n\
#                 - Si algún dato no se encuentra en el documento o no está disponible, debes indicar que **no hay información suficiente** (por ejemplo, escribiendo “No se encuentra información en el documento” o “Dato no disponible”).\n\
#                 - Rellena la columna 'Valor' **con la información encontrada** en el documento.\n\
#                     - Si la información está explícita, cópiala fielmente (o resume si es muy extensa).\n\
#                     - Si la información implica realizar un **cálculo o lectura interpretativa**, describe con claridad cómo obtuviste ese valor del documento.\n\
#                     - Si no encuentras la información, deja constancia de ello.\n\n\
#         3. **Output final** \n\
#             - Proporciona un archivo xlsx con todas sus columnas (Tipo, Bloque, Subbloque, Definición, Valor) y asegúrate de que cada fila tiene la columna 'Valor' correctamente cumplimentada según la información encontrada (o una nota si no la hay).\n\
#             - La **única columna que se debe modificar o completar** es la columna 'Valor'; las demás columnas deben conservarse tal cual fueron dadas en el Excel.\n\n\
#         4. **Estándares de calidad**\n\
#             - **No inventes información**: si algo no está en el PDF o no hay certeza, indícalo claramente.\n\
#             - **No omitas** ninguna de las filas. Cada fila debe tener alguna respuesta en la columna 'Valor'.\n\
#             - **Claridad y consistencia**: asegúrate de que los datos en la columna 'Valor' correspondan exclusivamente al contenido del documento."



#     assistant = client.beta.assistants.create(
#         name="ESG TRI Assistant",
#         instructions=instructions,
#         tools = [{"type": "code_interpreter", "type": "file_search"}],
#         model = "gpt-4o"
#         )

#     print(assistant.id)


def obtener_file(file_id):
    print("Descargando archivo...")
    output_path = './parciales/' + file_id + '.xlsx'
    api_response = client.files.with_raw_response.content(file_id)

    if api_response.status_code == 200:
        content = api_response.content
        with open(output_path, 'wb') as f:
            f.write(content)
        print('File downloaded successfully.')
    else:
        print("Error downloading file from assistant")

    return output_path[2:]


def query_assistant(assistant_id, excel_path, document_path, n_filas=10):
    response = {'Text': "", 'File': None}

    # Esto sustituirá a las instrucciones del assistant
    instructions = "Vas a recibir un archivo xlsx con la siguiente estructura de columnas:\n - Columna 1: Tipo\n - Columna 2: Bloque\n - Columna 3: Subbloque\n - Columna 4: Definición\n - Columna 5: Valor\n\n\
        Recibirás también un documento (generalmente en formato pdf) que contiene la información necesaria para completar la colunma 'Valor' de cada una de las filas del archivo xlsx. Tu tarea es **analizar exhaustivamente**\
         el documento proporcionado y completar la columna 'Valor' del archivo xlsx con la información que encuentres en el documento.\n\n### Instrucciones\n1. **Lee con atención el documento que se te proporcione**\n\
            - Analiza todo el contenido, tablas, anexos, notas al pie y cualquier otra sección que pueda contener la información relevante.\n\n\
        2. **Para cada una de las filas del archivo xlsx:**\n\
                - Identifica la 'Definición' o el significado que se corresponde con el 'Tipo', 'Bloque' y 'Subbloque'.\n\
                - Busca en el documento la información específica que responda o complete esa 'Definición'. \n\
                - Si algún dato no se encuentra en el documento o no está disponible, debes indicar que **no hay información suficiente** (por ejemplo, escribiendo “No se encuentra información en el documento” o “Dato no disponible”).\n\
                - Rellena la columna 'Valor' **con la información encontrada** en el documento.\n\
                    - Si la información está explícita, cópiala fielmente (o resume si es muy extensa).\n\
                    - Si la información implica realizar un **cálculo o lectura interpretativa**, describe con claridad cómo obtuviste ese valor del documento.\n\
                    - Si no encuentras la información, deja constancia de ello.\n\n\
        3. **Output final** \n\
            - Proporciona un archivo xlsx con todas sus columnas (Tipo, Bloque, Subbloque, Definición, Valor) y asegúrate de que cada fila tiene la columna 'Valor' correctamente cumplimentada según la información encontrada (o una nota si no la hay).\n\
            - La **única columna que se debe modificar o completar** es la columna 'Valor'; las demás columnas deben conservarse tal cual fueron dadas en el Excel.\n\n\
        4. **Estándares de calidad**\n\
            - **No inventes información**: si algo no está en el PDF o no hay certeza, indícalo claramente.\n\
            - **No omitas** ninguna de las filas. Cada fila debe tener alguna respuesta en la columna 'Valor'.\n\
            - **Claridad y consistencia**: asegúrate de que los datos en la columna 'Valor' correspondan exclusivamente al contenido del documento."


    print("Subiendo archivos al assistant...")
    try:
        file_excel = client.files.create(
            file=open(excel_path, 'rb'),
            purpose="assistants"
        )
        file_document = client.files.create(
            file=open(document_path, 'rb'),
            purpose="assistants"
        )
    except:
        print("Error al subir los archivos")
    

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": f"Por favor, completa las primeras {n_filas} archivo excel con la información del documento y devuélvemelo cuando esté completo. EL excel es el archivo con id {file_excel.id} y el documento con la información es el archivo con id {file_document.id}",
                "attachments": [
                    {
                        "file_id": file_excel.id,
                        "tools": [{"type": "code_interpreter"}]
                    },
                    {
                        "file_id": file_document.id,
                        "tools": [{"type": "file_search"}]
                    }
                ]
            }
        ]
    )
    print("Creating a run...")
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions=instructions,
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}, {"type": "file_search"}],
    )
    
   
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        
        # Separar archivo de texto
        for message in messages.data[0].content:
            if message.type == "text":
                response['Text'] += message.text.value
                
                if message.text.annotations:
                    if message.text.annotations[0].type == "file_path":
                        file_id = message.text.annotations[0].file_path.file_id
                        output_path = obtener_file(file_id)
                        response['File'] = output_path
    
    else:
        print(run.status)

    return response



# Estructura:    Parte: [Ruta, Número de filas]
input_parts = {
    'Part 1': ['./Inputs_TRI_divided/Inputs_TRI_part1.xlsx' ,30],
    'Part 2': ['./Inputs_TRI_divided/Inputs_TRI_part2.xlsx', 27],
    'Part 3': ['./Inputs_TRI_divided/Inputs_TRI_part3.xlsx', 34],
    'Part 4': ['./Inputs_TRI_divided/Inputs_TRI_part4.xlsx', 26],
    'Part 5': ['./Inputs_TRI_divided/Inputs_TRI_part5.xlsx', 21],
    'Part 6': ['./Inputs_TRI_divided/Inputs_TRI_part6.xlsx', 37],
}

document_path = './files/informe_telefonica.pdf'

# response = query_assistant(ESG_TRI_ASSISTANT_ID, input_parts['Part 6'][0], document_path, input_parts['Part 6'][1])
# print(response)


threads = {}

for part, inputs in input_parts.items():
    thread = threading.Thread(target=query_assistant, args=(ESG_TRI_ASSISTANT_ID, inputs[0], document_path, inputs[1]))
    threads[part] = thread
    thread.start()

for part in input_parts:
    threads[part].join()





