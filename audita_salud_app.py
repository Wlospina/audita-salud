import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Auditor Médico AI", page_icon="🩺", layout="wide")

# --- INYECCIÓN DE CSS PARA MEJORAR LA UI/UX ---
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
    """Formatea una fecha a un string en español de forma segura."""
    if not isinstance(date_obj, datetime): return "Fecha inválida"
    meses = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
    return f"{date_obj.day} de {meses[date_obj.month]} de {date_obj.year}"

def parse_date_flexible(date_str):
    """Parsea un string de fecha que puede contener el mes como texto o número."""
    meses_map = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
    date_str_normalized = date_str.lower()
    for name, num in meses_map.items():
        date_str_normalized = date_str_normalized.replace(name, num)
    
    # Limpia el string de cualquier carácter no deseado y normaliza separadores
    date_str_clean = re.sub(r'[\s/]+', '/', date_str_normalized)
    date_str_clean = re.sub(r'[^0-9/]', '', date_str_clean) # Quita todo lo que no sea número o /
    
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str_clean, fmt)
        except ValueError:
            pass
    return None

def find_birth_date(text):
    """Función de dos pasos: encuentra la etiqueta 'Fecha Nacimiento' y luego parsea las líneas siguientes."""
    match_label = re.search(r"Fecha\s*Nacimiento[\s:]*", text, re.IGNORECASE)
    if not match_label:
        return None
    
    # Analiza el texto justo después de la etiqueta (ej. los siguientes 50 caracteres)
    text_after_label = text[match_label.end() : match_label.end() + 50]
    return parse_date_flexible(text_after_label)

def find_patient_name(text):
    """Encuentra el nombre del paciente buscando la etiqueta y capturando la línea siguiente."""
    # Busca "Nombre Paciente:" y captura la línea siguiente, que es el nombre.
    match = re.search(r"Nombre\s*Paciente[\s:]*\n([^\n]+)", text, re.IGNORECASE)
    if match:
        # Limpia y formatea el nombre.
        return match.group(1).strip().title()
    return "No encontrado"

def extract_text_from_pdf(pdf_file):
    """Extrae texto de un PDF, PRESENVANDO LOS SALTOS DE LÍNEA."""
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.is_encrypted:
            st.error("❌ **Error: El PDF está protegido.**")
            return None
        # La corrección clave: unir con '\n' en lugar de ' '.
        full_text = "\n".join(page.get_text() for page in doc)
        if not full_text.strip():
            st.error("❌ **Error: El PDF no contiene texto extraíble.**")
            return None
        return full_text
    except Exception as e:
        st.error(f"❌ **Error inesperado al procesar el PDF:** {e}")
        return None

def calculate_age(birth_date, attention_date):
    if not birth_date or not attention_date: return "N/D"
    age = attention_date.year - birth_date.year - ((attention_date.month, attention_date.day) < (birth_date.month, birth_date.day))
    return f"{age} años"

def extract_attentions(text):
    """Identifica bloques de atención basándose en palabras clave de inicio."""
    attentions = []
    # Usamos una lista de posibles inicios de consulta
    block_starters = ["motivo de consulta", "enfermedad actual", "revisión por sistemas", "evolución"]
    block_starters_pattern = "|".join(block_starters)
    
    date_pattern = r"\d{1,2}[/\s-](?:[a-zA-ZáéíóúñÁÉÍÓÚÑ]+|[0-9]{1,2})[/\s-]\d{2,4}"

    for match in re.finditer(block_starters_pattern, text, re.IGNORECASE):
        # Busca la fecha más cercana antes de este bloque de consulta
        search_area_for_date = text[:match.start()]
        date_matches = list(re.finditer(date_pattern, search_area_for_date))
        if date_matches:
            latest_date_str = date_matches[-1].group(0)
            attention_date = parse_date_flexible(latest_date_str)
            
            # Para evitar duplicados, solo añadimos si la fecha es nueva
            if attention_date and (not attentions or attentions[-1]['fecha_atencion'] != attention_date):
                attentions.append({"fecha_atencion": attention_date, "contenido": text[match.start():]})
    
    # Si no se encontraron bloques, puede ser una historia simple. Intentamos un método de respaldo.
    if not attentions:
        # Aquí se podría añadir una lógica alternativa si el primer método falla.
        pass
        
    return attentions

# --- SECCIÓN DE INTERFAZ DE USUARIO (FRONT-END) ---
with st.sidebar:
    st.title("🩺 Auditor Médico AI")
    st.markdown("---")
    st.info("1. **Sube** la historia clínica.\n2. **Explora** el resumen y los detalles.\n3. **Usa** la búsqueda para encontrar términos.")
    st.markdown("---")
    st.success("Prototipo v6.0 - Precisión Mejorada.")

st.title("Panel de Auditoría de Historias Clínicas")
st.markdown("### Sube un archivo PDF para analizarlo y obtener un resumen ejecutivo.")

uploaded_file = st.file_uploader("Arrastra y suelta el archivo PDF aquí", type=["pdf"], label_visibility="collapsed")

if not uploaded_file:
    st.info("Esperando un archivo de historia clínica para comenzar el análisis...")
else:
    full_text = extract_text_from_pdf(uploaded_file)
    if full_text:
        st.success("✅ ¡Análisis completado! Revisa los resultados a continuación.")
        
        patient_name = find_patient_name(full_text)
        birth_date = find_birth_date(full_text)
        attentions = extract_attentions(full_text)
        
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
                for i, att in enumerate(attentions):
                    age_at_attention = calculate_age(birth_date, att['fecha_atencion'])
                    with st.expander(f"**{format_date_spanish(att['fecha_atencion'])}** - Edad del paciente: **{age_at_attention}**", expanded=(i==0)):
                        content_block = att['contenido']
                        companion_match = re.search(r"(acompañad[oa]\s+por|en\s+compañía\s+de)\s+([^\n]+)", content_block, re.IGNORECASE)
                        motivo = re.search(r"motivo de consulta:?(.+?)(?:\n[A-ZÁÉÍÓÚÑ\s]{4,}:|$)", content_block, re.IGNORECASE | re.DOTALL)
                        diagnostico = re.search(r"diagn[oó]stico:?(.+?)(?:\n[A-ZÁÉÍÓÚÑ\s]{4,}:|$)", content_block, re.IGNORECASE | re.DOTALL)
                        st.markdown(f"**Acompañante:** `{companion_match.group(2).strip() if companion_match else 'No especificado'}`")
                        st.info(f"**Motivo de Consulta:** {motivo.group(1).strip() if motivo else 'No especificado'}")
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
