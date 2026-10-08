"""Dashboard de telemetria em tempo real para qualidade do ar."""

import base64
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().with_name("telemetria.db")
TABLE = "leitura_ar"
ATIVOS = ["Laboratório", "Produção", "Escritório"]
st.set_page_config(page_title="WEG | Qualidade do ar", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root{--weg:#0064A6;--weg-dark:#06446f;--sky:#e7f4fb;--ink:#142b3b;--muted:#718493;--line:#e5edf1;--surface:#fff;--canvas:#f3f7f9;--gold:#f2c500}
.stApp{background:var(--canvas);color:var(--ink);font-family:'DM Sans',sans-serif}
[data-testid="stSidebar"]{background:linear-gradient(175deg,#073f69 0%,#052c4a 100%);border-right:0}
[data-testid="stSidebar"] *{color:#eff8fc}
[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"]{background:#f2c500}
[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#ffffff12;border-color:#ffffff35}
[data-testid="stSidebar"] [data-baseweb="select"] div{color:#fff}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#d6e8f2}
.brand{padding:8px 0 22px;border-bottom:1px solid #ffffff26;margin-bottom:23px}
.brand-logo{background:#fff;border-radius:12px;padding:6px 9px;display:inline-flex;align-items:center;justify-content:center}
.brand-logo img{display:block;width:45px;height:32px;object-fit:contain}
.brand-kicker{font-size:9px;letter-spacing:2.1px;font-weight:700;color:#9bcde7;margin-top:14px}
.brand-title{font-family:Manrope,sans-serif;font-size:20px;font-weight:800;color:white;line-height:1.17;margin-top:5px}
.brand-sub{font-size:11px;color:#bdd4e2;margin-top:8px}
.side-label{font-size:10px;letter-spacing:1.5px;color:#8abbd8;font-weight:700;margin:8px 0 7px}
.hero{position:relative;overflow:hidden;background:linear-gradient(115deg,#fff 0%,#fff 58%,#e3f3fb 100%);border:1px solid #e6eff3;border-radius:20px;padding:25px 30px;margin:3px 0 22px;box-shadow:0 8px 28px #0d3c5510}
.hero:after{content:'';position:absolute;width:210px;height:210px;border:1px solid #0064a612;border-radius:50%;right:-58px;top:-88px;box-shadow:0 0 0 25px #0064a608,0 0 0 50px #0064a605}
.eyebrow{font-size:10px;letter-spacing:2px;font-weight:700;color:var(--weg);text-transform:uppercase}
.hero h1{font-family:Manrope,sans-serif;font-size:31px;letter-spacing:-1px;line-height:1.15;color:var(--ink);margin:8px 0 7px}
.hero p{color:var(--muted);font-size:14px;margin:0;max-width:690px}
.live-pill{display:inline-flex;gap:8px;align-items:center;border:1px solid #d8eee4;background:#f2fbf6;color:#13774d;padding:8px 12px;border-radius:99px;font-size:11px;font-weight:700;position:relative;z-index:1}
.live-dot{width:7px;height:7px;background:#20ad70;border-radius:50%;box-shadow:0 0 0 4px #20ad7022}
[data-testid="stMetric"]{background:var(--surface);border:1px solid var(--line);border-radius:15px;padding:16px 18px;box-shadow:0 4px 18px #173e5308;min-height:119px}
[data-testid="stMetricLabel"] p{font-size:11px!important;font-weight:700!important;color:#6f8492!important}
[data-testid="stMetricValue"]{font-family:Manrope,sans-serif;color:var(--ink);font-size:27px!important;font-weight:800!important}
[data-testid="stMetricDelta"]{font-size:11px}
.section-head{display:flex;align-items:end;justify-content:space-between;margin:28px 0 12px}
.section-head h3{font-family:Manrope,sans-serif;font-size:18px;font-weight:800;color:var(--ink);margin:0}
.section-head span{font-size:11px;color:var(--muted)}
[data-testid="stPlotlyChart"]{background:#fff;border:1px solid var(--line);border-radius:16px;padding:8px 8px 0;box-shadow:0 4px 18px #173e5308}
[data-testid="stExpander"]{background:#fff;border:1px solid var(--line);border-radius:14px}
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
.footnote{color:#83939e;font-size:10px;text-align:right;margin-top:16px}
@media(max-width:700px){.hero{padding:21px}.hero h1{font-size:25px}}
</style>
""", unsafe_allow_html=True)


def ler_dados(ativo, limite=450):
    """Leitura somente leitura: WAL permite consultar enquanto simulator.py grava."""
    if not DB_PATH.exists():
        return pd.DataFrame(), "Banco ainda não criado. Inicie o simulator.py para começar a receber dados."
    sql = f"SELECT id, timestamp, ativo_id, co2_ppm, pm25_ugm3, umidade_pct, temperatura_c FROM {TABLE}"
    params = []
    if ativo != "Todos":
        sql += " WHERE ativo_id = ?"
        params.append(ativo)
    sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limite)
    try:
        with sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True, timeout=10) as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values(["timestamp", "ativo_id"])
        return df, None
    except (sqlite3.Error, pd.errors.DatabaseError, ValueError) as exc:
        return pd.DataFrame(), f"Não foi possível consultar o SQLite: {exc}"


def criar_grafico(df, coluna, unidade):
    fig = px.line(
        df, x="timestamp", y=coluna, color="ativo_id", markers=True,
        color_discrete_sequence=["#0064A6", "#00A6C7", "#18A878"],
        labels={"timestamp": "Horário", coluna: unidade, "ativo_id": "Ambiente"},
        template="plotly_white",
    )
    fig.update_traces(line={"width": 2.5}, marker={"size": 5}, hovertemplate="%{y:.1f} " + unidade + "<extra>%{fullData.name}</extra>")
    fig.update_layout(
        height=330, margin={"l": 12, "r": 18, "t": 18, "b": 8},
        hovermode="x unified", legend={"orientation": "h", "y": 1.12, "x": 0, "title": ""},
        font={"family": "DM Sans, sans-serif", "color": "#617887", "size": 11},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, tickformat="%H:%M:%S", title=None, rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#edf2f4", zeroline=False, title=None)
    return fig


st.sidebar.markdown(
    '<div class="brand"><div class="brand-logo"><img src="data:image/svg+xml;base64,'
    + base64.b64encode(Path(__file__).with_name("weg-logo.svg").read_bytes()).decode()
    + '" alt="WEG"></div><div class="brand-kicker">TELEMETRIA AMBIENTAL</div><div class="brand-title">Qualidade do ar</div><div class="brand-sub">Painel de monitoramento em tempo real</div></div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown('<div class="side-label">CONFIGURAÇÃO DA VISUALIZAÇÃO</div>', unsafe_allow_html=True)
intervalo = st.sidebar.slider("Atualizar painel a cada", min_value=2, max_value=10, value=3, step=1, format="%d s")
ativo = st.sidebar.selectbox("Ambiente monitorado", ["Todos", *ATIVOS], index=0)
st.sidebar.markdown('<div class="side-label" style="margin-top:26px">FONTE DE DADOS</div>', unsafe_allow_html=True)
st.sidebar.caption("SQLite · modo WAL\nDados sintéticos para demonstração")

df, erro = ler_dados(ativo)
agora = datetime.now()
st.markdown(
    '<div class="hero"><div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">'
    '<div><div class="eyebrow">CENTRO DE MONITORAMENTO · QUALIDADE AMBIENTAL</div>'
    '<h1>Respire melhor. Decida com dados.</h1>'
    '<p>Acompanhe as condições do ar nos ambientes monitorados, com atualização contínua e histórico de leituras.</p></div>'
    '<div class="live-pill"><span class="live-dot"></span> MONITORAMENTO ATIVO</div></div></div>',
    unsafe_allow_html=True,
)

if erro:
    st.info(erro)
elif df.empty:
    st.info("Ainda não há leituras. O painel exibirá os indicadores assim que o simulador gravar os primeiros dados.")
else:
    st.markdown('<div class="section-head"><h3>Leitura mais recente por ambiente</h3><span>Valores do último registro · atualizados automaticamente</span></div>', unsafe_allow_html=True)
    ultimos = df.sort_values(["timestamp", "id"]).groupby("ativo_id", as_index=False).tail(1).sort_values("ativo_id")
    colunas = st.columns(len(ultimos))
    for col, (_, leitura) in zip(colunas, ultimos.iterrows()):
        with col:
            st.markdown(f"**{leitura['ativo_id']}**")
            st.metric("CO₂", f"{leitura['co2_ppm']:.0f} ppm")
            st.metric("PM2.5", f"{leitura['pm25_ugm3']:.1f} µg/m³")
            st.metric("Umidade", f"{leitura['umidade_pct']:.0f}%")
            st.metric("Temperatura", f"{leitura['temperatura_c']:.1f} °C")
            st.caption(f"Última leitura · {leitura['timestamp']:%H:%M:%S}")

    st.markdown('<div class="section-head"><h3>Tendência das medições</h3><span>Histórico recente · passe o cursor para ver detalhes</span></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.caption("CONCENTRAÇÃO DE CO₂ · ppm")
        st.plotly_chart(criar_grafico(df, "co2_ppm", "ppm"), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.caption("MATERIAL PARTICULADO PM2.5 · µg/m³")
        st.plotly_chart(criar_grafico(df, "pm25_ugm3", "µg/m³"), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-head"><h3>Leituras recentes</h3><span>Últimos registros recebidos do banco de dados</span></div>', unsafe_allow_html=True)
    with st.expander("Abrir tabela de dados brutos", expanded=False):
        tabela = df.sort_values("timestamp", ascending=False).head(100).rename(columns={
            "timestamp": "Horário", "ativo_id": "Ambiente", "co2_ppm": "CO₂ (ppm)",
            "pm25_ugm3": "PM2.5 (µg/m³)", "umidade_pct": "Umidade (%)", "temperatura_c": "Temperatura (°C)", "id": "ID",
        })
        st.dataframe(tabela, use_container_width=True, hide_index=True, column_config={"Horário": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm:ss")})

st.markdown('<div class="footnote">Demonstração acadêmica · valores simulados · WEG</div>', unsafe_allow_html=True)
time.sleep(intervalo)
st.rerun()
