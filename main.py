

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsbombpy import sb
from mplsoccer import Pitch
import warnings

warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(page_title="StatsBomb Pass Visualizer", layout="wide")

st.title("⚽ Visualizador de Pases - Copa del Mundo 2022")

# ---------------------------------------------------------
# Carga de datos con Caché para acelerar la app
# ---------------------------------------------------------
@st.cache_data
def load_matches():
    # Cargar partidos del Mundial 2022 (competition_id=43, season_id=106)
    matches = sb.matches(competition_id=43, season_id=106)
    return matches

@st.cache_data
def load_events(match_id):
    # Cargar eventos del partido seleccionado
    events = sb.events(match_id=match_id)
    return events

# Cargar partidos
wc_2022 = load_matches()

# ---------------------------------------------------------
# Barra lateral (Sidebar): Filtros interactivos
# ---------------------------------------------------------
st.sidebar.header("Filtros del Partido")

# Lista de equipos disponibles
teams = sorted(wc_2022['home_team'].unique())
selected_team = st.sidebar.selectbox("Selecciona un equipo:", teams)

# Filtrar partidos donde participó el equipo seleccionado
filtered_matches = wc_2022[(wc_2022.home_team == selected_team) | (wc_2022.away_team == selected_team)]

# Formatear opciones para el selector de partidos
match_options = {
    f"{row['home_team']} vs {row['away_team']} ({row['match_date']})": row['match_id']
    for _, row in filtered_matches.iterrows()
}

selected_match_label = st.sidebar.selectbox("Selecciona un partido:", list(match_options.keys()))
match_id = match_options[selected_match_label]

# Cargar eventos del partido seleccionado
events = load_events(match_id)

# ---------------------------------------------------------
# Procesamiento de Pases
# ---------------------------------------------------------
variables = ['location', 'minute', 'period', 'player', 'second', 'team', 'type', 'pass_end_location', 'pass_recipient']
# Asegurar que existan las columnas en el dataframe
available_vars = [col for col in variables if col in events.columns]
passes = events[available_vars]

# Filtrar solo eventos de tipo "Pass"
final = passes[passes['type'] == 'Pass'].copy()
final.reset_index(drop=True, inplace=True)

# Extraer coordenadas x, y de origen y final
final['x0'] = final.location.apply(lambda x: x[0] if isinstance(x, list) else np.nan)
final['y0'] = final.location.apply(lambda x: x[1] if isinstance(x, list) else np.nan)
final['x1'] = final.pass_end_location.apply(lambda x: x[0] if isinstance(x, list) else np.nan)
final['y1'] = final.pass_end_location.apply(lambda x: x[1] if isinstance(x, list) else np.nan)

# Selector de minuto en la barra lateral (reemplaza a ipywidgets.interact)
max_minute = int(final['minute'].max()) if not final.empty else 90
minuto = st.sidebar.slider("Minuto del partido:", min_value=0, max_value=max_minute, value=15)

# ---------------------------------------------------------
# Visualización
# ---------------------------------------------------------
st.subheader(f"Pases registrados en el minuto {minuto}")

# Filtrar por el minuto seleccionado
passes_min = final[final.minute == minuto]

if passes_min.empty:
    st.warning(f"No hay pases registrados en el minuto {minuto}.")
else:
    # Graficar con mplsoccer y seaborn
    pitch = Pitch(pitch_color='grass', line_color='white', stripe=True)
    fig, ax = pitch.draw(figsize=(10, 6))
    
    sns.scatterplot(
        data=passes_min,
        x='x0',
        y='y0',
        hue='team',
        ax=ax,
        s=100,
        zorder=2
    )
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=2)
    
    # En Streamlit se usa st.pyplot en lugar de plt.show()
    st.pyplot(fig)

# Mostrar la tabla de datos procesados
with st.expander("Ver tabla de datos de pases"):
    st.dataframe(final[['minute', 'team', 'player', 'pass_recipient', 'x0', 'y0', 'x1', 'y1']])
