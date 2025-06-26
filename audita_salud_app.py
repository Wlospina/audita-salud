import streamlit as st
import fitz  # PyMuPDF
import os

st.set_page_config(page_title="Auditor Médico", layout="wide")

st.title("🩺 Auditor Médico de Historias Clínicas (Colombia)")
st.write("Sube un archivo PDF con la historia clínica y el sistema verificará el cumplimiento de normativas.")

uploaded_file = st.file_uploader("📄 Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    # Guardar el PDF temporalmente
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.read())

    # Extraer texto
    with fitz.open("temp.pdf") as doc:
        text = ""
        for page in doc:
            text += page.get_text()

    st.subheader("Texto extraído:")
    st.text_area("Resultado OCR", text, height=300)

    # Simular verificación con normas
    if "evolución" in text.lower() and "firma" in text.lower():
        st.success("✅ Historia clínica cumple con requisitos básicos.")
    else:
        st.error("❌ Faltan elementos claves como 'evolución' o 'firma'.")

    os.remove("temp.pdf")