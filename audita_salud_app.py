import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
from transformers import pipeline
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

        # El resto del código permanece igual...


        # Periodicidad de atención
        st.subheader("Periodicidad de Atención Médica")
        fechas = []
        patrones_fecha = [r'\d{2}/\d{2}/\d{4}', r'\d{4}-\d{2}-\d{2}']
        for patron in patrones_fecha:
            fechas.extend(re.findall(patron, full_text))
        fechas_unicas = sorted(set(fechas), key=lambda d: datetime.strptime(d, "%d/%m/%Y") if "/" in d else datetime.strptime(d, "%Y-%m-%d"))

        # Detectar fecha de nacimiento
        nacimiento_match = re.search(r'(Fecha de nacimiento|fecha nacimiento|Nacimiento):?\s*(\d{2}[/-]\d{2}[/-]\d{4})', full_text, re.IGNORECASE)
        fecha_nacimiento = None
        if nacimiento_match:
            fecha_nacimiento = nacimiento_match.group(2).replace("-", "/")
            try:
                fecha_nacimiento_dt = datetime.strptime(fecha_nacimiento, "%d/%m/%Y")
            except:
                fecha_nacimiento_dt = None

        if fechas_unicas:
            st.markdown(f"- Fechas encontradas: {', '.join(fechas_unicas)}")
            if len(fechas_unicas) > 1:
                fechas_dt = [datetime.strptime(f, "%d/%m/%Y") if "/" in f else datetime.strptime(f, "%Y-%m-%d") for f in fechas_unicas]
                diferencias = [(fechas_dt[i] - fechas_dt[i - 1]).days for i in range(1, len(fechas_dt))]
                promedio = round(sum(diferencias) / len(diferencias), 1)
                st.markdown(f"- En promedio, el paciente es atendido cada **{promedio} días**.")

            if fecha_nacimiento_dt:
                edades = []
                for f in fechas_unicas:
                    dt = datetime.strptime(f, "%d/%m/%Y") if "/" in f else datetime.strptime(f, "%Y-%m-%d")
                    edad = dt.year - fecha_nacimiento_dt.year - ((dt.month, dt.day) < (fecha_nacimiento_dt.month, fecha_nacimiento_dt.day))
                    edades.append((f, edad))
                st.markdown("**Edad del paciente en cada atención:**")
                for f, e in edades:
                    st.markdown(f"- 📆 {f}: **{e} años**")

                edad_actual = datetime.today().year - fecha_nacimiento_dt.year - ((datetime.today().month, datetime.today().day) < (fecha_nacimiento_dt.month, fecha_nacimiento_dt.day))
                st.markdown(f"- Edad actual del paciente: **{edad_actual} años**")

            # Buscar acompañante o responsable
            responsable = re.search(r'(acompañante|responsable)[^:\n]*[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ ]{3,})', full_text, re.IGNORECASE)
            if responsable:
                st.markdown(f"- Acompañante o responsable: **{responsable.group(2).strip()}**")
        else:
            st.info("No se encontraron fechas en el documento.")

        # Órdenes médicas
        st.subheader("Órdenes Médicas o Exámenes Solicitados")
        ordenes = re.findall(r'(Se (ordena|solicita|envía)[^\.\n]*)', full_text, re.IGNORECASE)
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
