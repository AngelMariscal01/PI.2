import streamlit as st # streamlit package
import numpy as np
import pandas as pd
from millify import millify # shortens values (10_000 ---> 10k)
from streamlit_extras.metric_cards import style_metric_cards # beautify metric card with css
import plotly.graph_objects as go
import altair as alt 

# Cargar datos y caché
@st.cache_data
def load_data():
    df = pd.read_csv('./data/Final.csv')  # Reemplazar con la ruta correcta
    df['FECHA_y'] = pd.to_datetime(df['FECHA_y'])
    return df
st.set_page_config(layout="wide", page_title="Dashboard de Accidentes Viales en CABA")

# Cargar datos
try:
    df = load_data()

    # Filtros Interactivos
    st.sidebar.header('Filtros')
    poblacion_caba = st.sidebar.number_input('Ingrese un número entero', min_value=0, max_value=5000000, value=3000000, step=1)
    st.sidebar.write(f'Número de la población: {poblacion_caba}')
    
    # Añadir opción "Todos los años"
    anios = df['AAAA_y'].unique().tolist()
    anios.insert(0, "Todos los años")
    anio = st.sidebar.selectbox("Seleccione el año actual a analizar", anios)
    anioPasado = None if anio == "Todos los años" else int(anio) - 1
    
    end_date = st.sidebar.date_input("Fecha de fin", value=pd.to_datetime(df['FECHA_y'].max()))
    end_date = pd.to_datetime(end_date)  # Convertir end_date a datetime64[ns]
    
    tipo_calle = st.sidebar.multiselect('Tipo de Calle', options=df['TIPO_DE_CALLE'].unique(), default=df['TIPO_DE_CALLE'].unique())
    comuna = st.sidebar.multiselect('Comuna', options=df['COMUNA'].unique(), default=df['COMUNA'].unique())
    rol = st.sidebar.multiselect('Rol', options=df['ROL'].unique(), default=df['ROL'].unique())
    sexo = st.sidebar.radio('Sexo', options=['AMBOS', 'MASCULINO', 'FEMENINO'], index=0)



    # Aplicar Filtros
    df_filtered = df[(df['TIPO_DE_CALLE'].isin(tipo_calle)) &
                     (df['COMUNA'].isin(comuna)) &
                     (df['ROL'].isin(rol))]
    if sexo != 'AMBOS':
        df_filtered = df_filtered[df_filtered['SEXO'] == sexo]
    # Filtrar por año si no se selecciona "Todos los años"
    if anio != "Todos los años":
        df_filtered = df_filtered[df_filtered['AAAA_y'] == int(anio)]
    
    # Funciones para el cálculo de KPIs
    def calcular_tasa_victimas(df, poblacion):
        homicidios = df.shape[0]
        tasa = (homicidios / poblacion) * 100000
        return round(tasa, 2)

    def filtrar_por_periodo(df, start_date, end_date):
        return df[(df['FECHA_y'] >= start_date) & (df['FECHA_y'] < end_date)]

    def calcular_tasa_accidentes_victimas(df, poblacion):
        accidentes = df[df['VICTIMA_y'].notnull()].shape[0]
        tasa = (accidentes / poblacion) * 1000
        return round(tasa, 2)

    def kpi_tasa_victimas_viales(df):
        start_date_ultimo_semestre = end_date - pd.DateOffset(months=6)
        start_date_semestre_anterior = start_date_ultimo_semestre - pd.DateOffset(months=6)
        ultimo_semestre = filtrar_por_periodo(df, start_date_ultimo_semestre, end_date)
        semestre_anterior = filtrar_por_periodo(df, start_date_semestre_anterior, start_date_ultimo_semestre)
        # Calcular las tasas de homicidios en siniestros viales
        tasa_ultimo_semestre = calcular_tasa_victimas(ultimo_semestre, poblacion_caba)
        tasa_semestre_anterior = calcular_tasa_victimas(semestre_anterior, poblacion_caba)
        if tasa_semestre_anterior != 0:
            reduccion_lograda = round(((tasa_semestre_anterior - tasa_ultimo_semestre) / tasa_semestre_anterior) * 100, 2)
        else:
            reduccion_lograda = 0
        return [tasa_ultimo_semestre, reduccion_lograda]

    def kpi_evolucion_cantidad_vitimas_en_moto(df):
        df_moto = df[df['VICTIMA_y'] == 'MOTO']
        accidentes_por_ano = df_moto[df_moto['VICTIMA_y'].notnull()].groupby(df_moto['FECHA_y'].dt.year).size()
        accidentes_a = accidentes_por_ano.get(anioPasado, 0) if anioPasado else 0
        accidentes_b = accidentes_por_ano.get(int(anio), 0) if anio != "Todos los años" else accidentes_por_ano.sum()
        reduccion_accidentes_moto = round(((accidentes_a - accidentes_b) / accidentes_a) * 100, 2) if accidentes_a != 0 else 0
        return reduccion_accidentes_moto

    def kpi_evolucion_accidentes_en_avenidas(df):
        df_avenidas = df[df['TIPO_DE_CALLE'] == 'AVENIDA']
        accidentes_avenidas_por_ano = df_avenidas[df_avenidas['VICTIMA_y'].notnull()].groupby(df_avenidas['FECHA_y'].dt.year).size()
        ultimo_ano = accidentes_avenidas_por_ano.get(int(anio), 0) if anio != "Todos los años" else accidentes_avenidas_por_ano.sum()
        penultimo_ano = accidentes_avenidas_por_ano.get(anioPasado, 0) if anioPasado else 0
        tasa_accidentes_ultimo_ano = round((ultimo_ano / poblacion_caba) * 1000, 4)
        tasa_accidentes_penultimo_ano = round((penultimo_ano / poblacion_caba) * 1000, 4)
        if tasa_accidentes_penultimo_ano != 0:
            reduccion_lograda = round(((tasa_accidentes_penultimo_ano - tasa_accidentes_ultimo_ano) / tasa_accidentes_penultimo_ano) * 100, 2)
        else:
            reduccion_lograda = 0
        return [tasa_accidentes_ultimo_ano, reduccion_lograda]

    # Calcular los KPIs
    kpi1 = kpi_tasa_victimas_viales(df)
    kpi2 = kpi_evolucion_cantidad_vitimas_en_moto(df)
    kpi3 = kpi_evolucion_accidentes_en_avenidas(df)

    # Mostrar objetivos de los KPIs
    st.markdown("""
    ### Objetivos de los KPIs
    - **Reducir en un 10% la tasa de victimas en siniestros viales de los últimos seis meses, en CABA, en comparación con la tasa de homicidios en siniestros viales del semestre anterior.**
    - **Reducir en un 7% la cantidad de accidentes mortales de motociclistas en el último año, en CABA, respecto al año anterior.**
    - **Reducir en un 5% la tasa de accidentes con víctimas en avenidas en el último año en comparación con el año anterior.**
    """)

    dash_1 = st.container()
    with dash_1:
        # Mostrar métricas en un cuadro separado
        st.header("KPIs de Accidentes Viales en CABA")

    dash_2 = st.container()
    with dash_2:
        col1, col2 = st.columns(2)

        with col1:
            st.metric(label="Tasa de victimas en siniestros viales",value=kpi1[0], delta=kpi1[1])
            st.metric('Evolución de accidentes mortales de motociclistas (%)', f'{kpi2:.2f}%')
        with col2:
            st.metric(label='Tasa de accidentes en avenidas por cada 1000 habitantes por año', value=kpi3[0], delta = kpi3[1])

    style_metric_cards(border_left_color = "#8673a1",background_color="#231a24")
    # Visualizaciones de Datos
    st.subheader('DASHBOARD')

    dash_3 = st.container()
    with dash_3:
        accidentes_por_tipo = df_filtered['TIPO_DE_CALLE'].value_counts().reset_index()
        accidentes_por_tipo.columns = ['TIPO_DE_CALLE', 'Cantidad']

        col1, col2 = st.columns(2)

        with col1:
            chart = alt.Chart(accidentes_por_tipo).mark_bar(opacity=0.9, color="#483D8B").encode(
                x=alt.X('Cantidad:Q', title='Cantidad de Accidentes'),
                y=alt.Y('TIPO_DE_CALLE:N', sort='-x', title='Tipo de Calle')
            )
            chart = chart.properties(title="Cantidad de Accidentes por Tipo de Calle")
            st.altair_chart(chart, use_container_width=True)

        muertes_por_tipo = df_filtered['VICTIMA_y'].value_counts().reset_index()
        muertes_por_tipo.columns = ['VEHICULO_VICTIMA', 'Cantidad']
        max_tipo = muertes_por_tipo.iloc[0]['VEHICULO_VICTIMA']
        with col2:
            chart_pie = alt.Chart(muertes_por_tipo).mark_arc(opacity=0.9).encode(
                theta=alt.Theta(field='Cantidad', type='quantitative'),
                color=alt.Color(field='VEHICULO_VICTIMA', type='nominal', scale=alt.Scale(
                    domain=muertes_por_tipo['VEHICULO_VICTIMA'].tolist(),
                    range=['#4B0082', '#483D8B', '#6A5ACD', '#7B68EE', '#9370DB', '#8A2BE2', '#9400D3']  # Colores más oscuros
                )),
                opacity=alt.condition(
                    alt.datum.VEHICULO_VICTIMA == max_tipo,
                    alt.value(1.0),
                    alt.value(0.5)
                ),
                tooltip=['VEHICULO_VICTIMA', 'Cantidad']
            ).properties(
                title='Cantidad de Accidentes por Vehículo de la Víctima'
            )

            st.altair_chart(chart_pie, use_container_width=True)
    
        # Gráfico de líneas: Histórico de edades de las víctimas
    # Gráfico de distribución de edades de las víctimas
    st.markdown('#### Distribución de Edades de las Víctimas')
    histograma_edades = alt.Chart(df_filtered).mark_bar(opacity=0.9, color="#483D8B").encode(
        alt.X('EDAD:Q', bin=True, title='Edad'),
        alt.Y('count()', title='Número de Víctimas')
    ).properties(
        title='Distribución de Edades de las Víctimas en Accidentes'
    )

    st.altair_chart(histograma_edades, use_container_width=True)
    # Mapa: Accidentes geolocalizados
    st.markdown('#### Mapa de Accidentes')
    df_filtered_map = df_filtered.rename(columns={'pos y': 'lat', 'pos x': 'lon'})
    st.map(df_filtered_map[['lat', 'lon']].dropna(how="any"))

    # Mostrar datos completos
    st.subheader('Datos Completos')
    st.dataframe(df_filtered)
except Exception as e:
    st.error(f"Error al calcular los KPIs: {e}")
