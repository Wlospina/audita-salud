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



