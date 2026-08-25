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

st.title("⚽ Visualizador de Pases - Copa Mundial de la FIFA")

# ---------------------------------------------------------
# Carga de Competiciones y Partidos con Caché
# ---------------------------------------------------------
@st.cache_data
def get_world_cup_editions():
    # Obtener todas las competiciones disponibles en StatsBomb
    comps = sb.competitions()
    # Filtrar únicamente las ediciones de Copa del Mundo Masculina
    wc_comps = comps[comps['competition_name'] == 'FIFA World Cup'].sort_values(by='season_name', ascending=False)
    return wc_comps

@st.cache_data
def load_matches(comp_id, season_id):
    # Cargar los partidos de la edición seleccionada
    matches = sb.matches(competition_id=comp_id, season_id=season_id)
    return matches

@st.cache_data
def load_events(match_id):
    # Cargar los eventos del partido seleccionado
    events = sb.events(match_id=match_id)
    return events

# ---------------------------------------------------------
# Barra Lateral: Selección de Edición y Partido
# ---------------------------------------------------------
st.sidebar.header("🏆 Seleccionar Mundial")

wc_editions = get_world_cup_editions()

# Diccionario para mapear el nombre de la edición (ej. "2022", "2018") con (competition_id, season_id)
edition_options = {
    f"Copa del Mundo {row['season_name']}": (row['competition_id'], row['season_id'])
    for _, row in wc_editions.iterrows()
}

selected_edition_name = st.sidebar.selectbox("Edición del Mundial:", list(edition_options.keys()))
comp_id, season_id = edition_options[selected_edition_name]

# Cargar los partidos correspondientes a la edición elegida
matches = load_matches(comp_id, season_id)

st.sidebar.header("🎯 Seleccionar Partido")

# Filtro por Fase del Torneo (Opcional)
stages = ["Todas las Fases"] + sorted(matches['competition_stage'].unique().tolist())
selected_stage = st.sidebar.selectbox("Fase del torneo:", stages)

if selected_stage != "Todas las Fases":
    filtered_matches = matches[matches['competition_stage'] == selected_stage]
else:
    filtered_matches = matches.copy()

filtered_matches = filtered_matches.sort_values(by='match_date')

# Desplegable de Partidos de esa edición
match_options = {
    f"{row['home_team']} {row['home_score']} - {row['away_score']} {row['away_team']} ({row['match_date']})": row['match_id']
    for _, row in filtered_matches.iterrows()
}

selected_match_label = st.sidebar.selectbox("Partido:", list(match_options.keys()))
match_id = match_options[selected_match_label]

# Cargar eventos del partido elegido
events = load_events(match_id)

# ---------------------------------------------------------
# Procesamiento de Eventos de Pase
# ---------------------------------------------------------
variables = ['location', 'minute', 'period', 'player', 'second', 'team', 'type', 'pass_end_location', 'pass_recipient']
available_vars = [col for col in variables if col in events.columns]
passes = events[available_vars]

# Filtrar solo eventos de tipo "Pass"
final = passes[passes['type'] == 'Pass'].copy()
final.reset_index(drop=True, inplace=True)

# Extraer coordenadas x, y (inicio y fin)
final['x0'] = final.location.apply(lambda x: x[0] if isinstance(x, list) else np.nan)
final['y0'] = final.location.apply(lambda x: x[1] if isinstance(x, list) else np.nan)
final['x1'] = final.pass_end_location.apply(lambda x: x[0] if isinstance(x, list) else np.nan)
final['y1'] = final.pass_end_location.apply(lambda x: x[1] if isinstance(x, list) else np.nan)

# ---------------------------------------------------------
# Filtros Adicionales (Minuto y Equipo)
# ---------------------------------------------------------
st.sidebar.header("⏱️ Filtros de Eventos")

# Selector de minuto
max_minute = int(final['minute'].max()) if not final.empty else 90
minuto = st.sidebar.slider("Minuto del partido:", min_value=0, max_value=max_minute, value=15)

# Selector de equipo dentro del partido
teams_in_match = sorted(final['team'].dropna().unique().tolist())
selected_team_filter = st.sidebar.radio("Mostrar pases de:", ["Ambos equipos"] + teams_in_match)

# Filtrar dataset final por minuto y equipo
passes_min = final[final.minute == minuto]
if selected_team_filter != "Ambos equipos":
    passes_min = passes_min[passes_min.team == selected_team_filter]

# ---------------------------------------------------------
# Renderizado de la Cancha
# ---------------------------------------------------------
st.subheader(f"{selected_edition_name} | {selected_match_label}")
st.caption(f"Visualizando pases en el minuto **{minuto}**")

if passes_min.empty:
    st.info(f"No hay pases registrados en el minuto {minuto} para los filtros seleccionados.")
else:
    # Dibujar la cancha con mplsoccer
    pitch = Pitch(pitch_color='#22312b', line_color='#c7d5cc', stripe=False)
    fig, ax = pitch.draw(figsize=(10, 6.5))
    
    teams = passes_min['team'].unique()
    colors = ['#e74c3c', '#3498db']  # Colores para distinguir equipos
    
    for idx, team in enumerate(teams):
        team_passes = passes_min[passes_min.team == team]
        team_color = colors[idx % len(colors)]
        
        # Dibujar flechas desde origen (x0, y0) hasta destino (x1, y1)
        pitch.arrows(
            team_passes.x0, team_passes.y0,
            team_passes.x1, team_passes.y1,
            ax=ax, color=team_color, width=2, headwidth=4, label=team, alpha=0.85
        )
        
        # Resaltar puntos de origen
        pitch.scatter(
            team_passes.x0, team_passes.y0,
            ax=ax, color=team_color, s=60, edgecolors='white', zorder=3
        )

    ax.legend(
        facecolor='#22312b', 
        edgecolor='none', 
        fontsize=10, 
        loc='upper center', 
        bbox_to_anchor=(0.5, 1.05), 
        ncol=2, 
        labelcolor='white'
    )
    st.pyplot(fig)

# Tabla interactiva desplegable
with st.expander("📋 Detalle de pases en este minuto"):
    st.dataframe(
        passes_min[['minute', 'second', 'team', 'player', 'pass_recipient', 'x0', 'y0', 'x1', 'y1']],
        use_container_width=True
    )
