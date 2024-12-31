import streamlit as st
from openai import OpenAI
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler
import threading
import json
import time


load_dotenv()

# Configuración de la clave API de OpenAI
client = OpenAI(api_key=os.getenv('API_KEY'))

ESG_TRI_ASSISTANT_ID = os.getenv('ESG_TRI_ASSISTANT_ID')

# logo_path = os.path.join(os.getcwd(), "/assets/nfoque_advisory_services_logo.jpg")


def obtener_file(file_id, part_name):
    print("Descargando archivo...")
    output_path = './parciales/downloaded/' + part_name + '.json'
    api_response = client.files.with_raw_response.content(file_id)

    if api_response.status_code == 200:
        content = api_response.content
        with open(output_path, 'wb') as f:
            f.write(content)
        print('File downloaded successfully.')
    else:
        print("Error downloading file from assistant")

    return output_path[2:]


def query_assistant(assistant_id, excel_path, document_path, part_name):
    response = {'Text': "", 'File': None}

    # Esto sustituirá a las instrucciones del assistant
    instructions = "Vas a recibir un archivo json con la siguiente estructura de columnas:\n - Columna 1: Tipo\n - Columna 2: Bloque\n - Columna 3: Subbloque\n - Columna 4: Definición\n - Columna 5: Valor\n\n\
        Recibirás también un documento (generalmente en formato pdf) que contiene la información necesaria para completar la colunma 'Valor' de cada una de las filas del archivo json. Tu tarea es **analizar exhaustivamente**\
         el documento proporcionado y completar la columna 'Valor' del archivo json con la información que encuentres en el documento.\n\n### Instrucciones\n1. **Lee con atención el documento que se te proporcione**\n\
            - Analiza todo el contenido, tablas, anexos, notas al pie y cualquier otra sección que pueda contener la información relevante.\n\n\
        2. **Para cada una de las filas del archivo json:**\n\
                - Identifica la 'Definición' o el significado que se corresponde con el 'Tipo', 'Bloque' y 'Subbloque'.\n\
                - Busca en el documento la información específica que responda o complete esa 'Definición'. \n\
                - Si algún dato no se encuentra en el documento o no está disponible, debes indicar que **no hay información suficiente** (por ejemplo, escribiendo “No se encuentra información en el documento” o “Dato no disponible”).\n\
                - Rellena la columna 'Valor' **con la información encontrada** en el documento.\n\
                    - Si la información está explícita, cópiala fielmente (o resume si es muy extensa).\n\
                    - Si la información implica realizar un **cálculo o lectura interpretativa**, describe con claridad cómo obtuviste ese valor del documento.\n\
                    - Si no encuentras la información, deja constancia de ello.\n\n\
        3. **Output final** \n\
            - Proporciona un archivo json con todas sus columnas (Tipo, Bloque, Subbloque, Definición, Valor) y asegúrate de que cada fila tiene la columna 'Valor' correctamente cumplimentada según la información encontrada (o una nota si no la hay).\n\
            - La **única columna que se debe modificar o completar** es la columna 'Valor'; las demás columnas deben conservarse tal cual fueron dadas en el json original.\n\n\
        4. **Estándares de calidad**\n\
            - **No inventes información**: si algo no está en el PDF o no hay certeza, indícalo claramente.\n\
            - **No omitas** ninguna de las filas. Cada fila debe tener alguna respuesta en la columna 'Valor'.\n\
            - **Claridad y consistencia**: asegúrate de que los datos en la columna 'Valor' correspondan exclusivamente al contenido del documento."

    max_retries = 3  # Número máximo de intentos

    for _ in range(max_retries):
        print("Subiendo archivos al assistant...", threading.current_thread().name, part_name)
        try:
            file_excel = client.files.create(
                file=open(excel_path, 'rb'),
                purpose="assistants"
            )
            file_document = client.files.create(
                file=open(document_path, 'rb'),
                purpose="assistants"
            )
        
            print("Creating a thread...", threading.current_thread().name, part_name)
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        # "content": f"Por favor, completa las primeras {n_filas} archivo excel con la información del documento y devuélvemelo cuando esté completo. EL excel es el archivo con id {file_excel.id} y el documento con la información es el archivo con id {file_document.id}",
                        "content": f"""
                            Aquí tienes dos archivos:
                            1) Un **JSON** (id {file_excel.id}) que contiene la tabla de datos que quiero que completes. Cada fila tiene las columnas: Tipo, Bloque, Subbloque, Definición y Valor. Solamente debes rellenar la columna 'Valor'.
                            2) Un **PDF** (id {file_document.id}) que contiene la información para completar dicha columna.

                            ### Tu tarea
                            1. Usa 'code_interpreter' para leer el archivo JSON (id {file_excel.id}).
                            2. Usa 'file_search' para analizar el PDF (id {file_document.id}).
                            3. Para cada fila del JSON, rellena la columna 'Valor' con los datos que encuentres en el PDF. Si no hay información, escribe "No se encuentra información en el documento".
                            4. Devuélveme un **único archivo JSON** (con la misma estructura) que contenga las columnas originales (Tipo, Bloque, Subbloque, Definición, Valor) y muestre la columna 'Valor' completa.

                            ### Importante
                            - No inventes información: si no aparece en el PDF, pon "No se encuentra información en el documento".
                            - No alteres las demás columnas.
                            - Devuelve el resultado **exclusivamente** como un archivo JSON (sin texto extra).

                            ¡Gracias!
                            """,
                        "attachments": [
                            {
                                "file_id": file_excel.id,
                                "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]
                            },
                            {
                                "file_id": file_document.id,
                                "tools": [{"type": "file_search"}]
                            }
                        ]
                    }
                ]
            )

            print("Creating a run...", threading.current_thread().name, part_name)
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
                print("Extrayendo mensajes...", threading.current_thread().name, part_name)
                # Separar archivo de texto
                for message in messages.data[0].content:
                    if message.type == "text":
                        response['Text'] += message.text.value
                        
                        if message.text.annotations:
                            if message.text.annotations[0].type == "file_path":
                                file_id = message.text.annotations[0].file_path.file_id
                                output_path = obtener_file(file_id, part_name)
                                response['File'] = output_path
                
                
                if response['File'] is None:
                    print("No se ha generado ningún archivo", threading.current_thread().name, part_name)
                
                return response

            else:
                print(run.status, threading.current_thread().name, part_name)
                print("Error en la ejecución del assistant. Reintentando...", threading.current_thread().name, part_name)

        except Exception as e:
                print(f"Error en la conexión con el assistant. {e}. Reintentando...", threading.current_thread().name, part_name)
                time.sleep(1)
    
    print("Error en la ejecución o conexión del assistant después de varios intentos", threading.current_thread().name, part_name)
    return response



start = time.time()

document_path = './files/informe_telefonica.pdf'
original_excel_path = './files/Inputs_TRI.xlsx'

data = pd.read_excel(original_excel_path)
df = pd.DataFrame(data)

part_length = 5
last_part_length = len(df)%part_length
num_parts = len(df)//part_length +1


original_excel_path = './files/Inputs_TRI.xlsx'
data = pd.read_excel(original_excel_path)
df = pd.DataFrame(data)

input_parts = {}

for i in range(num_parts):
    start = i*part_length
    end = (i+1)*part_length
    part = df.iloc[start:end]
    path = f'./parciales/inputs/part_{i}.json'
    # part.to_json(path)
    part.to_json(path, orient="records", force_ascii=False)
    
    input_parts[f'Part_{i}'] = path


threads = {}

for part, path in input_parts.items():
    thread = threading.Thread(target=query_assistant, args=(ESG_TRI_ASSISTANT_ID, path, document_path, part))
    threads[part] = thread
    thread.start()

for part in input_parts:
    threads[part].join()


# Combine json parts into an excel file
all_rows = []
dir = './parciales/downloaded'  # Directorio donde se descargan los archivos json con las respuestas dadas por el assistant

print("Combinando archivos...")
for name in os.listdir(dir):
    # Open file
    with open(os.path.join(dir, name), encoding='utf-8') as f:
        try:
            data = json.load(f)

            if isinstance(data, list):
                all_rows.extend(data)
            else:
                all_rows.append(data)

        except json.JSONDecodeError:
            # Si falla intentamos parsear linea por linea
            content = f.read().strip().splitlines()
            for line in content:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    all_rows.append(obj)

output_df = pd.DataFrame(all_rows)
output_df.to_excel('./Outputs_TRI.xlsx', index=False)


end = time.time()
print("Total Time: ", end-start)

