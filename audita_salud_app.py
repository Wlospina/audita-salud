import streamlit as st
import fitz  # PyMuPDF
from transformers import pipeline

st.set_page_config(page_title="Auditor Médico", page_icon="🩺", layout="centered")

st.title("Auditor Médico de Historias Clínicas (Colombia)")
st.write("Sube un archivo PDF con la historia clínica y el sistema verificará el cumplimiento de normativas.")

uploaded_file = st.file_uploader(" Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    with st.spinner(" Leyendo el contenido del PDF..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

    if full_text.strip():
        # Palabras clave mínimas para verificar cumplimiento básico
        palabras_clave = ["motivo de consulta", "antecedentes", "plan de manejo", "firma", "evolución", "examen físico"]
        faltantes = [palabra for palabra in palabras_clave if palabra.lower() not in full_text.lower()]

        st.markdown("###  Resultado de la auditoría:")
        st.info(f"Campos verificados: {len(palabras_clave)} | Campos faltantes: {len(faltantes)}")

        if not faltantes:
            st.success("La historia clínica contiene todos los campos clave requeridos.")
        else:
            st.error(" Faltan los siguientes campos clave:")
            for palabra in faltantes:
                st.markdown(f"- {palabra}")

        st.subheader("Texto extraído del PDF:")
        st.text_area("Contenido extraído:", full_text, height=400)
        # Filtro de búsqueda por palabra clave
# Filtro de búsqueda por palabra clave
st.markdown("### Buscar palabra clave en el texto")

# Input para palabra clave
palabra_clave = st.text_input("Ingresa una palabra o frase para buscar")

# Mostrar resultados si hay palabra clave ingresada
if palabra_clave:
    resultados = []
    for linea in full_text.split('\n'):
        if palabra_clave.lower() in linea.lower():
            # Resalta la palabra encontrada con Markdown (negrilla azul)
            linea_resaltada = linea.replace(
                palabra_clave,
                f"**:blue[{palabra_clave}]**"
            )
            resultados.append(linea_resaltada)

    if resultados:
        st.success(f" Se encontraron {len(resultados)} coincidencias:")
        for res in resultados:
            st.markdown(f"- {res}", unsafe_allow_html=True)
    else:
        st.warning("⚠ No se encontraron coincidencias.")



        #  Generar resumen automático con IA (modelo liviano)
        resumidor = pipeline("summarization", model="knkarthick/MEETING_SUMMARY")
        if len(full_text) > 100:
            resumen = resumidor(full_text[:1000])[0]['summary_text']
            st.subheader("Resumen automático del contenido clínico:")
            st.info(resumen)
        else:
        st.warning(" No se pudo extraer texto del PDF. Verifica que no sea un escaneo o imagen.")
