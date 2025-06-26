import streamlit as st
import fitz  # PyMuPDF

st.set_page_config(page_title="Auditor Médico", page_icon="🩺", layout="centered")

st.title("🩺 Auditor Médico de Historias Clínicas (Colombia)")
st.write("Sube un archivo PDF con la historia clínica y el sistema verificará el cumplimiento de normativas.")

uploaded_file = st.file_uploader("📄 Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    with st.spinner("🔍 Leyendo el contenido del PDF..."):
        # Leer PDF con PyMuPDF
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        if full_text.strip():
                    # Palabras clave mínimas para verificar cumplimiento básico
            
            palabras_clave = ["motivo de consulta", "antecedentes", "plan de manejo", "firma", "evolución", "examen físico"]
            faltantes = [palabra for palabra in palabras_clave if palabra.lower() not in full_text.lower()]

            st.markdown("### Resultado de la auditoría:")
            st.info(f"Campos verificados: {len(palabras_clave)} | Campos faltantes: {len(faltantes)}")

            if not faltantes:
                st.success("La historia clínica contiene todos los campos clave requeridos.")
            else:
                st.error(" Faltan los siguientes campos clave:")
                for palabra in faltantes:
                    st.markdown(f"- {palabra}")

            st.subheader("📖 Texto extraído del PDF:")
            st.text_area("Contenido extraído:", full_text, height=400)
       
        # Añadido código para leer y mostrar texto de PDFs
from transformers import pipeline

# Cargar modelo de resumen (solo se hace una vez)
resumidor = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Generar resumen
if len(full_text) > 100:  # evita errores con textos muy cortos
    resumen = resumidor(full_text[:1000], max_length=130, min_length=30, do_sample=False)[0]['summary_text']
    st.subheader("🧠 Resumen automático del contenido clínico:")
    st.info(resumen)
import streamlit as st
import fitz  # PyMuPDF
from transformers import pipeline

# Configuración de la app
st.set_page_config(page_title="Auditor Médico", page_icon="🩺", layout="centered")
st.title("🩺 Auditor Médico de Historias Clínicas (Colombia)")
st.write("Sube un archivo PDF con la historia clínica y el sistema verificará el cumplimiento de normativas.")

# Subir archivo
uploaded_file = st.file_uploader("📄 Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    with st.spinner("⏳ Leyendo el contenido del PDF..."):
        try:
            # Leer PDF con PyMuPDF
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text()

            if full_text.strip():
                # Palabras clave mínimas para cumplimiento básico
                palabras_clave = ["motivo de consulta", "antecedentes", "plan de manejo", "firma", "evolución", "examen físico"]
                faltantes = [p for p in palabras_clave if p.lower() not in full_text.lower()]

                st.markdown("### ✅ Resultado de la auditoría:")
                st.info(f"Campos verificados: {len(palabras_clave)} | Campos faltantes: {len(faltantes)}")

                if not faltantes:
                    st.success("✅ La historia clínica contiene todos los campos clave requeridos.")
                else:
                    st.error("❌ Faltan los siguientes campos clave:")
                    for palabra in faltantes:
                        st.markdown(f"- {palabra}")

                # Mostrar texto extraído
                st.subheader("📃 Texto extraído del PDF:")
                st.text_area("Contenido extraído:", full_text, height=300)

                # Resumen automático del texto
                if len(full_text) > 100:
                    resumen_modelo = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
                    resumen = resumen_modelo(full_text[:1000], max_length=130, min_length=30, do_sample=False)[0]['summary_text']
                    st.subheader("🤖 Resumen automático del contenido clínico:")
                    st.info(resumen)

                # Evaluación básica de redacción
                st.subheader("Evaluación de redacción clínica:")
                if len(full_text.split()) > 300:
                    st.success("Redacción adecuada: el texto es suficientemente largo y detallado.")
                else:
                    st.warning("Redacción mejorable: el texto clínico parece demasiado corto o resumido.")

                # Validación de algunos elementos normativos de la Resolución 1995
                st.subheader("📑 Validación básica con Resolución 1995 de 1999:")
                criterios = {
                    "Nombre del paciente": "nombre",
                    "Identificación": "cédula",
                    "Firma del profesional": "firma",
                    "Fecha de atención": "fecha",
                    "Diagnóstico": "diagnóstico"
                }
                criterios_faltantes = [campo for campo, palabra in criterios.items() if palabra.lower() not in full_text.lower()]
                if not criterios_faltantes:
                    st.success("Cumple con los criterios normativos básicos.")
                else:
                    st.error("Faltan estos criterios normativos:")
                    for campo in criterios_faltantes:
                        st.markdown(f"- {campo}")
            else:
                st.warning("⚠No se pudo extraer texto del PDF. Verifica que no sea una imagen escaneada.")

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")




