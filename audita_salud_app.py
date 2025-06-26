import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
from transformers import pipeline
from markupsafe import Markup
import streamlit.components.v1 as components

st.set_page_config(page_title="Auditor Médico", page_icon="🩺", layout="centered")
st.title("Auditor Médico de Historias Clínicas (Colombia)")

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
        st.subheader("Verificación de campos obligatorios")
        campos_clave = ["motivo de consulta", "antecedentes", "examen físico", "evolución", "plan de manejo", "firma", "nombre", "edad"]
        faltantes = [c for c in campos_clave if c.lower() not in full_text.lower()]

        if not faltantes:
            st.success("La historia clínica contiene todos los campos clave requeridos.")
        else:
            st.warning("Faltan los siguientes campos clave:")
            for f in faltantes:
                st.markdown(f"- {f}")

        # Buscar palabra clave
        st.subheader("Buscar palabra clave en el texto")
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

        # Mostrar texto completo con scroll y resaltado
        st.subheader("Texto extraído del PDF")
       
anchors = []

for idx, linea in enumerate(full_text.split('\n')):
    if palabra_clave.lower() in linea.lower():
        linea_resaltada = linea.replace(
            palabra_clave,
            f"<mark id='match-{idx}'>{palabra_clave}</mark>"
        )
        highlighted_lines.append(f"<div>{linea_resaltada}</div>")
        anchors.append(idx)
    else:
        highlighted_lines.append(f"<div>{linea}</div>")

components.html(
    f"""
    <div id="texto_extraido" style="height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px;">
        {''.join(highlighted_lines)}
    </div>
    <script>
        const params = new URLSearchParams(window.location.hash.substring(1));
        const target = document.getElementById("{'match-' + str(anchors[0]) if anchors else ''}");
        if (target) {{
            target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
 </script>
""",
height=400
)


        # Periodicidad de atención
                    st.subheader("Periodicidad de Atención Médica")
            fechas = []
            patrones_fecha = [r'\d{2}/\d{2}/\d{4}', r'\d{4}-\d{2}-\d{2}']
            for patron in patrones_fecha:
            fechas.extend(re.findall(patron, full_text))
            fechas_unicas = sorted(set(fechas), key=lambda d: datetime.strptime(d, "%d/%m/%Y") if "/" in d else datetime.strptime(d, "%Y-%m-%d"))

        if fechas_unicas:
            st.markdown(f"- Fechas encontradas: {', '.join(fechas_unicas)}")
            if len(fechas_unicas) > 1:
                fechas_dt = [datetime.strptime(f, "%d/%m/%Y") if "/" in f else datetime.strptime(f, "%Y-%m-%d") for f in fechas_unicas]
                diferencias = [(fechas_dt[i] - fechas_dt[i - 1]).days for i in range(1, len(fechas_dt))]
                promedio = round(sum(diferencias) / len(diferencias), 1)
                st.markdown(f"- En promedio, el paciente es atendido cada **{promedio} días**.")

            # Mostrar edad actual
            edad_actual = re.search(r'(\d+)\s*(años|a\.?\s?m\.?|a\.?\s?nos)', full_text.lower())
            if edad_actual:
                st.markdown(f"- Edad actual del paciente: **{edad_actual.group(1)} años**")

            # Buscar acompañante o responsable
            responsable = re.search(r'(acompañante|responsable)[^:\n]*[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ ]{3,})', full_text, re.IGNORECASE)
            if responsable:
                st.markdown(f"- Acompañante o responsable: **{responsable.group(2).strip()}**")
        else:
            st.info("No se encontraron fechas en el documento.")

        # Órdenes médicas
        st.subheader("Órdenes Médicas o Exámenes Solicitados")
        ordenes = re.findall(r'(Se (ordena|solicita|envía)[^.\n]*)', full_text, re.IGNORECASE)
        if ordenes:
            for o in ordenes:
                st.markdown(f"- {o[0].strip()}")
        else:
            st.info("No se encontraron órdenes médicas explícitas en el texto.")

        # Resumen automático con IA
        st.subheader("Resumen automático del contenido clínico")
        resumidor = pipeline("summarization", model="knkarthick/MEETING_SUMMARY")
        if len(full_text) > 100:
            resumen = resumidor(full_text[:1000])[0]['summary_text']
            st.info(resumen)
        else:
            st.warning("No se pudo extraer texto suficiente del PDF para generar resumen.")
