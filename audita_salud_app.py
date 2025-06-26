import streamlit as st
import fitz  # PyMuPDF
from transformers import pipeline
from markupsafe import Markup
st.set_page_config(page_title="Auditor Médico", page_icon="🩺", layout="centered")
st.title("Auditor Médico de Historias Clínicas (Colombia)")
st.write("Sube un archivo PDF con la historia clínica y el sistema verificará el cumplimiento de normativas.")

st.markdown("Este sistema te permite verificar automáticamente si una historia clínica cumple con los requerimientos mínimos establecidos por la normatividad colombiana (Resolución 1995 de 1999).")
st.markdown("#### ¿Qué debe contener una historia clínica?")
st.markdown("""
- Motivo de consulta  
- Antecedentes  
- Examen físico  
- Evolución  
- Plan de manejo 
- nombre
- Edad
- Firma del profesional  
""")

uploaded_file = st.file_uploader(" Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    with st.spinner(" Leyendo el contenido del PDF..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

# Funciones auxiliares
    if full_text.strip():
        st.markdown("###  Verificación de campos obligatorios")
        campos_clave = ["motivo de consulta", "antecedentes", "examen físico", "evolución", "plan de manejo", "firma", "nombre", "edad"]
        faltantes = [c for c in campos_clave if c.lower() not in full_text.lower()]

        if not faltantes:
            st.success(" La historia clínica contiene todos los campos clave requeridos.")
        else:
            st.warning(" Faltan los siguientes campos clave:")
            for f in faltantes:
                st.markdown(f"- {f}")

        st.markdown("### 🔍 Buscar una palabra o frase dentro del texto")
        palabra_clave = st.text_input("Escribe una palabra o frase:")

        if palabra_clave:
            resultados = []
            lineas = full_text.split('\n')
            for idx, linea in enumerate(lineas):
                if palabra_clave.lower() in linea.lower():
                    linea_resaltada = linea.replace(
                        palabra_clave,
                        f"<span style='background-color:yellow'><b>{palabra_clave}</b></span>"
                    )
                    resultados.append((f"match-{idx}", linea_resaltada))

            if resultados:
                st.success(f" Se encontraron {len(resultados)} coincidencias:")
                for anchor_id, linea_html in resultados:
                    st.markdown(f"- [Ir a coincidencia](#{anchor_id})", unsafe_allow_html=True)
                    st.markdown(f"<div id='{anchor_id}'>{linea_html}</div>", unsafe_allow_html=True)
            else:
                st.info(" No se encontraron coincidencias.")

        st.markdown("### Periodicidad de Atención Médica")
        fechas = extraer_fechas(full_text)
        if fechas:
            st.markdown(f"- Fechas encontradas: {', '.join(fechas)}")
            promedio = calcular_periodicidad(fechas)
            if promedio:
                st.markdown(f"- En promedio, el paciente es atendido cada **{promedio} días**.")
        else:
            st.info("No se encontraron fechas en el documento.")

        st.markdown("###  Órdenes Médicas o Exámenes Solicitados")
        ordenes = extraer_ordenes(full_text)
        if ordenes:
            for o in ordenes:
                st.markdown(f"-  {o}")
        else:
            st.info("No se encontraron órdenes médicas explícitas en el texto.")

def extraer_fechas(texto):
    patrones_fecha = [r'\d{2}/\d{2}/\d{4}', r'\d{4}-\d{2}-\d{2}']
    fechas = []
    for patron in patrones_fecha:
        fechas.extend(re.findall(patron, texto))
    fechas_unicas = sorted(set(fechas), key=lambda d: datetime.strptime(d, "%d/%m/%Y") if "/" in d else datetime.strptime(d, "%Y-%m-%d"))
    return fechas_unicas

def calcular_periodicidad(fechas):
    if len(fechas) < 2:
        return None
    fechas_dt = [datetime.strptime(f, "%d/%m/%Y") if "/" in f else datetime.strptime(f, "%Y-%m-%d") for f in fechas]
    diferencias = [(fechas_dt[i] - fechas_dt[i-1]).days for i in range(1, len(fechas_dt))]
    return round(sum(diferencias) / len(diferencias), 1)

def extraer_ordenes(texto):
    ordenes = re.findall(r'(Se (ordena|solicita|envía)[^.\n]*)', texto, re.IGNORECASE)
    return [o[0].strip() for o in ordenes]

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
# NUEVO BLOQUE: auditoría mejorada y resaltado
st.markdown("### Buscar palabra clave en el texto")
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
        st.success(f" Se encontraron {len(resultados)} coincidencias:")
        for anchor_id, res in resultados:
           st.markdown(f"- [Ir a coincidencia](#{anchor_id})", unsafe_allow_html=True)
           st.markdown(f"<div id='{anchor_id}'>{res}</div>", unsafe_allow_html=True)

    else:
        st.warning(" No se encontraron coincidencias.")

# AUDITORÍA AUTOMÁTICA
st.markdown("---")
st.markdown("### Campos Faltantes o Inconsistencias")

palabras_clave = [
    "motivo de consulta", "antecedentes", "plan de manejo",
    "firma", "evolución", "examen físico", "nombre", "edad"
]
faltantes = [palabra for palabra in palabras_clave if palabra.lower() not in full_text.lower()]

if not faltantes:
    st.success(" La historia clínica contiene todos los campos clave requeridos.")
else:
    st.error(" Faltan los siguientes campos clave según la norma:")
    for campo in faltantes:
        st.markdown(f"- {campo}")
st.markdown("### Buscar palabra clave en el texto")

# Input para palabra clave
palabra_clave = st.text_input("Ingresa una palabra o frase para buscar")

# Mostrar resultados si hay palabra clave ingresada
if palabra_clave:
    resultados = []
    for idx, linea in enumerate(full_text.split('\n')):

        if palabra_clave.lower() in linea.lower():
            # Resalta la palabra encontrada con Markdown (negrilla azul)
            linea_resaltada = linea.replace(
                palabra_clave,
                f"**:blue[{palabra_clave}]**"
            )
            resultados.append((f"match-{idx}", linea_resaltada))


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
