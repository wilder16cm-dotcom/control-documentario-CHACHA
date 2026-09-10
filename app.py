import streamlit as st
import sqlite3
import pandas as pd
import base64
import os

if 'pdf_actual' not in st.session_state:
    st.session_state.pdf_actual = None
if 'doc_seleccionado' not in st.session_state:
    st.session_state.doc_seleccionado = None

st.set_page_config(page_title="Control Documentario - CHACHA", layout="wide")

# ==========================================
# CSS: ESTILO SAAS CORPORATIVO + HITOS
# ==========================================
st.markdown("""
    <style>
    header {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 95%; }
    
    #zona-impresion { background-color: #FFFFFF; padding: 10px; }
    .eje-contenedor { display: flex; flex-direction: column; align-items: center; height: 100%; position: relative; }
    
    .fecha-eje { text-align: center; font-weight: 600; color: #475569; font-size: 0.8rem; background-color: #F1F5F9; padding: 4px 10px; border-radius: 12px; border: 1px solid #E2E8F0; z-index: 2; margin-bottom: 5px; }
    .linea-vertical { width: 2px; background-color: #E2E8F0; flex-grow: 1; min-height: 40px; z-index: 1; }
    .punto-nodo { width: 10px; height: 10px; border-radius: 50%; background-color: #94A3B8; z-index: 2; margin-top: -5px; margin-bottom: 5px; }
    
    .fecha-hito { background-color: #EF4444 !important; color: #FFFFFF !important; border-color: #EF4444 !important; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2); }
    .nodo-hito { background-color: #DC2626 !important; border: 2px solid #FEF2F2 !important; width: 12px; height: 12px; }
    
    .tarjeta-env { background-color: #F0F7FF !important; border: 1px solid #E2E8F0; border-left: 4px solid #2563EB; padding: 14px; border-radius: 6px; margin-bottom: 8px; -webkit-print-color-adjust: exact; }
    .tarjeta-recb { background-color: #ECFDF5 !important; border: 1px solid #E2E8F0; border-left: 4px solid #059669; padding: 14px; border-radius: 6px; margin-bottom: 8px; -webkit-print-color-adjust: exact; }
    
    /* NUEVA CLASE: Tarjeta de Hito a pantalla completa */
    .tarjeta-hito-full { 
        background-color: #FEF2F2 !important; 
        border: 1px solid #FCA5A5; 
        border-left: 6px solid #EF4444; 
        border-right: 6px solid #EF4444; 
        padding: 12px; 
        border-radius: 8px; 
        margin-top: 5px;
        margin-bottom: 20px; 
        text-align: center;
        box-shadow: 0 2px 4px rgba(239, 68, 68, 0.05);
        -webkit-print-color-adjust: exact; 
    }
    
    .asunto-texto { font-size: 0.85em; color: #334155 !important; margin-top: 8px; margin-bottom: 0px; line-height: 1.4; }
    .asunto-hito { color: #991B1B !important; font-weight: 500; display: block; margin-top: 5px; font-size: 0.9em; }
    .expediente-texto { font-size: 0.75em; color: #475569; background-color: #E2E8F0; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-top: 6px; font-weight: 500; }
    
    div[data-testid="stButton"] > button { border-radius: 4px; border: 1px solid #CBD5E1; background-color: #FFFFFF; color: #475569; padding: 2px 10px; }
    
    @media print {
        body * { visibility: hidden !important; }
        #zona-impresion, #zona-impresion * { visibility: visible !important; }
        #zona-impresion { position: absolute; left: 0; top: 0; width: 100% !important; }
        .stButton, .stDownloadButton { display: none !important; }
    }
    </style>
""", unsafe_allow_html=True)
# ==========================================
# CARGA DE DATOS
# ==========================================
@st.cache_data
def cargar_datos():
    conn = sqlite3.connect('db_elite.db')
    query = "SELECT * FROM control_documentario ORDER BY FECHA_DOC ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df['FECHA_STR'] = pd.to_datetime(df['FECHA_DOC']).dt.strftime('%d/%m/%Y')
    
    if 'NRO_EXPENDIENTE' in df.columns:
        df['NRO_EXPENDIENTE'] = df['NRO_EXPENDIENTE'].fillna("").astype(str).str.strip()
        df['NRO_EXPENDIENTE'] = df['NRO_EXPENDIENTE'].apply(lambda x: "" if x.lower() in ["none", "nan", ""] else x)
    else:
        df['NRO_EXPENDIENTE'] = ""
        
    return df

@st.cache_data
def cargar_links_nube():
    try:
        df_n = pd.read_excel('links_completos.xlsx')
        if 'Carpeta' not in df_n.columns:
            df_n['Carpeta'] = ""
        return df_n
    except:
        return pd.DataFrame(columns=['Nombre', 'URL', 'Carpeta'])

df = cargar_datos()
df_nube = cargar_links_nube()

# ==========================================
# ENCABEZADO Y FILTROS DINÁMICOS
# ==========================================
col_titulo, col_busq, col_comp, col_ent = st.columns([1.5, 1.5, 1, 1.2])

with col_titulo:
    st.markdown("<h3 style='margin-top: 25px;'>Control Documentario - CHACHA</h3>", unsafe_allow_html=True)

with col_busq:
    texto_busqueda = st.text_input("Buscador", placeholder="N° Documento o Asunto...")

with col_comp:
    lista_componentes = df['COMPONENTE'].dropna().unique().tolist()
    componente_seleccionado = st.selectbox("Componente", ["Todos"] + lista_componentes)

# Lógica dinámica: Mostrar entregables solo del componente seleccionado
df_filtrado = df if componente_seleccionado == "Todos" else df[df['COMPONENTE'] == componente_seleccionado]

with col_ent:
    if 'ENTREGABLE' in df.columns:
        lista_entregables = df_filtrado['ENTREGABLE'].dropna().unique().tolist()
        entregable_seleccionado = st.selectbox("Entregable", ["Todos"] + lista_entregables)
    else:
        entregable_seleccionado = "Todos"

# Aplicar filtros al DataFrame final
if entregable_seleccionado != "Todos" and 'ENTREGABLE' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['ENTREGABLE'] == entregable_seleccionado]
if texto_busqueda:
    df_filtrado = df_filtrado[
        df_filtrado['ASUNTO'].str.contains(texto_busqueda, case=False, na=False) |
        df_filtrado['NRO_DOC'].str.contains(texto_busqueda, case=False, na=False)
    ]

# ==========================================
# FUNCIÓN DEL VISOR DE PDF
# ==========================================
def mostrar_pdf(ruta_archivo):
    if pd.notna(ruta_archivo) and str(ruta_archivo).strip() != "":
        ruta_str = str(ruta_archivo).strip()
        if ruta_str.startswith("http"):
            if "drive.google.com" in ruta_str and "/view" in ruta_str:
                ruta_str = ruta_str.split("/view")[0] + "/preview"
            pdf_display = f'<iframe src="{ruta_str}" width="100%" height="800" type="application/pdf" style="border: none;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        elif os.path.exists(ruta_str):
            try:
                with open(ruta_str, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf" style="border: none;"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()

# ==========================================
# LÍNEA DE TIEMPO (IZQUIERDA)
# ==========================================
col_timeline, col_visor = st.columns([1.5, 2]) 

col_timeline, col_visor = st.columns([1.5, 2]) 

with col_timeline:
    st.markdown('<div id="zona-impresion">', unsafe_allow_html=True)
    
    # Texto limpio sin botón de impresión
    comp_texto = componente_seleccionado if componente_seleccionado != "Todos" else "General"
    ent_texto = f" > {entregable_seleccionado}" if entregable_seleccionado != "Todos" else ""
    st.markdown(f"**Línea de Tiempo:** `{comp_texto}{ent_texto}`")
    st.write("") # Un pequeño espacio en blanco visual

    h_env, h_eje, h_recb = st.columns([3, 1, 3])
    h_env.markdown("<h5 style='text-align: center; color: #2563EB;'>Enviadas</h5>", unsafe_allow_html=True)
    h_recb.markdown("<h5 style='text-align: center; color: #059669;'>Recibidas</h5>", unsafe_allow_html=True)
    
    with st.container(height=800):
        for index, row in df_filtrado.iterrows():
            # 1. Limpiamos las variables (Acá matamos el 'nan' de Pandas)
            tipo_evento = str(row.get('TIPO_EVENTO', '')).upper()
            es_hito = "HITO" in tipo_evento
            
            asunto_raw = str(row.get('ASUNTO', '')).strip()
            # Si el texto es 'nan', 'none' o está vacío, lo convertimos en un string vacío real ""
            asunto = "" if asunto_raw.lower() in ['nan', 'none', ''] else asunto_raw
            
            origen = str(row.get('ORIGEN_DOC', '')).upper()
            nro_doc = str(row.get('NRO_DOC', ''))
            
            exp_raw = str(row.get('NRO_EXPENDIENTE', '')).strip()
            expediente = "" if exp_raw.lower() in ['nan', 'none', ''] else exp_raw
            html_exp = f"<div class='expediente-texto'>📁 Exp: {expediente}</div>" if expediente else ""
            
            # 2. Renderizamos el eje central primero
            c_env, c_eje, c_recb = st.columns([3, 1, 3])
            
            with c_eje:
                if es_hito:
                    st.markdown(f"<div class='eje-contenedor'><div class='fecha-eje fecha-hito'>{row['FECHA_STR']}</div><div class='punto-nodo nodo-hito'></div><div class='linea-vertical'></div></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='eje-contenedor'><div class='fecha-eje'>{row['FECHA_STR']}</div><div class='punto-nodo'></div><div class='linea-vertical'></div></div>", unsafe_allow_html=True)
            
            # 3. Renderizamos las Tarjetas (Verticales)
            if es_hito:
                html_asunto = f"<span class='asunto-hito'>{asunto}</span>" if asunto else ""
                st.markdown(f"<div class='tarjeta-hito-full'><strong>🎯 {nro_doc}</strong><br>{html_asunto}</div>", unsafe_allow_html=True)
            else:
                # Asegurar captura del expediente saltando errores de NaN
                exp_raw = str(row.get('NRO_EXPENDIENTE', '')).strip()
                expediente = "" if exp_raw.lower() in ['nan', 'none', 'nat', ''] else exp_raw
                
                # HTML con estilo en línea por si la clase CSS se borró accidentalmente
                html_exp = f"<div style='font-size: 0.75em; color: #475569; background-color: #E2E8F0; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-top: 6px; margin-bottom: 2px; font-weight: 600;'>📁 Exp: {expediente}</div>" if expediente else ""
                
                if 'ENV' in origen:
                    with c_env:
                        st.markdown(f"<div class='tarjeta-env'><strong>✉️ {nro_doc}</strong><br>{html_exp}<div class='asunto-texto'>{asunto}</div></div>", unsafe_allow_html=True)
                        if st.button("Ver PDF", key=f"btn_env_{row['ID_REGISTRO']}", use_container_width=True):
                            st.session_state.doc_seleccionado = nro_doc.strip()
                            st.session_state.pdf_actual = "BUSCAR_PRINCIPAL" 
                else:
                    with c_recb:
                        st.markdown(f"<div class='tarjeta-recb'><strong>📥 {nro_doc}</strong><br>{html_exp}<div class='asunto-texto'>{asunto}</div></div>", unsafe_allow_html=True)
                        if st.button("Ver PDF", key=f"btn_recb_{row['ID_REGISTRO']}", use_container_width=True):
                            st.session_state.doc_seleccionado = nro_doc.strip()
                            st.session_state.pdf_actual = "BUSCAR_PRINCIPAL"
                        
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# VISOR Y LÓGICA DE CARPETAS (DERECHA)
# ==========================================
with col_visor:
    if st.session_state.doc_seleccionado:
        st.subheader("Visor de Documento")
        nro_doc = st.session_state.doc_seleccionado
        nombre_pdf_esperado = f"{nro_doc}.pdf".upper()
        
        match_principal = df_nube[
            (df_nube['Nombre'].str.strip().str.upper() == nombre_pdf_esperado) | 
            (df_nube['Nombre'].str.strip().str.upper() == nro_doc.upper())
        ]
        
        url_principal = None
        if not match_principal.empty:
            url_principal = match_principal.iloc[0]['URL']
            if st.session_state.pdf_actual == "BUSCAR_PRINCIPAL":
                st.session_state.pdf_actual = url_principal
            mostrar_pdf(st.session_state.pdf_actual)
        else:
            st.warning(f"⚠️ No se encontró el archivo principal en Drive para `{nro_doc}`")
            
        st.markdown("---")
        
        anexos = df_nube[
            (df_nube['Carpeta'].str.strip().str.upper() == nro_doc.upper()) & 
            (df_nube['Nombre'].str.strip().str.upper() != nombre_pdf_esperado) &
            (df_nube['Nombre'].str.strip().str.upper() != nro_doc.upper())
        ]
        
        if not anexos.empty:
            st.markdown(f"### 📎 Anexos encontrados ({len(anexos)}):")
            if url_principal:
                if st.button("🏠 Ver Documento Principal", type="primary", use_container_width=True):
                    st.session_state.pdf_actual = url_principal
                    st.rerun()
            for idx, anexo in anexos.iterrows():
                if st.button(f"📄 {anexo['Nombre']}", key=f"anx_{idx}", use_container_width=True):
                    st.session_state.pdf_actual = anexo['URL']
                    st.rerun()
        else:
            st.info("No se encontraron anexos para este documento.")
            
        if st.button("❌ Cerrar Visor"):
            st.session_state.pdf_actual = None
            st.session_state.doc_seleccionado = None
            st.rerun()
    else:
        st.info("👈 Selecciona 'Ver PDF' en la línea de tiempo para leer un documento.")

# ==========================================
# PANORAMA HORIZONTAL (LÍNEA DE TIEMPO INTERACTIVA)
# ==========================================
import plotly.graph_objects as go

st.divider()
st.subheader("Panorama General: Hitos y Flujo Documentario")

if not df_filtrado.empty:
    df_plot = df_filtrado.copy()
    df_plot['FECHA_DT'] = pd.to_datetime(df_plot['FECHA_DOC'])
    
    # Función para limpiar y acortar el asunto para que no sature la gráfica
    def limpiar_asunto(texto):
        t = str(texto).strip()
        if t.lower() in ['nan', 'none', '']:
            return ""
        return t[:40] + "..." if len(t) > 40 else t

    fig = go.Figure()

    # 1. Trazar el Eje central horizontal grueso
    fig.add_hline(y=0, line_width=4, line_color="#CBD5E1")

    # Variables para alternar las alturas y evitar choques
    env_nivel = 1
    rec_nivel = 1
    
    colores_nodos = []

    # 2. Construir las "Etiquetas" con tallo incorporado
    for index, row in df_plot.iterrows():
        tipo = str(row.get('TIPO_EVENTO', '')).upper()
        origen = str(row.get('ORIGEN_DOC', '')).upper()
        asunto_limpio = limpiar_asunto(row.get('ASUNTO', ''))
        
        # Limpieza del expediente (evitar los nan de pandas)
        exp_raw = str(row.get('NRO_EXPENDIENTE', '')).strip()
        expediente = "" if exp_raw.lower() in ['nan', 'none', ''] else exp_raw
        
        # Jerarquía visual usando HTML
        texto_etiqueta = f"<b>{row['NRO_DOC']}</b>"
        
        # Si existe un expediente, lo agregamos justo debajo del documento
        if expediente:
            texto_etiqueta += f"<br><span style='font-size:10.5px; color:#475569;'>📁 Exp: {expediente}</span>"
            
        # Finalmente el asunto cortado
        if asunto_limpio:
            texto_etiqueta += f"<br><span style='font-size:9.5px; color:#64748B;'>{asunto_limpio}</span>"

        # Lógica de niveles y colores
        if "HITO" in tipo:
            ay_offset = -40 
            color = "#EF4444"
        elif 'ENV' in origen:
            ay_offset = -70 * env_nivel 
            color = "#2563EB"
            env_nivel = env_nivel + 1 if env_nivel < 3 else 1 
        else:
            ay_offset = 70 * rec_nivel  
            color = "#059669"
            rec_nivel = rec_nivel + 1 if rec_nivel < 3 else 1 
            
        colores_nodos.append(color)

        # Plotly Annotations: Creación de la etiqueta
        fig.add_annotation(
            x=row['FECHA_DT'], 
            y=0,
            text=texto_etiqueta,
            showarrow=True, 
            arrowhead=0, 
            arrowwidth=2, 
            arrowcolor=color,
            ax=0, 
            ay=ay_offset, 
            bgcolor="rgba(255,255,255,0.95)", 
            bordercolor=color, 
            borderwidth=1.5, 
            borderpad=6,
            font=dict(size=12, color="#1E293B")
        )

    # 3. Trazar los Nodos (los círculos sobre la línea)
    fig.add_trace(go.Scatter(
        x=df_plot['FECHA_DT'],
        y=[0] * len(df_plot), # Todos los puntos en el eje 0
        mode='markers',
        marker=dict(size=14, color=colores_nodos, line=dict(width=2, color='white')),
        hoverinfo='text',
        hovertext="<b>" + df_plot['FECHA_STR'] + "</b><br>" + df_plot['ASUNTO'] # Al pasar el mouse muestra todo sin cortar
    ))

    # 4. Configurar el lienzo (Scroll y limpieza visual)
    fig.update_layout(
        height=650, # Más alto para que respiren las etiquetas
        showlegend=False,
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickformat="%d %b\n%Y",  # Día, Mes y Año en 2 líneas
            tickfont=dict(size=12, color="#475569", weight="bold")
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-1, 1] # Congela el eje Y para que todo el espacio lo manejen los pixeles
        ),
        hoverlabel=dict(bgcolor="white", font_size=13, bordercolor="#CBD5E1")
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos para mostrar en el panorama general con los filtros actuales.")