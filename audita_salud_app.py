import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
import pandas as pd # Usaremos pandas para mostrar los resúmenes de forma ordenada

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Auditor Médico AI", page_icon="🩺", layout="wide")

# --- FUNCIONES DE LÓGICA DE BACK-END ---

def extract_text_from_pdf(pdf_file):
    """Extrae texto de un archivo PDF subido."""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        full_text = " ".join(page.get_text() for page in doc)
        doc.close()
        return full_text
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return None

def calculate_age(birth_date, attention_date):
    """Calcula la edad en años en un momento específico."""
    if not birth_date or not attention_date:
        return "N/A"
    age = attention_date.year - birth_date.year - ((attention_date.month, attention_date.day) < (birth_date.month, birth_date.day))
    return age

def find_birth_date(text):
    """Encuentra la fecha de nacimiento en el texto usando regex."""
    # Regex mejorado para capturar más formatos (dd/mm/yyyy, dd-mm-yyyy, etc.)
    match = re.search(r"fecha\s+(de\s+)?nacimiento[\s:]*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4})", text, re.IGNORECASE)
    if match:
        date_str = match.group(2).replace('-', '/')
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                pass
    return None

def extract_attentions(text):
    """
    Función clave para extraer cada atención/consulta como un bloque de texto separado.
    Esto asume que cada nueva atención está marcada por una fecha.
    """
    # Regex para encontrar fechas en formato dd/mm/yyyy o similar. Este es el pivote.
    # Esta es la parte más delicada y que podrías tener que ajustar.
    pattern = r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})"
    
    # Split el texto por las fechas encontradas. El primer elemento es el encabezado.
    content_parts = re.split(pattern, text)
    
    attentions = []
    # Empezamos desde el índice 1, agrupando fecha y contenido
    for i in range(1, len(content_parts), 2):
        date_str = content_parts[i]
        content = content_parts[i+1]
        
        # Intentamos parsear la fecha
        attention_date = None
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"):
            try:
                attention_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                pass
        
        if attention_date and len(content.strip()) > 50: # Evitar fechas sueltas sin contenido
            # Buscamos acompañantes en el texto de esta atención
            companion_match = re.search(r"(acompañad[oa]\s+por|en\s+compañía\s+de)\s+([^,.\n]+)", content, re.IGNORECASE)
            companion = companion_match.group(2).strip() if companion_match else "No especificado"
            
            attentions.append({
                "fecha_atencion": attention_date,
                "contenido": content.strip(),
                "acompanante": companion
            })
            
    return attentions

# --- INTERFAZ DE USUARIO (FRONT-END CON STREAMLIT) ---

# Barra lateral
st.sidebar.title("📄 Instrucciones")
st.sidebar.markdown("""
1.  **Sube** la historia clínica en formato PDF.
2.  El sistema **analizará** automáticamente el contenido.
3.  **Revisa** el resumen de atenciones y la verificación de campos.
4.  **Utiliza la búsqueda** para encontrar términos específicos en el documento.
""")
st.sidebar.info("App desarrollada como prototipo para auditoría médica. La precisión depende de la calidad y formato del PDF.")

st.title("🩺 Auditor Médico AI (Normativa Colombiana)")
st.markdown("Esta herramienta extrae y estructura la información de historias clínicas para facilitar la auditoría.")

uploaded_file = st.file_uploader("Sube el archivo PDF de la historia clínica", type=["pdf"])

if uploaded_file:
    full_text = extract_text_from_pdf(uploaded_file)

    if full_text:
        st.success("✅ PDF procesado correctamente.")
        
        # Extraer información clave
        birth_date = find_birth_date(full_text)
        attentions = extract_attentions(full_text)
        
        # --- Pestañas para organizar la información ---
        tab1, tab2, tab3 = st.tabs(["📊 Resumen de Atenciones", "✅ Auditoría de Campos", "🔍 Búsqueda y Texto Completo"])

        with tab1:
            st.header("Resumen Cronológico de Atenciones")
            if not attentions:
                st.warning("No se pudieron identificar atenciones individuales basadas en fechas. El documento puede tener un formato no estándar.")
            else:
                summary_data = []
                for att in sorted(attentions, key=lambda x: x['fecha_atencion']):
                    age_at_attention = calculate_age(birth_date, att['fecha_atencion']) if birth_date else "Fecha Nac. no encontrada"
                    # Resumen simple del contenido: las primeras 250 letras.
                    short_summary = att['contenido'][:250].strip() + "..."
                    
                    summary_data.append({
                        "Fecha Atención": att['fecha_atencion'].strftime("%Y-%m-%d"),
                        "Edad en Atención": age_at_attention,
                        "Acompañante": att['acompanante'],
                        "Resumen del Evento": short_summary
                    })
                
                df = pd.DataFrame(summary_data)
                st.dataframe(df, use_container_width=True)
                
                st.metric(label="Número Total de Atenciones Identificadas", value=len(attentions))
                
                # Expansor para ver el detalle de cada atención
                with st.expander("Ver detalle completo de cada atención"):
                    for i, att in enumerate(sorted(attentions, key=lambda x: x['fecha_atencion'])):
                        st.subheader(f"Atención {i+1}: {att['fecha_atencion'].strftime('%d de %B de %Y')}")
                        st.markdown(f"**Acompañante:** {att['acompanante']}")
                        st.text_area("Contenido:", att['contenido'], height=200, key=f"att_content_{i}")

        with tab2:
            st.header("Verificación de Campos Obligatorios (Resolución 1995 de 1999)")
            # La lógica aquí sigue siendo una búsqueda simple, pero es un buen inicio.
            # Una auditoría real necesitaría reglas más complejas.
            campos_clave = {
                "identificación del usuario": ["nombre", "identificacion", "documento"],
                "motivo de consulta": ["motivo de consulta"],
                "enfermedad actual": ["enfermedad actual", "evolucion"],
                "antecedentes": ["antecedentes"],
                "examen físico": ["examen fisico", "examen físico"],
                "diagnóstico": ["diagnostico", "diagnóstico", "dx"],
                "plan de manejo": ["plan de manejo", "tratamiento"]
            }
            
            lower_text = full_text.lower()
            
            cols = st.columns(3)
            col_idx = 0
            for campo, keywords in campos_clave.items():
                if any(keyword in lower_text for keyword in keywords):
                    cols[col_idx].success(f"✔️ {campo.title()}")
                else:
                    cols[col_idx].error(f"❌ {campo.title()} (No encontrado)")
                col_idx = (col_idx + 1) % 3

        with tab3:
            st.header("Búsqueda por Palabra Clave y Texto Completo")
            palabra_clave = st.text_input("Ingresa una palabra o frase para buscar en todo el documento")

            if palabra_clave:
                # Usamos regex para encontrar y resaltar sin ser sensible a mayúsculas/minúsculas
                highlighted_text = re.sub(f"({re.escape(palabra_clave)})", r"<mark>\1</mark>", full_text, flags=re.IGNORECASE)
                st.markdown("---")
                st.subheader("Texto con resultados resaltados:")
            else:
                highlighted_text = full_text
            
            # Usar un componente de markdown para mostrar el texto con scroll
            st.markdown(f"""
            <div style="height:500px;overflow-y:scroll;border:1px solid #ddd;padding:10px;border-radius:5px;">
                {highlighted_text.replace(chr(10), "<br>")}
            </div>
            """, unsafe_allow_html=True)
