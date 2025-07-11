import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Auditor Médico AI", page_icon="🩺", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f5f5f5; }
    .card { background-color: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .card-title { font-size: 1.5em; font-weight: bold; color: #2563EB; margin-bottom: 10px; }
    mark { background-color: #fde047; padding: 2px 4px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# --- SECCIÓN DE FUNCIONES DE LÓGICA (BACK-END) ---

def format_date_spanish(date_obj):
    if not isinstance(date_obj, datetime): return "Fecha inválida"
    meses = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
    return f"{date_obj.day} de {meses[date_obj.month]} de {date_obj.year}"

def parse_date_flexible(date_str):
    meses_map = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
    date_str_normalized = date_str.lower()
    for name, num in meses_map.items():
        date_str_normalized = date_str_normalized.replace(name, num)
    date_str_clean = re.sub(r'[^0-9/]', '', date_str_normalized).strip('/')
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str_clean, fmt)
        except ValueError:
            pass
    return None

def find_birth_date(text):
    # Busca la etiqueta y luego busca un patrón de fecha en un área más amplia (100 caracteres)
    match_label = re.search(r"Fecha\s*Nacimiento[\s:]*", text, re.IGNORECASE)
    if match_label:
        text_after_label = text[match_label.end():match_label.end() + 100]
        date_match = re.search(r"(\d{1,2}[/\s-](?:[a-zA-ZáéíóúñÁÉÍÓÚÑ]+|[0-9]{1,2})[/\s-]\d{2,4})", text_after_label)
        if date_match:
            return parse_date_flexible(date_match.group(1))
    return None

def find_patient_name(text):
    match = re.search(r"Nombre\s*Paciente[\s:]*\n([^\n]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return "No encontrado"

def extract_text_pages(pdf_file):
    """NUEVA FUNCIÓN: Extrae el texto PÁGINA POR PÁGINA, manteniendo la estructura."""
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.is_encrypted:
            st.error("❌ **Error: El PDF está protegido.**")
            return None
        pages = [page.get_text() for page in doc]
        if not any(page.strip() for page in pages):
            st.error("❌ **Error: El PDF no contiene texto extraíble.**")
            return None
        return pages
    except Exception as e:
        st.error(f"❌ **Error inesperado al procesar el PDF:** {e}")
        return None

def calculate_age(birth_date, attention_date):
    if not birth_date or not attention_date: return "N/D"
    age = attention_date.year - birth_date.year - ((attention_date.month, attention_date.day) < (birth_date.month, birth_date.day))
    return f"{age} años"

def extract_attentions(page_texts):
    """NUEVA ARQUITECTURA: Procesa el documento página por página para encontrar atenciones."""
    attentions = []
    current_attention = None
    
    # Palabras clave que indican el inicio de una nueva consulta/atención
    starters = ["motivo de consulta", "enfermedad actual", "control", "evolución"]
    starters_pattern = re.compile("|".join(starters), re.IGNORECASE)
    date_pattern = re.compile(r"\b(\d{1,2}[/\s-](?:[a-zA-ZáéíóúñÁÉÍÓÚÑ]+|[0-9]{1,2})[/\s-]\d{2,4})\b", re.IGNORECASE)

    for page_text in page_texts:
        is_new_attention = starters_pattern.search(page_text)
        
        if is_new_attention:
            # Si encontramos un inicio, guardamos la atención anterior (si existía)
            if current_attention:
                attentions.append(current_attention)
            
            # Buscamos la fecha en la página actual
            date_match = date_pattern.search(page_text)
            attention_date = parse_date_flexible(date_match.group(1)) if date_match else None
            
            # Creamos la nueva atención
            current_attention = {
                "fecha_atencion": attention_date,
                "contenido": page_text
            }
        elif current_attention:
            # Si no es una nueva atención, es una continuación de la anterior
            current_attention["contenido"] += "\n" + page_text
            
    # No olvidar guardar la última atención después del bucle
    if current_attention:
        attentions.append(current_attention)
        
    return attentions

# --- SECCIÓN DE INTERFAZ DE USUARIO (FRONT-END) ---
with st.sidebar:
    st.title("🩺 Auditor Médico AI")
    st.markdown("---")
    st.info("1. **Sube** la historia clínica.\n2. **Explora** el resumen y los detalles.\n3. **Usa** la búsqueda para encontrar términos.")
    st.markdown("---")
    st.success("Prototipo v8.0 - Lógica Reconstruida.")

st.title("Panel de Auditoría de Historias Clínicas")
st.markdown("### Sube un archivo PDF para analizarlo y obtener un resumen ejecutivo.")

uploaded_file = st.file_uploader("Arrastra y suelta el archivo PDF aquí", type=["pdf"], label_visibility="collapsed")

if not uploaded_file:
    st.info("Esperando un archivo de historia clínica para comenzar el análisis...")
else:
    page_texts = extract_text_pages(uploaded_file)
    if page_texts:
        full_text = "\n".join(page_texts)
        st.success("✅ ¡Análisis completado! Revisa los resultados a continuación.")
        
        patient_name = find_patient_name(full_text)
        birth_date = find_birth_date(full_text)
        attentions = extract_attentions(page_texts)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📄 Resumen del Paciente</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Paciente", patient_name)
        col2.metric("Fecha de Nacimiento", format_date_spanish(birth_date) if birth_date else "No encontrada")
        col3.metric("Atenciones Identificadas", len(attentions))
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
            campos_clave = {"Identificación": ["identificacion", "documento"], "Motivo de Consulta": ["motivo de consulta"], "Enfermedad Actual": ["enfermedad actual"], "Antecedentes": ["antecedentes"], "Examen Físico": ["examen fisico"], "Diagnóstico": ["diagnostico", "dx"], "Plan de Manejo": ["plan de manejo"], "Firma del Profesional": ["firma", "dr\."]}
            lower_text = full_text.lower()
            for campo, keywords in campos_clave.items():
                st.markdown(f"- **{campo}:** {'<span style=\"color:green;\">✔️ Encontrado</span>' if any(kw in lower_text for kw in keywords) else '<span style=\"color:red;\">❌ No Encontrado</span>'}", unsafe_allow_html=True)

        with tab3:
            st.header("Explorador de Texto Completo")
            palabra_clave = st.text_input("Ingresa una palabra o frase para resaltar en el texto")
            highlighted_text = full_text.replace('\n', '<br>')
            if palabra_clave:
                highlighted_text = re.sub(f"({re.escape(palabra_clave)})", r"<mark>\1</mark>", highlighted_text, flags=re.IGNORECASE)
            st.markdown(f'<div style="height:600px;overflow-y:scroll;border:1px solid #ddd;padding:15px;border-radius:5px;background-color:white;">{highlighted_text}</div>', unsafe_allow_html=True)
