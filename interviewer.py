# interviewer.py

import json
import boto3
import logging
from config import AWS_MODEL_ID, AWS_BEDROCK_VERSION

# Configuración del logging (opcional, si ya lo configuras en otro lugar, podrías omitirlo aquí)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Interviewer:
    """
    Clase encargada de interactuar con la API de Amazon Bedrock para generar preguntas
    y evaluar respuestas durante la entrevista.
    """
    def __init__(self):
        try:
            self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        except Exception as e:
            logging.error(f"Error inicializando el cliente de boto3: {e}")
            raise

    def generate_question(self, cv_content, position, conversation_history):
        """
        Genera una pregunta basándose en el contenido del CV, el puesto y el historial de la conversación.
        """
        body = {
            "anthropic_version": AWS_BEDROCK_VERSION,
            "max_tokens": 5000,
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Actúa como un entrevistador profesional de recursos humanos para el puesto de '{position}'.
CV: {cv_content}
Historial: {conversation_history}
Formula preguntas específicas y naturales que permitan evaluar la idoneidad del candidato.
                    """
                }
            ]
        }
        return self._invoke_model(body)

    def evaluate_response(self, question, user_response):
        """
        Evalúa la respuesta del usuario basado en la pregunta realizada.
        """
        body = {
            "anthropic_version": AWS_BEDROCK_VERSION,
            "max_tokens": 3000,
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Evalúa la siguiente respuesta:
Pregunta: {question}
Respuesta: {user_response}
Proporciona una puntuación del 1 al 10 y una justificación detallada.
                    """
                }
            ]
        }
        return self._invoke_model(body)

    def _invoke_model(self, body):
        """
        Método privado que se encarga de invocar el modelo de Bedrock y procesar la respuesta.
        """
        try:
            response = self.client.invoke_model(
                modelId=AWS_MODEL_ID,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            response_body = json.loads(response['body'].read().decode('utf-8'))
            content = response_body.get('content', [])
            if isinstance(content, list):
                return " ".join(item.get("text", "") for item in content).strip()
            return content.strip()
        except Exception as e:
            logging.error(f"Error al invocar el modelo: {e}")
            return f"Error: {e}"
