import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
from html import escape

# --- CONSTANTES ---
# Patrones de Regex compilados para mayor eficiencia y robustez
DATE_PATTERN = re.compile(r"\b(\d{1,2}(?:\s*|/|-)(?:de)?(?:\s*|/|-)(?:[a-zA-ZáéíóúñÁÉÍÓÚÑ]+|\d{1,2})(?:\s*|/|-)(?:de)?(?:\s*|/|-)\d{2,4})\b", re.IGNORECASE)
MESES_MAP = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
    'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}
STARTERS_PATTERN = re.compile(r"^(?:motivo de consulta|enfermedad actual|control|evolución)", re.IGNORECASE | re.MULTILINE)
MESES_MAP_INVERSE = {v: k for k, v in MESES_MAP.items()}


# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Auditor Médico AI", page_icon="🩺", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f5f5f5; }
    .card { background-color: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .card-title { font-size: 1.5em; font-weight: bold; color: #2563EB; margin-bottom: 10px; }
    mark { background-color: #fde047; padding: 2px 4px; border-radius: 3px; color: black; }
    .scroll-container { max-height: 600px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: white; }
</style>
""", unsafe_allow_html=True)

# --- SECCIÓN DE FUNCIONES DE LÓGICA (BACK-END) ---

def format_date_spanish(date_obj):
    if not isinstance(date_obj, datetime): return "Fecha inválida"
    return f"{date_obj.day} de {MESES_MAP_INVERSE[date_obj.month]} de {date_obj.year}"

def parse_date_flexible(date_str):
    date_str_normalized = date_str.lower()
    for name, num in MESES_MAP.items():
        date_str_normalized = date_str_normalized.replace(name, num)
    date_str_clean = re.sub(r'[^0-9/]', '/', date_str_normalized).strip('/')
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str_clean, fmt)
        except (ValueError, TypeError):
            continue
    return None

def find_demographic_data(page_texts):
    """Busca los datos demográficos clave en las primeras páginas."""
    full_text_header = "\n".join(page_texts[:2])
    
    name_match = re.search(r"Nombre\s*Paciente[\s:]*\n([^\n]+)", full_text_header, re.IGNORECASE)
    patient_name = name_match.group(1).strip().title() if name_match else "No encontrado"
    
    birth_date = None
    birth_date_label_match = re.search(r"Fecha\s*Nacimiento[\s:]*", full_text_header, re.IGNORECASE)
    if birth_date_label_match:
        text_after_label = full_text_header[birth_date_label_match.end():]
        date_match = DATE_PATTERN.search(text_after_label)
        if date_match:
            birth_date = parse_date_flexible(date_match.group(1))

    # --- CORRECCIÓN DEL BUG ---
    # El guion '-' debe escaparse con '\' dentro de un conjunto de caracteres [].
    id_match = re.search(r"(?:Identificación|Documento)[\s:]*([0-9X\-.]+)", full_text_header, re.IGNORECASE)
    identification = id_match.group(1).strip() if id_match else "No encontrado"

    return patient_name, birth_date, identification

@st.cache_data(show_spinner=False)
def process_pdf_data(_file_bytes):
    """Función cacheada que procesa los bytes del PDF y extrae toda la información."""
    try:
        doc = fitz.open(stream=_file_bytes, filetype="pdf")
        if doc.is_encrypted: return {"error": "El PDF está protegido por contraseña."}
        
        page_texts = [page.get_text() for page in doc]
        doc.close()
        
        if not any(page.strip() for page in page_texts): return {"error": "El PDF no contiene texto extraíble."}
        
        patient_name, birth_date, identification = find_demographic_data(page_texts)

        attentions = []
        current_attention_content = []
        current_attention_date = None

        for page_text in page_texts:
            is_new_attention_page = STARTERS_PATTERN.search(page_text)
            date_on_page = DATE_PATTERN.search(page_text)

            if is_new_attention_page and date_on_page:
                if current_attention_content:
                    attentions.append({"fecha_atencion": current_attention_date, "contenido": "\n".join(current_attention_content)})
                
                current_attention_date = parse_date_flexible(date_on_page.group(1))
                current_attention_content = [page_text]
            elif current_attention_content:
                current_attention_content.append(page_text)
        
        if current_attention_content:
            attentions.append({"fecha_atencion": current_attention_date, "contenido": "\n".join(current_attention_content)})

        return {
            "patient_name": patient_name, "birth_date": birth_date, "identification": identification,
            "attentions": attentions, "page_texts": page_texts, "error": None
        }

    except Exception as e:
        return {"error": f"Error al procesar el PDF: {str(e)}"}

def calculate_age(birth_date, attention_date):
    if not isinstance(birth_date, datetime) or not isinstance(attention_date, datetime): return "N/D"
    age = attention_date.year - birth_date.year - ((attention_date.month, attention_date.day) < (birth_date.month, birth_date.day))
    return f"{age} años"

# --- SECCIÓN DE INTERFAZ DE USUARIO (FRONT-END) ---
with st.sidebar:
    st.title("🩺 Auditor Médico AI")
    st.markdown("---")
    st.info("1. **Sube** la historia clínica.\n2. **Explora** el resumen y los detalles.\n3. **Usa** la búsqueda para encontrar términos.")
    st.markdown("---")
    st.success("Prototipo v10.0 - Estable.")

st.title("Panel de Auditoría de Historias Clínicas")
st.markdown("### Sube un archivo PDF para analizarlo y obtener un resumen ejecutivo.")

uploaded_file = st.file_uploader("Arrastra y suelta el archivo PDF aquí", type=["pdf"], label_visibility="collapsed")

if not uploaded_file:
    st.info("Esperando un archivo de historia clínica para comenzar el análisis...")
else:
    pdf_bytes = uploaded_file.getvalue()
    data = process_pdf_data(pdf_bytes)

    if data.get("error"):
        st.error(f'❌ **{data["error"]}**')
    else:
        st.success("✅ ¡Análisis completado! Revisa los resultados a continuación.")
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📄 Resumen del Paciente</p>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Paciente", data['patient_name'])
        col2.metric("Fecha de Nacimiento", format_date_spanish(data['birth_date']) if data['birth_date'] else "No encontrada")
        col3.metric("Identificación", data['identification'])
        col4.metric("Atenciones Identificadas", len(data['attentions']))
        st.markdown('</div>', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["📊 Resumen de Atenciones", "✅ Auditoría de Campos", "🔍 Búsqueda y Texto Completo"])

        with tab1:
            st.header("Cronología de Atenciones")
            if not data['attentions']:
                st.warning("No se pudieron identificar atenciones individuales claras en el documento.")
            else:
                for i, att in enumerate(sorted(data['attentions'], key=lambda x: x['fecha_atencion'] or datetime.min, reverse=True)):
                    age = calculate_age(data['birth_date'], att['fecha_atencion'])
                    fecha_display = format_date_spanish(att['fecha_atencion']) if att['fecha_atencion'] else "Fecha no identificada"
                    with st.expander(f"**{fecha_display}** - Edad del paciente: **{age}**", expanded=(i == 0)):
                        content = att['contenido']
                        motivo = re.search(r"(?:motivo de consulta|enfermedad actual|control|evolución)[\s:]*(.+?)(?=\n[A-ZÁÉÍÓÚÑ\s]{4,}:|$)", content, re.DOTALL | re.IGNORECASE)
                        diagnostico = re.search(r"diagn[oó]stico[\s:]*(.+?)(?=\n[A-ZÁÉÍÓÚÑ\s]{4,}:|$)", content, re.DOTALL | re.IGNORECASE)
                        st.info(f"**Motivo/Evolución:** {motivo.group(1).strip() if motivo else 'No especificado'}")
                        st.success(f"**Diagnóstico/Plan:** {diagnostico.group(1).strip() if diagnostico else 'No especificado'}")
                        if st.checkbox("Mostrar texto completo de esta atención", key=f"cb_{i}"):
                            st.text_area("Contenido:", content, height=200, disabled=True, key=f"att_content_{i}")

        with tab2:
            st.header("Auditoría de Campos Obligatorios")
            full_text = "\n".join(data['page_texts']).lower()
            campos_clave = {"Identificación": ["identificacion"], "Motivo Consulta": ["motivo de consulta"], "Enfermedad Actual": ["enfermedad actual"], "Antecedentes": ["antecedentes"], "Examen Físico": ["examen fisico"], "Diagnóstico": ["diagnostico"], "Plan Manejo": ["plan de manejo"], "Firma": ["firma", "dr\."]}
            for campo, keywords in campos_clave.items():
                status = '<span style="color:green;">✔️ Encontrado</span>' if any(kw in full_text for kw in keywords) else '<span style="color:red;">❌ No Encontrado</span>'
                st.markdown(f"- **{campo}:** {status}", unsafe_allow_html=True)

        with tab3:
            st.header("Explorador de Texto Completo")
            palabra_clave = st.text_input("Ingresa una palabra o frase para resaltar en el texto")
            full_text_escaped = escape("\n".join(data['page_texts']))
            if palabra_clave:
                full_text_display = re.sub(f"({re.escape(palabra_clave)})", r"<mark>\1</mark>", full_text_escaped, flags=re.IGNORECASE)
            else:
                full_text_display = full_text_escaped
            st.markdown(f'<div class="scroll-container">{full_text_display.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
