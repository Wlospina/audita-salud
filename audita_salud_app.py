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
            st.subheader("📖 Texto extraído del PDF:")
            st.text_area("Contenido extraído:", full_text, height=400)
        else:
            st.warning("No se pudo extraer texto del PDF. Verifica que no sea una imagen o escaneado.")
# Añadido código para leer y mostrar texto de PDFs

