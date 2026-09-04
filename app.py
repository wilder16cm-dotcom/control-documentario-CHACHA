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
    st.session_state.doc_seleccionado = None

# 1. Configuración general de la página
st.set_page_config(page_title="Control Documentario - Chachapoyas", layout="wide")

# CSS personalizado para eliminar márgenes y estilizar la línea de tiempo
st.markdown("""
    <style>
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 95%;
    }

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

    .tarjeta-env {
        background-color: #f0f8ff !important;
        padding: 10px;
        border-left: 4px solid #4A90E2;
        border-radius: 4px;
        margin-bottom: 10px;
        -webkit-print-color-adjust: exact;
    }
    .tarjeta-recb {
        background-color: #f4fbf4 !important;
        padding: 10px;
        border-left: 4px solid #50E3C2;
        border-radius: 4px;
        margin-bottom: 10px;
        -webkit-print-color-adjust: exact;
    }
    .asunto-texto {
        font-size: 0.9em;
        color: #333333;
        margin-bottom: 8px;
    }

    /* --- MAGIA CSS PARA AISLAR SOLO LA ZONA DE IMPRESIÓN --- */
    @media print {
        /* Ocultar absolutamente todo lo demás de la página */
        body * {
            visibility: hidden !important;
        }
        /* Mostrar únicamente el contenedor de la izquierda y sus hijos */
        #zona-impresion, #zona-impresion * {
            visibility: visible !important;
        }
        #zona-impresion {
            position: absolute;
            left: 0;
            top: 0;
            width: 100% !important;
        }
        /* Ocultar los botones de "Ver PDF" dentro del reporte impreso para que quede limpio */
        .stButton {
            display: none !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

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
    st.markdown('<div id="zona-impresion">', unsafe_allow_html=True)
    
    col_info_lin, col_btn_print = st.columns([2, 1])
    with col_info_lin:
        st.markdown(f"### Componente: `{componente_seleccionado}`")
    with col_btn_print:
        # Solución limpia sin st.components.v1.html: Usamos un link estilizado como botón con JavaScript nativo
        st.markdown("""
            <div style="text-align: right;">
                <a href="javascript:window.print();" style="
                    display: inline-block;
                    background-color: #ffffff;
                    color: #31333F;
                    border: 1px solid #d0d5dd;
                    padding: 0.45rem 0.75rem;
                    font-weight: 400;
                    border-radius: 0.5rem;
                    text-decoration: none;
                    font-size: 0.9rem;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                ">
                    🖨️ Exportar a PDF
                </a>
            </div>
        """, unsafe_allow_html=True)

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
                            <p class="asunto-texto">{row['ASUNTO']}], row['ASUNTO']</p>
                        </div>
                    """, unsafe_allow_html=True)
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
                        
    st.markdown('</div>', unsafe_allow_html=True)

with col_visor:
    st.subheader("Visor de Documento")
    
    if st.session_state.doc_seleccionado:
        
        nro_orig = str(st.session_state.doc_seleccionado).upper()
        
        # 1. PRIMER FILTRO: Limpieza numérica estricta
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
            resultados = df_nube[df_nube['Nombre'].str.contains(patron_flexible, case=False, regex=True, na=False)]
            
            if not resultados.empty:
                if "RL" in nro_orig:
                    resultados = resultados[resultados['Nombre'].str.contains("RL", case=False, na=False)]
                elif "GV" in nro_orig:
                    resultados = resultados[resultados['Nombre'].str.contains("GV", case=False, na=False)]
                
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
            st.error("No se encontraron archivos en Drive con la numeración y siglas exactas.")

        # ==========================================
        # BUSCADOR MANUAL PERMANENTE (SALVAVIDAS)
        # ==========================================
        st.markdown("---")
        st.markdown("### 🔎 Búsqueda Manual de Respaldo en Drive")
        busqueda_emergencia = st.text_input("Escribe otra palabra clave o número:", key="input_emergencia")
        
        if busqueda_emergencia:
            res_emergencia = df_nube[df_nube['Nombre'].str.contains(busqueda_emergencia, case=False, na=False)]
            if not res_emergencia.empty:
                st.success(f"Se encontraron {len(res_emergencia)} archivos:")
                for idx, r in res_emergencia.iterrows():
                    if st.button(f"📄 Abrir: {r['Nombre']}", key=f"emer_{idx}"):
                        st.session_state.pdf_actual = r['URL']
                        st.rerun()
            else:
                st.warning("No se encontraron archivos con ese término en Drive.")
            
        if st.button("❌ Cerrar Panel"):
            st.session_state.pdf_actual = None
            st.session_state.doc_seleccionado = None
            st.rerun()
            
    else:
        st.info("👈 Selecciona 'Ver PDF' en la línea de tiempo o usa este buscador libre para explorar todos los archivos en Drive:")
        
        busqueda_libre_drive = st.text_input("🔍 Buscador general en Drive:", placeholder="Escribe número, palabra clave o contratista...")
        
        if busqueda_libre_drive:
            resultados_libres = df_nube[df_nube['Nombre'].str.contains(busqueda_libre_drive, case=False, na=False)]
            
            if not resultados_libres.empty:
                st.success(f"Se encontraron {len(resultados_libres)} archivos:")
                for idx, r in resultados_libres.iterrows():
                    if st.button(f"📄 Abrir: {r['Nombre']}", key=f"libre_drive_{idx}"):
                        st.session_state.pdf_actual = r['URL']
                        st.rerun()
            else:
                st.warning("No se encontraron archivos en Drive con ese término.")