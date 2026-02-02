import streamlit as st
from groq import Groq
import json
from PyPDF2 import PdfReader

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Tutor Pro Bachillerato", page_icon="🎓", layout="wide")

# Gestión de la API Key (Prioriza Secrets de Streamlit Cloud)
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = "TU_LLAVE_DE_GROQ_AQUI"

client = Groq(api_key=api_key)

# --- 2. ESTADO DE LA SESIÓN ---
if "temas" not in st.session_state:
    st.session_state.temas = []
if "indice_actual" not in st.session_state:
    st.session_state.indice_actual = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "aprobado" not in st.session_state:
    st.session_state.aprobado = False


# --- 3. FUNCIONES ---
def extraer_texto(archivos_pdf):
    texto_completo = ""
    for pdf in archivos_pdf:
        lector = PdfReader(pdf)
        for pagina in lector.pages:
            texto_completo += pagina.extract_text() or ""
    return texto_completo


def generar_temario_ia(texto):
    prompt = f"""
    Eres un catedrático de Bachillerato experto en la asignatura. 
    Tu objetivo es transcribir y explicar TODO el contenido de los apuntes adjuntos.
    
    REGLAS ESTRICTAS:
    1. NO RESUMAS. Explica cada concepto detalladamente para que el alumno no tenga que volver a leer el PDF original.
    2. DIVISIÓN CLARA: Si hay 6 archivos o conceptos distintos, crea al menos un tema por cada uno. No los mezcles.
    3. FIDELIDAD: Si el PDF menciona nombres, fechas o datos específicos, DEBEN aparecer en la explicación.
    4. CLARIDAD: Reescribe el lenguaje "difícil" del PDF a uno que un alumno entienda perfectamente, pero sin perder el rigor.

    RESPONDE SOLO EN JSON:
    {{
      "temas": [
        {{
          "titulo": "Título específico del PDF",
          "explicacion": "Explicación completa, extensa y sin dejarse detalles...",
          "preguntas": ["...", "..."]
        }}
      ]
    }}
    Apuntes para procesar: {texto[:11000]}
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)["temas"]
    except Exception as e:
        st.error(f"Error IA: {e}")
        return []


def calificar(pregunta, respuesta, contexto):
    prompt = f"Califica esta respuesta de 0 a 10 basada en el texto. Responde JSON con 'nota', 'feedback' y 'olvidos'. Pregunta: {pregunta}. Respuesta: {respuesta}. Contexto: {contexto}"
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)


# --- 4. INTERFAZ (SIDEBAR) ---
with st.sidebar:
    st.header("📂 Apuntes")
    archivos = st.file_uploader("Sube tus PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Iniciar Tutoría") and archivos:
        with st.spinner("Procesando..."):
            st.session_state.temas = generar_temario_ia(extraer_texto(archivos))
            st.session_state.indice_actual = 0
            st.session_state.feedback = None
            st.rerun()

# --- 5. CUERPO PRINCIPAL ---
st.title("🎓 Tutor IA Bachillerato")

if st.session_state.temas:
    tema = st.session_state.temas[st.session_state.indice_actual]

    # Barra de progreso
    progreso = (st.session_state.indice_actual + 1) / len(st.session_state.temas)
    st.progress(progreso)
    st.write(f"**Tema {st.session_state.indice_actual + 1} de {len(st.session_state.temas)}**")

    # PESTAÑAS: Aquí está el cambio ingenioso
    tab_estudio, tab_examen = st.tabs(["📖 Estudiar", "📝 Examinarse"])

    with tab_estudio:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(tema['titulo'])
        with col2:
            if st.button("🆘 No entiendo nada"):
                with st.spinner("Simplificando..."):
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": f"Explica esto muy fácil: {tema['explicacion']}"}]
                    )
                    st.warning(res.choices[0].message.content)

        st.write(tema['explicacion'])

    with tab_examen:
        st.subheader("Cuestionario")
        st.info(f"1. {tema['preguntas'][0]}")
        st.info(f"2. {tema['preguntas'][1]}")

        resp_usuario = st.text_area("Tus respuestas:", key=f"area_{st.session_state.indice_actual}")

        if st.button("Enviar Examen"):
            with st.spinner("Corrigiendo..."):
                resultado = calificar(tema['preguntas'], resp_usuario, tema['explicacion'])
                st.session_state.feedback = resultado
                st.session_state.aprobado = float(resultado["nota"]) >= 6.0

        if st.session_state.feedback:
            fb = st.session_state.feedback
            st.divider()
            st.metric("Nota EBAU", f"{fb['nota']}/10")

            if st.session_state.aprobado:
                st.success(fb['feedback'])
                if st.session_state.indice_actual < len(st.session_state.temas) - 1:
                    if st.button("Siguiente Tema ➡️"):
                        st.session_state.indice_actual += 1
                        st.session_state.feedback = None
                        st.rerun()
                else:
                    st.balloons()
                    st.success("¡Curso completado!")
            else:
                st.error(f"Nota insuficiente (mínimo 6). {fb['feedback']}")
                st.info(f"Te faltó: {fb['olvidos']}")
else:
    st.info("Sube tus apuntes en la barra lateral para empezar.")