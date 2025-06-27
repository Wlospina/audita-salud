import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
from markupsafe import Markup
import streamlit.components.v1 as components

st.set_page_config(page_title="Auditor Médico", page_icon="🩺", layout="wide")

# Barra lateral
st.sidebar.title("📄 Instrucciones")
st.sidebar.markdown("1. Sube un archivo PDF de historia clínica.\n2. Revisa los campos obligatorios.\n3. Usa la búsqueda de texto.\n4. Consulta periodicidad, edad y órdenes médicas.")

st.title("🩺 Auditor Médico de Historias Clínicas (Colombia)")

st.markdown("Sube un archivo PDF con la historia clínica y el sistema verificará el cumplimiento de normativas.")
st.markdown("""
#### ¿Qué debe contener una historia clínica?
- Motivo de consulta  
- Antecedentes  
- Examen físico  
- Evolución  
- Plan de manejo  
- Nombre  
- Edad  
- Firma del profesional
""")

uploaded_file = st.file_uploader("Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    with st.spinner("Leyendo el contenido del PDF..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

    if full_text.strip():
        # Verificación de campos obligatorios
        st.subheader("✅ Verificación de campos obligatorios")
        campos_clave = ["motivo de consulta", "antecedentes", "examen físico", "evolución", "plan de manejo", "firma", "nombre", "edad"]
        faltantes = [c for c in campos_clave if c.lower() not in full_text.lower()]

        if not faltantes:
            st.success("La historia clínica contiene todos los campos clave requeridos.")
        else:
            st.warning("Faltan los siguientes campos clave:")
            for f in faltantes:
                st.markdown(f"- {f}")

        # Buscar palabra clave
        st.subheader("🔍 Buscar palabra clave en el texto")
        palabra_clave = st.text_input("Ingresa una palabra o frase para buscar")

        if palabra_clave:
            resultados = []
            for idx, linea in enumerate(full_text.split('\n')):
                if palabra_clave.lower() in linea.lower():
                    linea_resaltada = linea.replace(
                        palabra_clave,
                        Markup(f"<span style='background-color:yellow'><b>{palabra_clave}</b></span>")
                    )
                    resultados.append((f"match-{idx}", linea_resaltada))

            if resultados:
                st.success(f"Se encontraron {len(resultados)} coincidencias:")
                for anchor_id, res in resultados:
                    st.markdown(f"- [Ir a coincidencia](#{anchor_id})", unsafe_allow_html=True)
                    st.markdown(f"<div id='{anchor_id}'>{res}</div>", unsafe_allow_html=True)
            else:
                st.warning("No se encontraron coincidencias.")

        # Mostrar texto completo con scroll y responsivo
        st.subheader("📃 Texto extraído del PDF")
        components.html(
            f"""
            <style>
                #texto_extraido {{
                    max-height: 60vh;
                    overflow-y: auto;
                    border: 1px solid #ccc;
                    padding: 15px;
                    background: #f9f9f9;
                    font-size: 15px;
                    line-height: 1.5;
                    font-family: 'Segoe UI', sans-serif;
                }}
                @media (max-width: 768px) {{
                    #texto_extraido {{ font-size: 14px; }}
                }}
            </style>
            <div id='texto_extraido'>
                {'<br>'.join([f"<div id='match-{idx}'>{linea.replace(palabra_clave, f'<mark>{palabra_clave}</mark>')}</div>" if palabra_clave.lower() in linea.lower() else linea for idx, linea in enumerate(full_text.split('\n'))])}
            </div>
            <script>
                const url = new URL(window.location.href);
                const hash = url.hash;
                if (hash.startsWith("#match-")) {{
                    const el = document.getElementById(hash.slice(1));
                    if (el) {{
                        el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        el.style.backgroundColor = '#fff8c6';
                    }}
                }}
            </script>
            """,
            height=400
        )

        # Buscar fecha de nacimiento en el texto
        fecha_nacimiento_dt = None
        match_fn = re.search(r"fecha\s+nacimiento[\s:\-]*([\d]{{1,2}}/[\d]{{1,2}}/[\d]{{2,4}})", full_text, re.IGNORECASE)
        if match_fn:
            try:
                fecha_nacimiento_dt = datetime.strptime(match_fn.group(1), "%d/%m/%Y")
            except ValueError:
                try:
                    fecha_nacimiento_dt = datetime.strptime(match_fn.group(1), "%d/%m/%y")
                except:
                    pass

        # Aquí continuaría el resto de funcionalidades, como periodicidad, edad, etc.
        # Asegúrate de utilizar la variable `fecha_nacimiento_dt` solo si fue definida correctamente
        # if fecha_nacimiento_dt:
        #     calcular edad o mostrar edad al momento de cada atención
