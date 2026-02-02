import streamlit as st
from groq import Groq
import json
from PyPDF2 import PdfReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Tutor Pro Bachillerato", page_icon="🎓", layout="wide")

# Intentamos sacar la llave de los secretos (para la web) o de una variable local
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    # Si lo pruebas en local y no tienes secretos, puedes pegarla aquí temporalmente
    api_key = "TU_LLAVE_DE_GROQ_AQUI"

client = Groq(api_key=api_key)

# --- 2. INICIALIZAR EL "CEREBRO" (SESSION STATE) ---
if "temas" not in st.session_state:
    st.session_state.temas = []
if "indice_actual" not in st.session_state:
    st.session_state.indice_actual = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "aprobado" not in st.session_state:
    st.session_state.aprobado = False


# --- 3. FUNCIONES DE AYUDA ---
def extraer_texto(archivos_pdf):
    texto_completo = ""
    for pdf in archivos_pdf:
        lector = PdfReader(pdf)
        for pagina in lector.pages:
            texto_completo += pagina.extract_text() or ""
    return texto_completo


def generar_temario_ia(texto):
    prompt = f"""
    Eres un profesor de Bachillerato español. Divide estos apuntes en temas coherentes.
    Para cada tema, crea una explicación magistral y 2 preguntas de examen.
    RESPONDE EXCLUSIVAMENTE EN JSON con esta estructura:
    {{
      "temas": [
        {{
          "titulo": "Nombre del tema",
          "explicacion": "Texto largo y detallado...",
          "preguntas": ["Pregunta 1", "Pregunta 2"]
        }}
      ]
    }}
    Apuntes: {texto[:8000]}
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        data = json.loads(chat_completion.choices[0].message.content)
        return data["temas"]
    except Exception as e:
        st.error(f"Error con la IA: {e}")
        return []


def calificar_respuesta(pregunta, respuesta_alumno, contexto):
    prompt = f"""
    Actúa como corrector de Selectividad. Califica la respuesta sobre 10 basándote en los apuntes.
    Pregunta: {pregunta}
    Respuesta del alumno: {respuesta_alumno}
    Apuntes originales: {contexto}

    Responde en JSON con: "nota" (número), "feedback" (puntos fuertes y debilidades) y "olvidos" (conceptos clave que faltan).
    """
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )
    return json.loads(chat_completion.choices[0].message.content)


# --- 4. INTERFAZ DE USUARIO ---
st.title("🎓 Tutor IA de Bachillerato")
st.markdown("Sube tus apuntes y estudia tema a tema. ¡Solo pasarás si demuestras que sabes!")

# Sidebar para subir archivos
with st.sidebar:
    st.header("📂 Tus Apuntes")
    archivos = st.file_uploader("Sube uno o varios PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Empezar a Estudiar") and archivos:
        with st.spinner("La IA está leyendo tus apuntes..."):
            texto_extraido = extraer_texto(archivos)
            st.session_state.temas = generar_temario_ia(texto_extraido)
            st.session_state.indice_actual = 0
            st.session_state.feedback = None
            st.session_state.aprobado = False
            st.rerun()

# --- 5. LÓGICA DE ESTUDIO ---
if st.session_state.temas:
    tema = st.session_state.temas[st.session_state.indice_actual]

    # Barra de progreso
    total = len(st.session_state.temas)
    progreso = (st.session_state.indice_actual + 1) / total
    st.progress(progreso)
    st.write(f"**Progreso: Tema {st.session_state.indice_actual + 1} de {total}**")

    # Mostrar contenido
    st.subheader(f"Tema: {tema['titulo']}")
    with st.expander("📖 Leer Explicación", expanded=True):
        st.write(tema['explicacion'])

    # Sección de evaluación
    st.markdown("---")
    st.write("### 📝 Examen rápido")
    st.write(f"**Pregunta 1:** {tema['preguntas'][0]}")
    st.write(f"**Pregunta 2:** {tema['preguntas'][1]}")

    respuesta = st.text_area("Escribe aquí tus respuestas combinadas:",
                             placeholder="Desarrolla tus respuestas lo mejor posible...")

    if st.button("📤 Enviar para Corregir"):
        with st.spinner("Corrigiendo..."):
            resultado = calificar_respuesta(tema['preguntas'], respuesta, tema['explicacion'])
            st.session_state.feedback = resultado
            st.session_state.aprobado = float(resultado["nota"]) >= 6.0

    # Mostrar feedback si existe
    if st.session_state.feedback:
        fb = st.session_state.feedback
        st.markdown(f"### Nota: {fb['nota']}/10")

        if st.session_state.aprobado:
            st.success(f"**¡Buen trabajo!** {fb['feedback']}")
            st.info(f"**Lo que podrías mejorar:** {fb['olvidos']}")

            if st.session_state.indice_actual < total - 1:
                if st.button("Siguiente Tema ➡️"):
                    st.session_state.indice_actual += 1
                    st.session_state.feedback = None
                    st.session_state.aprobado = False
                    st.rerun()
            else:
                st.balloons()
                st.success("¡Has terminado todos los apuntes! Estás listo para el examen.")
        else:
            st.error(f"**Necesitas repasar.** Nota mínima para pasar: 6.0")
            st.warning(f"**Feedback:** {fb['feedback']}")
            st.info(f"**Te ha faltado decir:** {fb['olvidos']}")

else:
    st.info("Sube tus archivos PDF en la barra lateral para generar tu plan de estudio personalizado.")