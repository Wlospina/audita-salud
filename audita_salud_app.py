import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
import locale

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Auditor Médico AI", page_icon="🩺", layout="wide")

# Intentar establecer la localización en español para el formato de fechas.
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except locale.Error:
        # Este warning solo aparecerá si la localización falla.
        st.warning("No se pudo establecer la localización a español. Las fechas podrían aparecer en inglés.")

# --- INYECCIÓN DE CSS PARA MEJORAR LA UI/UX ---
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .card-title {
        font-size: 1.5em;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 10px;
    }
    mark {
      background-color: #fde047;
      padding: 2px 4px;
      border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)


# --- SECCIÓN DE FUNCIONES DE LÓGICA (BACK-END) ---
# Todas las funciones que procesan los datos deben estar definidas aquí, al principio.

def extract_text_from_pdf(pdf_file):
    """Extrae texto de un PDF, manejando errores de encriptación o formato."""
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if doc.is_encrypted:
            st.error("❌ **Error: El PDF está protegido con contraseña.**")
            st.warning("Solución: Abra el PDF, elija 'Imprimir' y guárdelo como un nuevo PDF. Luego, suba ese nuevo archivo.")
            doc.close()
            return None
            
        full_text = " ".join(page.get_text() for page in doc)
        doc.close()
        
        if not full_text.strip():
            st.error("❌ **Error: El PDF no contiene texto extraíble (podría ser una imagen).**")
            st.warning("Este sistema solo puede leer PDFs con texto digital, no imágenes escaneadas.")
            return None

        return full_text
        
    except Exception as e:
        st.error(f"❌ **Error inesperado al procesar el PDF:** {e}")
        st.info("El archivo podría estar dañado. Intente la solución de 'Imprimir a PDF'.")
        return None

def calculate_age(birth_date, attention_date):
    """Calcula la edad en años en un momento específico."""
    if not birth_date or not attention_date:
        return "N/D" # No Disponible
    age = attention_date.year - birth_date.year - ((attention_date.month, attention_date.day) < (birth_date.month, birth_date.day))
    return f"{age} años"

def find_birth_date(text):
    """Encuentra la fecha de nacimiento en el texto."""
    match = re.search(r"fecha\s+(de\s+)?nacimiento[\s:]*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4})", text, re.IGNORECASE)
    if match:
        date_str = re.sub(r'[-.]', '/', match.group(2))
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                pass
    return None

def extract_attentions(text):
    """Divide el texto en bloques de atención usando fechas como separadores."""
    pattern = r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})"
    content_parts = re.split(pattern, text)
    attentions = []
    header_info = ""
    
    if len(content_parts) > 1:
        header_info = content_parts[0]
        
        for i in range(1, len(content_parts), 2):
            date_str = re.sub(r'[-.]', '/', content_parts[i])
            content = content_parts[i+1]
            attention_date = None
            for fmt in ("%d/%m/%Y", "%d/%m/%y"):
                try:
                    attention_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError: pass
            
            if attention_date and len(content.strip()) > 50:
                companion_match = re.search(r"(acompañad[oa]\s+por|en\s+compañía\s+de)\s+([^,.\n]+)", content, re.IGNORECASE)
                companion = companion_match.group(2).strip() if companion_match else "No especificado"
                
                attentions.append({
                    "fecha_atencion": attention_date,
                    "contenido": content.strip(),
                    "acompanante": companion
                })
    return attentions, header_info


# --- SECCIÓN DE INTERFAZ DE USUARIO (FRONT-END) ---

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.title("🩺 Auditor Médico AI")
    st.markdown("---")
    st.markdown("### 📄 Instrucciones")
    st.info("""
    1.  **Sube** la historia clínica en PDF.
    2.  **Explora** las pestañas para ver el resumen, la auditoría y el texto completo.
    3.  **Utiliza** la búsqueda para encontrar términos específicos.
    """)
    st.markdown("---")
    st.success("Prototipo funcional. La precisión depende de la calidad del PDF.")


# --- Contenido Principal ---
st.title("Panel de Auditoría de Historias Clínicas")
st.markdown("### Sube un archivo PDF para analizarlo según la normativa colombiana y obtener un resumen ejecutivo.")

uploaded_file = st.file_uploader(
    "Arrastra y suelta el archivo PDF aquí o haz clic para seleccionarlo", 
    type=["pdf"],
    label_visibility="collapsed"
)

# --- Lógica Principal de la Aplicación ---
if not uploaded_file:
    st.info("Esperando un archivo de historia clínica para comenzar el análisis...")
else:
    full_text = extract_text_from_pdf(uploaded_file)

    # El código de análisis solo se ejecuta si el texto fue extraído con éxito
    if full_text:
        st.success("✅ ¡Análisis completado! Revisa los resultados a continuación.")
        
        # Extracción de datos estructurados
        birth_date = find_birth_date(full_text)
        attentions, header_text = extract_attentions(full_text)
        
        # Tarjeta de Resumen del Paciente
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📄 Resumen del Paciente</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        name_match = re.search(r"(?:paciente|nombre)[\s:]*([A-ZÁÉÍÓÚÑ\s]{10,})", header_text, re.IGNORECASE)
        patient_name = name_match.group(1).strip().title() if name_match and name_match.group(1) else "No encontrado"
        col1.metric("Paciente", patient_name)
        col2.metric("Fecha de Nacimiento", birth_date.strftime("%d de %B de %Y") if birth_date else "No encontrada")
        col3.metric("Atenciones Identificadas", len(attentions))
        st.markdown('</div>', unsafe_allow_html=True)

        # Pestañas con los resultados detallados
        tab1, tab2, tab3 = st.tabs(["📊 Resumen de Atenciones", "✅ Auditoría de Campos", "🔍 Búsqueda y Texto Completo"])

        with tab1:
            st.header("Cronología de Atenciones")
            if not attentions:
                st.warning("No se pudieron identificar atenciones individuales en el documento.")
            else:
                sorted_attentions = sorted(attentions, key=lambda x: x['fecha_atencion'], reverse=True)
                for i, att in enumerate(sorted_attentions):
                    age_at_attention = calculate_age(birth_date, att['fecha_atencion'])
                    with st.expander(f"**{att['fecha_atencion'].strftime('%d de %B de %Y')}** - Edad del paciente: **{age_at_attention}**", expanded=(i==0)):
                        st.markdown(f"**Acompañante:** `{att['acompanante']}`")
                        motivo = re.search(r"motivo de consulta:?(.+?)(?:\n[A-ZÁÉÍÓÚÑ\s]+:|$)", att['contenido'], re.IGNORECASE | re.DOTALL)
                        diagnostico = re.search(r"diagn[oó]stico:?(.+?)(?:\n[A-ZÁÉÍÓÚÑ\s]+:|$)", att['contenido'], re.IGNORECASE | re.DOTALL)
                        st.info(f"**Motivo de Consulta:** {motivo.group(1).strip() if motivo else 'No especificado'}")
                        st.success(f"**Diagnóstico/Plan:** {diagnostico.group(1).strip() if diagnostico else 'No especificado'}")
                        if st.checkbox("Mostrar texto completo de esta atención", key=f"cb_{i}"):
                            st.text_area("Contenido:", att['contenido'], height=200, disabled=True, key=f"att_content_{i}")

        with tab2:
            st.header("Auditoría de Campos Obligatorios (Resolución 1995 de 1999)")
            campos_clave = {
                "Identificación del Usuario": ["nombre", "identificacion", "documento"], "Motivo de Consulta": ["motivo de consulta"],
                "Enfermedad Actual": ["enfermedad actual", "evolucion"], "Antecedentes": ["antecedentes"],
                "Examen Físico": ["examen fisico", "examen físico"], "Diagnóstico": ["diagnostico", "diagnóstico", "dx"],
                "Plan de Manejo": ["plan de manejo", "tratamiento"], "Firma del Profesional": ["firma", "dr\.", "dra\."]}
            lower_text = full_text.lower()
            for campo, keywords in campos_clave.items():
                if any(keyword in lower_text for keyword in keywords):
                    st.success(f"✔️ **{campo}:** Encontrado")
                else:
                    st.error(f"❌ **{campo}:** Campo potencialmente ausente o no identificado.")
            st.caption("Nota: Esta es una verificación de palabras clave, no una validación semántica.")

        with tab3:
            st.header("Explorador de Texto Completo")
            palabra_clave = st.text_input("Ingresa una palabra o frase para resaltar en el texto")
            highlighted_text = full_text.replace(chr(10), "<br>")
            if palabra_clave:
                highlighted_text = re.sub(f"({re.escape(palabra_clave)})", r"<mark>\1</mark>", highlighted_text, flags=re.IGNORECASE)
            st.markdown(f'<div style="height:600px;overflow-y:scroll;border:1px solid #ddd;padding:15px;border-radius:5px;background-color:white;">{highlighted_text}</div>', unsafe_allow_html=True)
