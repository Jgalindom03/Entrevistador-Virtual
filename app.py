# app.py

import logging
import urllib.parse
import requests
import time
import streamlit as st
import plotly.express as px
from streamlit_lottie import st_lottie
from interviewer import Interviewer
from helpers import (
    get_countries_data,
    upload_and_parse_cv,
    sentiment_analysis,
    load_lottieurl,
    generate_final_summary
)
import io
from fpdf import FPDF

# Configuración del logging (opcional si ya lo configuras globalmente)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==============================
# ESTILOS Y ASPECTO CORPORATIVO
# ==============================
st.markdown(
    """
    <style>
    /* Estilo general para la página */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f5f7fa;
        color: #333;
    }
    /* Contenedor principal */
    .main .block-container {
        padding: 2rem 2rem;
        max-width: 1200px;
        background-color: #fff;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    }
    /* Sidebar */
    .css-1d391kg {
        background-color: #e8eff5;
    }
    /* Encabezado */
    .header {
        text-align: center;
        margin-bottom: 2rem;
    }
    /* Título principal */
    .header h1 {
        font-size: 2.5rem;
        color: #0a3d62;
    }
    /* Footer */
    .footer {
        text-align: center;
        font-size: 0.8rem;
        color: #888;
        margin-top: 2rem;
    }
    /* Botones personalizados */
    .stButton>button {
        background-color: #0a3d62;
        color: #fff;
        border-radius: 5px;
        border: none;
        height: 40px;
        width: 150px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #075a82;
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True
)

# ==============================
# Función para exportar el PDF en memoria
# ==============================

def export_to_pdf_in_memory(content: str) -> io.BytesIO:
    """Genera un PDF en memoria a partir de texto plano."""
    # 1. Reemplazar caracteres conflictivos (comillas, guiones largos, etc.)
    #   por sus equivalentes ASCII.
    content_cleaned = (content
                       .replace("“", '"')
                       .replace("”", '"')
                       .replace("’", "'")
                       .replace("‘", "'")
                       .replace("–", "-")
                       .replace("—", "-")
                       .replace("…", "..."))

    # 2. Crear objeto FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content_cleaned)

    # 3. Generar string del PDF en memoria
    pdf_str = pdf.output(dest='S')  # Dependiendo de la versión, puede devolver str o bytes

    # 4. Asegurarnos de que 'pdf_str' sea bytes
    if isinstance(pdf_str, str):
        # encode() a latin-1 ignorando caracteres no representables
        pdf_str = pdf_str.encode('latin-1', 'ignore')

    # 5. Crear buffer BytesIO y retornarlo
    pdf_buffer = io.BytesIO(pdf_str)
    pdf_buffer.seek(0)
    return pdf_buffer
# ==============================
# MAIN APP
# ==============================
def main():
    # Encabezado profesional con animación Lottie
    st.markdown("<div class='header'><h1>Entrevistador Virtual</h1><p>Soluciones de Inteligencia Artificial para potenciar tu carrera</p></div>", unsafe_allow_html=True)
    
    # Animación Lottie
    lottie_animation = load_lottieurl("https://assets1.lottiefiles.com/packages/lf20_jcikwtux.json")
    if lottie_animation:
        st_lottie(lottie_animation, height=150, key="initial")

    st.write("Sube tu CV y especifica el puesto al que deseas postular. El sistema generará preguntas de entrevista y evaluará tus respuestas, brindándote un análisis profundo y recomendaciones.")

    # --------------------------
    # Inicialización de variables en session_state
    # --------------------------
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = ""
    if "cv_text" not in st.session_state:
        st.session_state.cv_text = ""
    if "position" not in st.session_state:
        st.session_state.position = ""
    if "modalidad" not in st.session_state:
        st.session_state.modalidad = ""
    if "ubicacion" not in st.session_state:
        st.session_state.ubicacion = ""
    if "num_questions" not in st.session_state:
        st.session_state.num_questions = 0
    if "interview_finished" not in st.session_state:
        st.session_state.interview_finished = False
    if "last_question" not in st.session_state:
        st.session_state.last_question = ""
    if "polarity_list" not in st.session_state:
        st.session_state.polarity_list = []
    if "final_summary" not in st.session_state:
        st.session_state.final_summary = ""
    if "avg_polarity" not in st.session_state:
        st.session_state.avg_polarity = 0.0
    if "final_summary_generated" not in st.session_state:
        st.session_state.final_summary_generated = False
    if "evaluations" not in st.session_state:
        st.session_state.evaluations = []  # Se almacena la evaluación de cada respuesta

    # Barra de progreso
    progress = st.progress(0)

    # --------------------------
    # Inicialización del entrevistador
    # --------------------------
    interviewer = Interviewer()

    # --------------------------
    # Subida del CV y configuración inicial
    # --------------------------
    if not st.session_state.cv_text or not st.session_state.position:
        uploaded_file = st.file_uploader("Sube tu CV en formato PDF", type=["pdf"])
        position = st.text_input("Ingresa el puesto al que deseas postular")
        modalidad = st.radio("Selecciona la modalidad de trabajo:", ("Remoto", "Presencial", "Ambos"))
        
        st.markdown("### Selecciona la ubicación usando la API")
        countries_data = get_countries_data()
        if not countries_data:
            st.error("No se pudieron cargar los datos de países y ciudades.")
        else:
            list_countries = sorted([country["country"] for country in countries_data])
            selected_countries = st.multiselect("Selecciona uno o varios países:", list_countries)
            ubicacion = ""
            if selected_countries:
                ubicacion_parts = []
                for country in selected_countries:
                    country_info = next((item for item in countries_data if item["country"] == country), None)
                    if country_info:
                        opciones_ciudades = ["Todos"] + sorted(country_info["cities"])
                        selected_cities = st.multiselect(f"Selecciona la(s) ciudad(es) para {country}:", opciones_ciudades, default=["Todos"])
                        if "Todos" in selected_cities or not selected_cities:
                            ubicacion_parts.append(country)
                        else:
                            ubicacion_parts.append(", ".join(selected_cities) + ", " + country)
                ubicacion = " | ".join(ubicacion_parts)
            else:
                st.error("Por favor, selecciona al menos un país.")
        
        if st.button("Iniciar entrevista"):
            if uploaded_file is None:
                st.error("Por favor, sube tu CV en formato PDF.")
                return
            if position.strip() == "":
                st.error("Por favor, ingresa el puesto al que deseas postular.")
                return
            with st.spinner("Procesando tu CV..."):
                cv_content = upload_and_parse_cv(uploaded_file)
            if cv_content == "":
                st.error("No se pudo extraer texto del CV. Revisa el formato del archivo.")
                return
            st.session_state.cv_text = cv_content
            st.session_state.position = position
            st.session_state.modalidad = modalidad
            st.session_state.ubicacion = ubicacion

            # Inicia el historial de la entrevista
            st.session_state.conversation_history = f"Inicio de la entrevista para el puesto '{position}' - Modalidad: {modalidad}"
            if ubicacion:
                st.session_state.conversation_history += f", Ubicación: {ubicacion}.\n"
            else:
                st.session_state.conversation_history += ".\n"
            st.success("CV cargado y entrevista iniciada. ¡Comencemos!")
    
    # --------------------------
    # Desarrollo de la entrevista
    # --------------------------
    if st.session_state.cv_text and st.session_state.position and not st.session_state.interview_finished:
        st.subheader("Entrevista en Curso")

        # Botón para generar nueva pregunta
        if st.button("Nueva pregunta"):
            question = interviewer.generate_question(
                st.session_state.cv_text,
                st.session_state.position,
                st.session_state.conversation_history
            )
            st.session_state.last_question = question
            st.session_state.conversation_history += f"Entrevistador: {question}\n"
            st.session_state.num_questions += 1

            # Actualizamos la barra de progreso (suponiendo 10 preguntas como tope)
            total_questions = 10
            progress_value = min(st.session_state.num_questions / total_questions, 1.0)
            progress.progress(progress_value)

            # Verificar si la pregunta indica que la entrevista finalizó
            if "finalizar la entrevista" in question.lower() or "terminado" in question.lower():
                st.session_state.interview_finished = True
                st.session_state.final_summary_generated = True
                final_summary = generate_final_summary(st.session_state.conversation_history)
                avg_polarity = (sum(st.session_state.polarity_list) / len(st.session_state.polarity_list)
                                if st.session_state.polarity_list else 0.0)
                st.session_state.final_summary = final_summary
                st.session_state.avg_polarity = avg_polarity
                st.session_state.conversation_history += "\n=== Resumen Final de la Entrevista ===\n"
                st.session_state.conversation_history += final_summary
                st.session_state.conversation_history += f"\nPromedio de Polaridad (Tono Global): {avg_polarity:.2f}\n"

        # Mostrar la última pregunta y el área de respuesta
        if st.session_state.last_question:
            st.markdown(f"**Entrevistador:** {st.session_state.last_question}")
            user_response = st.text_area("Tu respuesta (escribe aquí y presiona Enter cuando termines):", 
                                         key=f"response_{st.session_state.num_questions}", height=150)
            
            # Botón para registrar la respuesta
            if st.button("Registrar respuesta", key=f"btn_response_{st.session_state.num_questions}"):
                if user_response:
                    st.session_state.conversation_history += f"Usuario: {user_response}\n"
                    with st.spinner("Evaluando respuesta..."):
                        evaluation = interviewer.evaluate_response(st.session_state.last_question, user_response)
                    # Se añade la evaluación al historial de evaluaciones
                    st.session_state.evaluations.append(evaluation)
                    st.markdown(f"**Evaluación:** {evaluation}")
                    sentiment = sentiment_analysis(user_response)
                    if sentiment:
                        st.write(f"**Análisis de Sentimiento:** Polaridad = {sentiment.polarity:.2f}, Subjetividad = {sentiment.subjectivity:.2f}")
                        st.session_state.polarity_list.append(sentiment.polarity)
                    st.success("Respuesta registrada. Genera una nueva pregunta para continuar la entrevista.")
                else:
                    st.error("Por favor, escribe tu respuesta antes de registrarla.")

        # Botón para finalizar la entrevista (en caso de que el usuario lo decida manualmente)
        if not st.session_state.final_summary_generated:
            if st.button("Finalizar entrevista"):
                st.session_state.interview_finished = True
                st.session_state.final_summary_generated = True
                final_summary = generate_final_summary(st.session_state.conversation_history)
                avg_polarity = (sum(st.session_state.polarity_list) / len(st.session_state.polarity_list)
                                if st.session_state.polarity_list else 0.0)
                st.session_state.final_summary = final_summary
                st.session_state.avg_polarity = avg_polarity
                st.session_state.conversation_history += "\n=== Resumen Final de la Entrevista ===\n"
                st.session_state.conversation_history += final_summary
                st.session_state.conversation_history += f"\nPromedio de Polaridad (Tono Global): {avg_polarity:.2f}\n"
    
    # --------------------------
    # Mostrar resumen final junto con la evaluación, similar al historial
    # --------------------------
    if st.session_state.interview_finished and st.session_state.final_summary_generated:
        st.subheader("Resumen Final de la Entrevista")
        st.write(st.session_state.final_summary)
        st.write(f"**Promedio de Polaridad de la Conversación:** {st.session_state.avg_polarity:.2f}")
        
        # Mostrar las evaluaciones registradas para cada respuesta
        st.markdown("### Evaluación de las Respuestas")
        if st.session_state.evaluations:
            for idx, eval_text in enumerate(st.session_state.evaluations, start=1):
                st.markdown(f"**Evaluación de la Respuesta {idx}:** {eval_text}")
        else:
            st.info("No se registraron evaluaciones.")
        
        st.success("Entrevista finalizada y resumen generado. ¡Gracias por participar!")
    
    # --------------------------
    # Gráfico de análisis de polaridad (si hay datos)
    # --------------------------
    if st.session_state.polarity_list:
        data = {"Pregunta": list(range(1, len(st.session_state.polarity_list) + 1)),
                "Polaridad": st.session_state.polarity_list}
        fig = px.bar(data, x="Pregunta", y="Polaridad", title="Análisis de Polaridad de Respuestas")
        st.plotly_chart(fig)

    # --------------------------
    # Panel lateral: historial y exportar PDF
    # --------------------------
    st.sidebar.title("Historial de la entrevista")
    st.sidebar.text_area("Historial", st.session_state.conversation_history, height=300)

    # Exportar PDF en memoria
    if st.sidebar.button("Exportar a PDF"):
        pdf_buffer = export_to_pdf_in_memory(st.session_state.conversation_history)
        st.sidebar.download_button(
            label="Descargar PDF",
            data=pdf_buffer,
            file_name="entrevista_resultado.pdf",
            mime="application/pdf"
        )

    # --------------------------
    # Búsqueda de empleos en plataformas externas
    # --------------------------
    st.sidebar.markdown("## Buscar empleos similares en plataformas externas")
    if st.session_state.position:
        position_query = urllib.parse.quote(st.session_state.position)
        location_query = urllib.parse.quote(st.session_state.ubicacion) if st.session_state.ubicacion else ""
        linkedin_url = f"https://www.linkedin.com/jobs/search?keywords={position_query}"
        indeed_url = f"https://www.indeed.com/jobs?q={position_query}"
        if location_query:
            linkedin_url += f"&location={location_query}"
            indeed_url += f"&l={location_query}"
        st.sidebar.markdown(f"[Buscar en LinkedIn]({linkedin_url})", unsafe_allow_html=True)
        st.sidebar.markdown(f"[Buscar en Indeed]({indeed_url})", unsafe_allow_html=True)
    
    st.sidebar.markdown("<div class='footer'>© 2025 Javier Galindo Martínez - Todos los derechos reservados</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
