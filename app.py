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
    for idx, pdf in enumerate(archivos_pdf):
        lector = PdfReader(pdf)
        # Marcador para que la IA sepa que cambia de archivo
        texto_completo += f"\n\n--- INICIO DEL DOCUMENTO {idx+1}: {pdf.name} ---\n"
        for pagina in lector.pages:
            texto_completo += pagina.extract_text() or ""
    return texto_completo


def generar_temario_ia(texto):
    # Subimos a 18,000 caracteres. Si Groq da error, baja a 15,000.
    prompt = f"""
    Eres un Tutor de Excelencia para 2º de Bachillerato. Tu misión es generar apuntes que sustituyan por completo a los originales por su alto nivel de detalle.

    REGLAS DE ORO PARA LA EXPLICACIÓN:
    1. EXHAUSTIVIDAD TOTAL: No resumas. Si el PDF dice 10 cosas, tú explicas 10 cosas con todo su detalle.
    2. ESTRUCTURA DE CADA TEMA: La explicación debe tener al menos 4 párrafos largos. Usa conectores lógicos, fechas, nombres propios y datos técnicos del PDF.
    3. CERO OMISIONES: Está prohibido decir "en resumen", "etcétera" o "entre otros". Escribe todo el contenido.
    4. CLARIDAD MAGISTRAL: Reescribe lo "imposible de entender" de forma que un alumno lo comprenda a la primera, pero manteniendo el vocabulario técnico necesario para el examen.
    5. UN TEMA POR PDF: He subido varios archivos. Crea una entrada en el JSON para cada uno de ellos obligatoriamente.

    FORMATO DE SALIDA (JSON ESTRICTO):
    {{
      "temas": [
        {{
          "titulo": "Título muy específico basado en el nombre del archivo",
          "explicacion": "Escribe aquí una lección magistral EXTENSA (mínimo 500 palabras por tema). Incluye antecedentes, desarrollo y consecuencias. No te dejes nada del contenido original.",
          "preguntas": ["Pregunta de desarrollo 1", "Pregunta de relación 2"]
        }}
      ]
    }}

    CONTENIDO DE LOS APUNTES:
    {texto[:18000]}
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",  # Este modelo es el que mejor sigue instrucciones largas
            temperature=0.3,  # Bajamos la temperatura para que sea más fiel al texto y menos creativo
            response_format={"type": "json_object"}
        )
        data = json.loads(chat_completion.choices[0].message.content)
        return data["temas"]
    except Exception as e:
        st.error(f"Error con la IA: {e}")
        return []


def calificar(pregunta, respuesta, contexto):
    prompt = f"""
    Actúa como un corrector de Selectividad de nivel máximo. Tu objetivo es ayudar al alumno a pasar del aprobado al 10 (la excelencia).

    CRITERIOS DE CORRECCIÓN:
    1. RIGOR: ¿Faltan matices técnicos o vocabulario específico de los apuntes?
    2. ESTRUCTURA: ¿La respuesta está bien hilada o es solo una lista de ideas?
    3. EL CAMINO AL 10: Identifica exactamente qué detalle, dato o relación conceptual falta para que la nota sea perfecta.

    CONTEXTO DE REFERENCIA:
    {contexto}

    PREGUNTA: {pregunta}
    RESPUESTA DEL ALUMNO: {respuesta}

    RESPONDE EXCLUSIVAMENTE EN JSON:
    {{
      "nota": 0.0,
      "feedback": "Análisis crítico de la respuesta actual.",
      "olvidos": "Lista de datos o conceptos clave que se han omitido.",
      "como_llegar_al_10": "Instrucciones específicas: qué términos añadir, qué frases mejorar o qué matiz incluir para la nota máxima."
    }}
    """
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Error en la calificación: {e}")
        return {"nota": 0, "feedback": "Error", "olvidos": "Error", "como_llegar_al_10": "Reintentar"}


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
st.sidebar.markdown("---")
st.sidebar.write(f"📖 **Temas cargados:** {len(st.session_state.temas)}")

if st.session_state.temas:
    tema = st.session_state.temas[st.session_state.indice_actual]

    # Barra de progreso
    progreso = (st.session_state.indice_actual + 1) / len(st.session_state.temas)
    st.progress(progreso)
    st.write(f"**Tema {st.session_state.indice_actual + 1} de {len(st.session_state.temas)}**")

    # 1. CREACIÓN DE PESTAÑAS
    tab_estudio, tab_examen = st.tabs(["📖 Estudiar", "📝 Examinarse"])

    with tab_estudio:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(tema['titulo'])
        with col2:
            if st.button("🆘 No entiendo nada", key=f"sos_{st.session_state.indice_actual}"):
                with st.spinner("Simplificando..."):
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": f"Explica esto muy fácil: {tema['explicacion']}"}]
                    )
                    st.warning(res.choices[0].message.content)

        st.write(tema['explicacion'])

        # --- CHAT INTEGRADO EN EL TEMA ---
        st.divider()
        st.markdown("### 💬 Pregúntale a tu Tutor sobre este tema")

        chat_key = f"chat_{st.session_state.indice_actual}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        for mensaje in st.session_state[chat_key]:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

        if prompt_usuario := st.chat_input("¿Qué no te ha quedado claro?", key=f"input_{chat_key}"):
            st.session_state[chat_key].append({"role": "user", "content": prompt_usuario})
            with st.chat_message("user"):
                st.markdown(prompt_usuario)

            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    contexto_chat = f"Eres un tutor. Responde dudas sobre este tema específico: {tema['explicacion']}. Duda del alumno: {prompt_usuario}"
                    respuesta = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": contexto_chat}]
                    )
                    full_response = respuesta.choices[0].message.content
                    st.markdown(full_response)
            st.session_state[chat_key].append({"role": "assistant", "content": full_response})

    with tab_examen:
        st.subheader("🏁 Recta Final antes del Examen")

        # --- CHECKLIST DE ÚLTIMA HORA ---
        with st.expander("🔍 REPASO EXPRESS", expanded=False):
            if st.button("✨ Generar Checklist de Oro", key=f"btn_check_{st.session_state.indice_actual}"):
                with st.spinner("Extrayendo lo vital..."):
                    prompt_check = f"Basándote en este tema: {tema['explicacion']}, dime los 5 conceptos o datos exactos que suelen preguntar. Sé muy breve."
                    res_check = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt_check}]
                    )
                    st.session_state[f"checklist_{st.session_state.indice_actual}"] = res_check.choices[
                        0].message.content

            if f"checklist_{st.session_state.indice_actual}" in st.session_state:
                st.info(st.session_state[f"checklist_{st.session_state.indice_actual}"])

        st.divider()
        st.subheader("📝 Cuestionario")
        st.info(f"1. {tema['preguntas'][0]}")
        st.info(f"2. {tema['preguntas'][1]}")

        resp_usuario = st.text_area("Tus respuestas:", key=f"area_{st.session_state.indice_actual}")

        if st.button("Enviar Examen", key=f"env_{st.session_state.indice_actual}"):
            with st.spinner("Corrigiendo..."):
                resultado = calificar(tema['preguntas'], resp_usuario, tema['explicacion'])
                st.session_state.feedback = resultado

        if st.session_state.feedback:
            fb = st.session_state.feedback
            nota = float(fb['nota'])
            st.markdown(f"### Nota: {nota}/10")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### ✅ Feedback")
                st.write(fb['feedback'])
            with col_b:
                st.markdown("#### 🔥 El Camino al 10")
                st.success(fb['como_llegar_al_10'])

            if nota >= 6.0:
                if st.session_state.indice_actual < len(st.session_state.temas) - 1:
                    if st.button("Siguiente Tema ➡️"):
                        st.session_state.indice_actual += 1
                        st.session_state.feedback = None
                        st.rerun()
                else:
                    st.balloons()
                    st.success("¡TEMARIO COMPLETADO!")

                    # --- SIMULADOR PAU FINAL ---
                    st.divider()
                    if st.button("🎲 Sortear Tema de Examen Global"):
                        import random

                        st.session_state.tema_objeto_examen = random.choice(st.session_state.temas)
                        st.session_state.simulacro_pregunta = f"Desarrolle el siguiente tema: {st.session_state.tema_objeto_examen['titulo']}"
                        st.rerun()

                    if "simulacro_pregunta" in st.session_state:
                        st.error(f"### EXAMEN: {st.session_state.simulacro_pregunta}")
                        resp_pau = st.text_area("Desarrollo completo:", height=300, key="input_pau")
                        if st.button("⚖️ Entregar al Tribunal"):
                            with st.spinner("Calificando..."):
                                prompt_pau = f"Corrige este examen de Selectividad: {st.session_state.simulacro_pregunta}. Respuesta: {resp_pau}. Referencia: {st.session_state.tema_objeto_examen['explicacion']}"
                                final_res = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": prompt_pau}]
                                )
                                st.session_state.resultado_pau = final_res.choices[0].message.content

                        if "resultado_pau" in st.session_state:
                            st.info(st.session_state.resultado_pau)
else:
    st.info("Sube tus apuntes en la barra lateral para empezar.")