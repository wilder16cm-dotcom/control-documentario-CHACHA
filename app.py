import streamlit as st
import sqlite3
import pandas as pd
import base64
import os
import re

# Inicializar variables de estado
if 'pdf_actual' not in st.session_state:
    st.session_state.pdf_actual = None
if 'doc_seleccionado' not in st.session_state:
    st.session_state.doc_seleccionado = None # NUEVO: Guarda el nombre de la carta al hacer clic

# 1. Configuración general de la página
st.set_page_config(page_title="Control Documentario - Chachapoyas", layout="wide")

# CSS personalizado para eliminar márgenes y estilizar la línea de tiempo
st.markdown("""
    <style>
    /* Ocultar el header predeterminado de Streamlit */
    header {visibility: hidden;}
    
    /* ELIMINAR EL ESPACIO BLANCO SUPERIOR */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 95%;
    }

    /* Estilos para el eje central */
    .eje-contenedor {
        display: flex;
        flex-direction: column;
        align-items: center;
        height: 100%;
        position: relative;
    }
    .fecha-eje { 
        text-align: center; 
        font-weight: bold; 
        color: #555555; 
        font-size: 0.85em; 
        background-color: #f0f2f6;
        padding: 4px 8px;
        border-radius: 12px;
        z-index: 2;
        margin-bottom: 5px;
    }
    .linea-vertical {
        width: 2px;
        background-color: #d3d3d3;
        flex-grow: 1;
        min-height: 40px;
        z-index: 1;
    }
    .punto-nodo {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background-color: #a0a0a0;
        z-index: 2;
        margin-top: -5px;
        margin-bottom: 5px;
    }

    /* Colores para tarjetas */
    .tarjeta-env {
        background-color: #f0f8ff;
        padding: 10px;
        border-left: 4px solid #4A90E2;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .tarjeta-recb {
        background-color: #f4fbf4;
        padding: 10px;
        border-left: 4px solid #50E3C2;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .asunto-texto {
        font-size: 0.9em;
        color: #333333;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar variable de estado para mantener el PDF abierto
if 'pdf_actual' not in st.session_state:
    st.session_state.pdf_actual = None

# ==========================================
# CARGA DE DATOS (Base de datos y Drive)
# ==========================================
@st.cache_data
def cargar_datos():
    conn = sqlite3.connect('proyecto_selva.db')
    query = "SELECT * FROM control_documentario ORDER BY FECHA_DOC ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['FECHA_STR'] = pd.to_datetime(df['FECHA_DOC']).dt.strftime('%d/%m/%Y')
    return df

@st.cache_data
def cargar_links_nube():
    try:
        return pd.read_excel('links_completos.xlsx')
    except:
        return pd.DataFrame(columns=['Nombre', 'URL'])

df = cargar_datos()
df_nube = cargar_links_nube()

# ==========================================
# ENCABEZADO SUPERIOR
# ==========================================
col_titulo, col_buscador, col_filtro = st.columns([1.5, 2, 1])

with col_titulo:
    st.markdown("<h3 style='margin-top: 0px;'>Control Documentario - Chachapoyas</h3>", unsafe_allow_html=True)

with col_buscador:
    texto_busqueda = st.text_input("🔍 Buscar N° o asunto...", label_visibility="collapsed", placeholder="🔍 Buscar en registros...")

with col_filtro:
    lista_componentes = df['COMPONENTE'].dropna().unique().tolist()
    componente_seleccionado = st.selectbox("Filtro", ["Todos"] + lista_componentes, label_visibility="collapsed")

# Filtrado de la base de datos local
df_filtrado = df
if componente_seleccionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['COMPONENTE'] == componente_seleccionado]
if texto_busqueda:
    df_filtrado = df_filtrado[
        df_filtrado['ASUNTO'].str.contains(texto_busqueda, case=False, na=False) |
        df_filtrado['NRO_DOC'].str.contains(texto_busqueda, case=False, na=False)
    ]

# ==========================================
# FUNCIÓN DEL VISOR
# ==========================================
def mostrar_pdf(ruta_archivo):
    if pd.notna(ruta_archivo) and str(ruta_archivo).strip() != "":
        ruta_str = str(ruta_archivo).strip()
        
        if ruta_str.startswith("http"):
            pdf_display = f'<iframe src="{ruta_str}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        elif os.path.exists(ruta_str):
            try:
                with open(ruta_str, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error de lectura: {e}")
        else:
            st.error(f"El archivo no se encuentra: {ruta_str}")
    else:
        st.error("Este registro no tiene ningún documento vinculado en la base de datos.")

st.divider()

# ==========================================
# ESTRUCTURA PRINCIPAL (Línea de tiempo y Visor)
# ==========================================
col_timeline, col_visor = st.columns([1.5, 2]) 

with col_timeline:
    h_env, h_eje, h_recb = st.columns([3, 1, 3])
    h_env.markdown("<h4 style='text-align: center; color: #4A90E2;'>Enviadas</h4>", unsafe_allow_html=True)
    h_recb.markdown("<h4 style='text-align: center; color: #50E3C2;'>Recibidas</h4>", unsafe_allow_html=True)
    
    with st.container(height=800):
        for index, row in df_filtrado.iterrows():
            c_env, c_eje, c_recb = st.columns([3, 1, 3])
            
            with c_eje:
                st.markdown(f"""
                    <div class='eje-contenedor'>
                        <div class='fecha-eje'>{row['FECHA_STR']}</div>
                        <div class='punto-nodo'></div>
                        <div class='linea-vertical'></div>
                    </div>
                """, unsafe_allow_html=True)
            
            origen = str(row.get('ORIGEN_DOC', '')).upper()
            
            if 'ENV' in origen:
                with c_env:
                    st.markdown(f"""
                        <div class="tarjeta-env">
                            <strong>✉️ {row['NRO_DOC']}</strong>
                            <p class="asunto-texto">{row['ASUNTO']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    # Al hacer clic, guarda tanto el link como el número de documento
                    if st.button("Ver PDF", key=f"btn_env_{row['ID_REGISTRO']}", use_container_width=True):
                        st.session_state.pdf_actual = row.get('ARCHIVO_PDF')
                        st.session_state.doc_seleccionado = row.get('NRO_DOC')
            else:
                with c_recb:
                    st.markdown(f"""
                        <div class="tarjeta-recb">
                            <strong>📥 {row['NRO_DOC']}</strong>
                            <p class="asunto-texto">{row['ASUNTO']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("Ver PDF", key=f"btn_recb_{row['ID_REGISTRO']}", use_container_width=True):
                        st.session_state.pdf_actual = row.get('ARCHIVO_PDF')
                        st.session_state.doc_seleccionado = row.get('NRO_DOC')

with col_visor:
    st.subheader("Visor de Documento")
    
    if st.session_state.doc_seleccionado:
        
        nro_orig = str(st.session_state.doc_seleccionado).upper()
        
        # 1. PRIMER FILTRO: Limpieza numérica estricta (El ADN matemático)
        match_estricto = re.search(r'0*(\d+)\s*[-/]?\s*(2025|2026)', nro_orig)
        
        if match_estricto:
            num_base = match_estricto.group(1) 
            year_base = match_estricto.group(2)
            patron_flexible = fr'(?<!\d)0*{num_base}(?!\d)[\s\-_]*{year_base}'
            nro_limpio = f"{num_base}-{year_base}"
        else:
            match_suelto = re.search(r'(?:0*)(\d+.*)', nro_orig)
            nro_limpio = match_suelto.group(1).split('/')[0].strip() if match_suelto else nro_orig
            patron_flexible = re.sub(r'[\s\-]+', '.*', nro_limpio)

        if pd.notna(st.session_state.pdf_actual) and str(st.session_state.pdf_actual).strip() != "":
            mostrar_pdf(st.session_state.pdf_actual)
        else:
            st.warning("⚠️ La base de datos no tiene un enlace asignado. Usando búsqueda en Drive...")

        st.markdown("---")
        st.markdown(f"### 🔍 Coincidencias exactas en Drive para: `{nro_limpio}`")
        
        try:
            # Aplicamos la búsqueda por número y año
            resultados = df_nube[df_nube['Nombre'].str.contains(patron_flexible, case=False, regex=True, na=False)]
            
            # 2. SEGUNDO FILTRO: Palabras Clave (El francotirador)
            if not resultados.empty:
                # Si es una carta enviada de tipo RL
                if "RL" in nro_orig:
                    resultados = resultados[resultados['Nombre'].str.contains("RL", case=False, na=False)]
                # Si es una carta enviada de tipo GV
                elif "GV" in nro_orig:
                    resultados = resultados[resultados['Nombre'].str.contains("GV", case=False, na=False)]
                
                # Si es un documento recibido (o enviado) que involucra al MTC
                if "MTC" in nro_orig:
                    resultados = resultados[resultados['Nombre'].str.contains("MTC", case=False, na=False)]
                    
        except:
            resultados = pd.DataFrame()
            
        if not resultados.empty:
            for idx, r in resultados.iterrows():
                if st.button(f"📄 Abrir: {r['Nombre']}", key=f"auto_{idx}"):
                    st.session_state.pdf_actual = r['URL']
                    st.rerun()
        else:
            st.error("No se encontraron archivos en Drive que cumplan con la numeración y las siglas exactas (GV, RL, MTC).")
            
        if st.button("❌ Cerrar Panel"):
            st.session_state.pdf_actual = None
            st.session_state.doc_seleccionado = None
            st.rerun()
            
    else:
        st.info("👈 Selecciona 'Ver PDF' en la línea de tiempo para buscar o leer el documento.")