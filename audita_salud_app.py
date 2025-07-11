import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
import bleach
from html import escape

# --- CONSTANTES ---
DATE_PATTERN = re.compile(r"\b(\d{1,2}\s+(?:de\s+)?(?:[a-zA-ZáéíóúñÁÉÍÓÚÑ]+|\d{1,2})(?:\s+de\s+)?\d{2,4})\b", re.IGNORECASE)
MESES_MAP = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
    'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Auditor Médico AI", page_icon="🩺", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f5f5f5; }
    .card { background-color: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .card-title { font-size: 1.5em; font-weight: bold; color: #2563EB; margin-bottom: 10px; }
    mark { background-color: #fde047; padding: 2px 4px; border-radius: 3px; }
    .scroll-container { max-height: 600px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: white; }
</style>
""", unsafe_allow_html=True)

# --- SECCIÓN DE FUNCIONES DE LÓGICA (BACK-END) ---
def format_date_spanish(date_obj):
    """Formatea un objeto datetime al formato español (e.g., "12 de mayo de 2023")."""
    if not isinstance(date_obj, datetime):
        return "Fecha inválida"
    meses = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
             7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
    return f"{date_obj.day} de {meses[date_obj.month]} de {date_obj.year}"

def parse_date_flexible(date_str):
    """Convierte una cadena de texto en un objeto datetime, soportando múltiples formatos."""
    date_str_normalized = date_str.lower()
    for name, num in MESES_MAP.items():
        date_str_normalized = date_str_normalized.replace(name, num)
    date_str_clean = re.sub(r'[^\d\s/-]', '', date_str_normalized).strip('/')
    if not date_str_clean:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%d-%m-%Y", "%d %m %Y"):
        try:
            return datetime.strptime(date_str_clean, fmt)
        except ValueError:
            pass
    return None

def find_birth_date(page_texts):
    """Busca la fecha de nacimiento en todo el documento."""
    for i, page in enumerate(page_texts):
        st.write(f"Buscando fecha de nacimiento en página {i+1}")
        match_label = re.search(r"(?:Fecha\s*Nacimiento|Nacimiento)[\s:]*", page, re.IGNORECASE)
        if match_label:
            text_after_label = page[match_label.end():match_label.end() + 150]
            date_match = re.search(DATE_PATTERN, text_after_label)
            if date_match:
                parsed_date = parse_date_flexible(date_match.group(1))
                st.write(f"Fecha de nacimiento encontrada: {date_match.group(1)} -> {parsed_date}")
                return parsed_date
    st.warning("⚠️ No se pudo extraer la fecha de nacimiento. Revisar el formato en el PDF.")
    return None

def find_patient_name(page_texts):
    """Busca el nombre del paciente en las primeras páginas del documento."""
    for page in page_texts[:2]:
        match = re.search(r"Nombre\s*Paciente[\s:]*\n([^\n]+)", page, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return "No encontrado"

def find_identification(page_texts):
    """Busca el número de identificación del paciente en el documento."""
    for i, page in enumerate(page_texts[:2]):
        st.write(f"Buscando identificación en página {i+1}")
        match = re.search(r"(?:Identificación|Documento)[\s:]*(\d+)", page, re.IGNORECASE)
        if match:
            st.write(f"Identificación encontrada: {match.group(1)}")
            return match.group(1).strip()
    st.warning("⚠️ No se pudo extraer la identificación. Revisar el formato en el PDF.")
    return "No encontrado"

@st.cache_data
def extract_text_pages(pdf_file):
    """Extrae el texto página por página de un archivo PDF."""
    try:
        st.write(f"Procesando archivo: {pdf_file.name}, tamaño: {pdf_file.size} bytes")
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.is_encrypted:
            st.error("❌ **Error: El PDF está protegido por contraseña.**")
            return None
        pages = [page.get_text() for page in doc]
        st.write(f"Extracción completada: {len(pages)} páginas procesadas")
        if not any(page.strip() for page in pages):
            st.error("❌ **Error: El PDF no contiene texto extraíble. Intenta con un PDF basado en texto.**")
            return None
        doc.close()
        return pages
    except Exception as e:
        st.error(f"❌ **Error al procesar el PDF:** {str(e)}. Verifica que el archivo sea un PDF válido.")
        return None

def calculate_age(birth_date, attention_date):
    """Calcula la edad del paciente en el momento de la atención."""
    if not isinstance(birth_date, datetime) or not isinstance(attention_date, datetime):
        return "N/D"
    age = attention_date.year - birth_date.year - ((attention_date.month, attention_date.day) < (birth_date.month, birth_date.day))
    return f"{age} años"

def extract_attentions(page_texts):
    """Extrae atenciones médicas del documento, usando fechas y palabras clave como delimitadores."""
    attentions = []
    current_attention = None
    starters = ["motivo de consulta", "enfermedad actual", "control", "evolución"]
    starters_pattern = re.compile("|".join(starters), re.IGNORECASE)

    for i, page_text in enumerate(page_texts):
        st.write(f"Procesando página {i+1} para atenciones")
        date_match = DATE_PATTERN.search(page_text)
        is_new_attention = starters_pattern.search(page_text) or date_match

        if is_new_attention and date_match:
            if current_attention:
                attentions.append(current_attention)
            current_attention = {
                "fecha_atencion": parse_date_flexible(date_match.group(1)),
                "contenido": page_text
            }
        elif current_attention:
            current_attention["contenido"] += "\n" + page_text

    if current_attention:
        attentions.append(current_attention)
    st.write(f"Atenciones detectadas: {len(attentions)}")
    return attentions

# --- SECCIÓN DE INTERFAZ DE USUARIO (FRONT-END) ---
with st.sidebar:
    st.title("🩺 Auditor Médico AI")
    st.markdown("---")
    st.info("1. **Sube** la historia clínica.\n2. **Explora** el resumen y los detalles.\n3. **Usa** la búsqueda para encontrar términos.")
    st.markdown("---")
    st.success("Prototipo v9.1 - Depuración Activa.")

st.title("Panel de Auditoría de Historias Clínicas")
st.markdown("### Sube un archivo PDF para analizarlo y obtener un resumen ejecutivo.")

uploaded_file = st.file_uploader("Arrastra y suelta el archivo PDF aquí", type=["pdf"], label_visibility="collapsed")

if not uploaded_file:
    st.info("Esperando un archivo de historia clínica para comenzar el análisis...")
else:
    if uploaded_file.size > 10 * 1024 * 1024:  # Límite de 10MB
        st.error("❌ **Error: El archivo excede el tamaño máximo de 10MB.**")
    elif uploaded_file.type != "application/pdf":
        st.error("❌ **Error: Por favor, sube un archivo PDF válido.**")
    else:
        with st.spinner("Procesando el archivo PDF..."):
            page_texts = extract_text_pages(uploaded_file)
            if page_texts:
                st.success("✅ ¡Análisis completado! Revisa los resultados a continuación.")

                patient_name = find_patient_name(page_texts)
                birth_date = find_birth_date(page_texts)
                identification = find_identification(page_texts)
                attentions = extract_attentions(page_texts)

                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<p class="card-title">📄 Resumen del Paciente</p>', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Paciente", patient_name)
                col2.metric("Fecha de Nacimiento", format_date_spanish(birth_date) if birth_date else "No encontrada")
                col3.metric("Identificación", identification)
                col4.metric("Atenciones Identificadas", len(attentions))
                st.markdown('</div>', unsafe_allow_html=True)

                tab1, tab2, tab3 = st.tabs(["📊 Resumen de Atenciones", "✅ Auditoría de Campos", "🔍 Búsqueda y Texto Completo"])

                with tab1:
                    st.header("Cronología de Atenciones")
                    if not attentions:
                        st.warning("No se pudieron identificar atenciones individuales claras en el documento.")
                    else:
                        for i, att in enumerate(sorted(attentions, key=lambda x: x['fecha_atencion'] or datetime.min, reverse=True)):
                            age_at_attention = calculate_age(birth_date, att['fecha_atencion'])
                            fecha_display = format_date_spanish(att['fecha_atencion']) if att['fecha_atencion'] else "Fecha no identificada"

                            with st.expander(f"**{fecha_display}** - Edad del paciente: **{age_at_attention}**", expanded=(i==0)):
                                content_block = att['contenido']
                                companion_match = re.search(r"(acompañad[oa]\s+por|en\s+compañía\s+de)\s+([^\n]+)", content_block, re.IGNORECASE)
                                motivo = re.search(r"(?:motivo de consulta|enfermedad actual|control|evolución)[\s:]*(.+?)(?:\n[A-ZÁÉÍÓÚÑ\s]{4,}:|$)", content_block, re.IGNORECASE | re.DOTALL)
                                diagnostico = re.search(r"diagn[oó]stico[\s:]*(.+?)(?:\n[A-ZÁÉÍÓÚÑ\s]{4,}:|$)", content_block, re.IGNORECASE | re.DOTALL)

                                st.markdown(f"**Acompañante:** `{companion_match.group(2).strip() if companion_match else 'No especificado'}`")
                                st.info(f"**Motivo de Consulta/Evolución:** {motivo.group(1).strip() if motivo else 'No especificado'}")
                                st.success(f"**Diagnóstico/Plan:** {diagnostico.group(1).strip() if diagnostico else 'No especificado'}")
                                if st.checkbox("Mostrar texto completo de esta atención", key=f"cb_{i}"):
                                    st.text_area("Contenido:", content_block, height=200, disabled=True, key=f"att_content_{i}")

                with tab2:
                    st.header("Auditoría de Campos Obligatorios")
                    campos_clave = {
                        "Identificación": ["identificacion", "documento"],
                        "Motivo de Consulta": ["motivo de consulta"],
                        "Enfermedad Actual": ["enfermedad actual"],
                        "Antecedentes": ["antecedentes"],
                        "Examen Físico": ["examen fisico"],
                        "Diagnóstico": ["diagnostico", "dx"],
                        "Plan de Manejo": ["plan de manejo"],
                        "Firma del Profesional": ["firma", "dr\."]
                    }
                    full_text = "\n".join(page_texts).lower()
                    for campo, keywords in campos_clave.items():
                        status = '<span style="color:green;">✔️ Encontrado</span>' if any(kw in full_text for kw in keywords) else '<span style="color:red;">❌ No Encontrado</span>'
                        st.markdown(f"- **{campo}:** {status}", unsafe_allow_html=True)

                with tab3:
                    st.header("Explorador de Texto Completo")
                    palabra_clave = st.text_input("Ingresa una palabra o frase para resaltar en el texto")
                    full_text_display = "\n".join(page_texts).replace('\n', '<br>')
                    if palabra_clave:
                        palabra_clave_escaped = escape(palabra_clave)
                        full_text_display = re.sub(f"({re.escape(palabra_clave_escaped)})", r"<mark>\1</mark>", full_text_display, flags=re.IGNORECASE)
                        full_text_display = bleach.clean(full_text_display)
                    st.markdown(f'<div class="scroll-container">{full_text_display}</div>', unsafe_allow_html=True)
                    
