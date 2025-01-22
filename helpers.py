# helpers.py

import logging
import time
import requests
import urllib.parse
from PyPDF2 import PdfReader
from fpdf import FPDF
from textblob import TextBlob
from config import PDF_OUTPUT_PATH

def get_countries_data():
    """
    Obtiene la lista de países y sus ciudades desde la API de countriesnow.space.
    Se reduce el tiempo de espera entre intentos para acelerar el proceso.
    """
    url = "https://countriesnow.space/api/v0.1/countries"
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if not data.get("error", True):
                return data.get("data", [])
            else:
                logging.error("Error en la respuesta de la API.")
        except Exception as e:
            logging.error(f"Intento {attempt + 1} - Error al obtener los datos: {e}")
        time.sleep(0.2)
    return []

def upload_and_parse_cv(uploaded_file):
    """
    Extrae el texto de un archivo PDF que representa el CV.
    """
    try:
        pdf_reader = PdfReader(uploaded_file)
        content = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                content += text
        return content.strip()
    except Exception as e:
        logging.error(f"Error al leer el PDF: {e}")
        return ""

def export_to_pdf(conversation_history):
    """
    Exporta el historial completo de la entrevista a un archivo PDF.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, conversation_history)
        pdf_file = PDF_OUTPUT_PATH
        pdf.output(pdf_file)
        return pdf_file
    except Exception as e:
        logging.error(f"Error exportando a PDF: {e}")
        return None

def sentiment_analysis(text):
    """
    Realiza un análisis de sentimiento simple usando TextBlob.
    """
    try:
        analysis = TextBlob(text)
        return analysis.sentiment  # Objeto con polarity y subjectivity
    except Exception as e:
        logging.error(f"Error realizando análisis de sentimiento: {e}")
        return None

def get_job_recommendations(position, location):
    """
    Ejemplo de función para obtener sugerencias personalizadas.
    """
    position_query = urllib.parse.quote(position)
    location_query = urllib.parse.quote(location)

    recommendations = [
        {
            "title": f"Empleo similar 1 para {position} en {location}",
            "url": f"https://www.linkedin.com/jobs/search?keywords={position_query}&location={location_query}"
        },
        {
            "title": f"Empleo similar 2 para {position} en {location}",
            "url": f"https://www.indeed.com/jobs?q={position_query}&l={location_query}"
        },
        {
            "title": f"Empleo similar 3 para {position} en {location}",
            "url": f"https://www.google.com/search?q=jobs+{position_query}+in+{location_query}"
        },
    ]
    return recommendations

def load_lottieurl(url: str):
    """
    Carga una animación Lottie desde una URL.
    """
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        logging.error(f"Error cargando Lottie: {e}")
        return None

def generate_final_summary(conversation_history):
    """
    Genera un resumen final a partir del historial de la conversación.
    """
    summary = "Resumen de la entrevista:\n"
    summary += conversation_history
    summary += "\nGracias por participar en la entrevista virtual."
    return summary
