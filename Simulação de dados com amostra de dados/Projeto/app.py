import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().with_name("Sensores.db")
TABLE = "leitura_sensores"
COLUNAS = {"Temperatura": ("temperatura", "°C"), "Umidade": ("umidade", "%"), "Pressão": ("pressao", "hPa")}
ESPERADAS = {"id", "timestamp", "sensor_id", "temperatura", "umidade", "pressao"}

st.set_page_config(page_title="Operações | Monitoramento Industrial", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root{--ink:#202a34;--muted:#71808e;--line:#e2e7eb;--paper:#f3f5f7;--yellow:#f2c500}
.stApp{background:var(--paper);color:var(--ink)}
[data-testid="stSidebar"]{background:#202a34}[data-testid="stSidebar"] *{color:#edf1f4}
.brand{border-bottom:1px solid #ffffff35;padding:4px 0 18px;margin-bottom:16px}
.brand b{display:block;color:var(--yellow);font-size:11px;letter-spacing:1.5px}.brand strong{display:block;color:white;font-size:21px;margin-top:7px}
.brand small{color:#bac4cc}.top{background:white;border-top:4px solid var(--yellow);padding:17px 21px;border-radius:8px;margin-bottom:16px}
.eyebrow{color:var(--muted);font-size:11px;font-weight:700;letter-spacing:1.4px}.title{font-size:29px;font-weight:750}.subtitle{color:var(--muted);font-size:14px}
.kpi{background:white;border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-height:100px}
.kpi label{color:var(--muted);font-size:11px;font-weight:700}.kpi div{font-size:25px;font-weight:750;margin-top:8px}.kpi small{color:var(--muted)}
div[data-testid="stMetric"]{background:white;border:1px solid var(--line);padding:12px 15px;border-radius:8px}
</style>""", unsafe_allow_html=True)


@st.cache_data(ttl=3, show_spinner=False)
def inspect_db(path, modified):
    del modified
    if not Path(path).exists():
        return "Banco SQLite não encontrado. Inicie o simulador para criá-lo.", [], []
    try:
        with sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True) as conn:
            tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'", conn)["name"].tolist()
            if TABLE not in tables:
                return f"Tabela '{TABLE}' não encontrada.", tables, []
            columns = pd.read_sql_query(f"PRAGMA table_info({TABLE})", conn)["name"].tolist()
            return None, tables, columns
    except sqlite3.Error as exc:
        return f"Não foi possível abrir o banco: {exc}", [], []


@st.cache_data(ttl=3, show_spinner=False)
def load_data(path, modified, start, end, sensor, limit=50000):
    del modified
    sql = "SELECT id,timestamp,sensor_id,temperatura,umidade,pressao FROM leitura_sensores WHERE timestamp>=? AND timestamp<?"
    params = [start, end]
    if sensor != "Todos":
        sql += " AND sensor_id=?"
        params.append(sensor)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    try:
        with sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True, timeout=10) as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            for col in ("temperatura", "umidade", "pressao"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.sort_values("timestamp")
        return df, None
    except (sqlite3.Error, ValueError, TypeError) as exc:
        return pd.DataFrame(), f"Erro ao consultar as leituras: {exc}"


def header(title, subtitle, section):
    st.markdown(f'<div class="top"><div class="eyebrow">{section}</div><div class="title">{title}</div><div class="subtitle">{subtitle}</div></div>', unsafe_allow_html=True)


def kpi(label, value, note=""):
    st.markdown(f'<div class="kpi"><label>{label}</label><div>{value}</div><small>{note}</small></div>', unsafe_allow_html=True)


def line_chart(df, column, title, unit):
    fig = px.line(df, x="timestamp", y=column, color="sensor_id", markers=True, title=title,
                  labels={"timestamp": "Horário", column: unit, "sensor_id": "Sensor"}, template="plotly_white")
    fig.update_layout(hovermode="x unified", legend_title_text="Sensor", margin=dict(l=10, r=10, t=50, b=10))
    fig.update_xaxes(rangeslider_visible=True)
    return fig


def detect_anomalies(df):
    """Robust modified z-score; only a statistical signal, never a fault prediction."""
    events = []
    for sensor, group in df.groupby("sensor_id"):
        group = group.sort_values("timestamp")
        for label, (column, unit) in COLUNAS.items():
            valid = group.dropna(subset=[column])
            if len(valid) < 20:
                continue
            values = valid[column]
            median = values.median()
            mad = (values - median).abs().median()
            if pd.isna(mad) or mad == 0:
                continue
            score = 0.6745 * (values - median) / mad
            flagged = valid.loc[score.abs() > 3.5].copy()
            for idx, row in flagged.iterrows():
                events.append({"timestamp": row["timestamp"], "sensor_id": sensor, "variável": label,
                               "valor": row[column], "unidade": unit, "desvio robusto": float(score.loc[idx])})
    return pd.DataFrame(events).sort_values("timestamp", ascending=False) if events else pd.DataFrame(columns=["timestamp", "sensor_id", "variável", "valor", "unidade", "desvio robusto"])


st.sidebar.markdown('<div class="brand"><b>MONITORAMENTO INDUSTRIAL</b><strong>Operações</strong><small>Painel de processo · SQLite</small></div>', unsafe_allow_html=True)
page = st.sidebar.radio("NAVEGAÇÃO", ["🏭 Visão Geral", "📡 Monitoramento", "📊 Histórico", "🔮 Manutenção Preditiva", "⚠️ Alarmes", "🧪 Qualidade dos Dados", "📥 Exportação"])
period = st.sidebar.selectbox("Período", ["Última hora", "Últimas 6 horas", "Últimas 24 horas", "Últimos 7 dias", "Todo o histórico"], index=2)
refresh = st.sidebar.toggle("Atualização automática", value=True)
refresh_seconds = st.sidebar.select_slider("Atualizar a cada", [5, 10, 15, 30], value=10, format_func=lambda n: f"{n} s")
hours = {"Última hora": 1, "Últimas 6 horas": 6, "Últimas 24 horas": 24, "Últimos 7 dias": 168}
now = datetime.now()
start = (now - timedelta(hours=hours[period])).strftime("%Y-%m-%d %H:%M:%S") if period != "Todo o histórico" else "0001-01-01 00:00:00"
end = (now + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
try:
    modified = DB_PATH.stat().st_mtime_ns
except OSError:
    modified = 0
problem, tables, columns = inspect_db(str(DB_PATH), modified)
if problem:
    header("Monitoramento Industrial", "Painel de operações", "CENTRO DE OPERAÇÕES")
    st.error(problem)
    if tables:
        st.caption("Tabelas encontradas: " + ", ".join(tables))
    st.stop()
missing = ESPERADAS - set(columns)
if missing:
    st.error("Esquema incompatível. Colunas ausentes: " + ", ".join(sorted(missing)))
    st.stop()
try:
    with sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, timeout=10) as conn:
        sensors = ["Todos"] + pd.read_sql_query("SELECT DISTINCT sensor_id FROM leitura_sensores WHERE sensor_id IS NOT NULL ORDER BY sensor_id", conn)["sensor_id"].astype(str).tolist()
except sqlite3.Error as exc:
    st.error(f"Não foi possível listar os sensores: {exc}")
    st.stop()
sensor = st.sidebar.selectbox("Sensor", sensors)


def render():
    try:
        modified_now = DB_PATH.stat().st_mtime_ns
    except OSError:
        modified_now = 0
    df, error = load_data(str(DB_PATH), modified_now, start, end, sensor)
    if error:
        st.error(error)
        return
    title = page.split(" ", 1)[1]
    if df.empty:
        header(title, "Leituras armazenadas no banco para os filtros escolhidos.", "AQUISIÇÃO DE DADOS")
        st.info("Nenhuma leitura encontrada neste período e sensor.")
        return

    if page == "🏭 Visão Geral":
        header("Visão Geral", "Resumo do histórico disponível para os filtros atuais.", "CENTRO DE OPERAÇÕES")
        metrics = st.columns(4)
        vals = [("SENSORES COM DADOS", str(df.sensor_id.nunique()), "Observados no período"),
                ("LEITURAS", f"{len(df):,}".replace(",", "."), "Máximo de 50 mil nesta consulta"),
                ("TEMPERATURA MÉDIA", f"{df.temperatura.mean():.2f} °C", "Valores registrados"),
                ("ÚLTIMA LEITURA", df.timestamp.max().strftime("%d/%m %H:%M:%S"), "Horário do banco")]
        for col, data in zip(metrics, vals):
            with col: kpi(*data)
        left, right = st.columns(2)
        with left: st.plotly_chart(line_chart(df, "temperatura", "Temperatura por sensor", "Temperatura (°C)"), width="stretch")
        with right: st.plotly_chart(line_chart(df, "umidade", "Umidade por sensor", "Umidade (%)"), width="stretch")
        st.caption("Banco atual gerado pelo simulator.py: leituras sintéticas de temperatura, umidade e pressão. Não há eventos de falha ou estado; disponibilidade, MTBF e MTTR não são calculáveis.")

    elif page == "📡 Monitoramento":
        header("Monitoramento", "Última leitura registrada e tendência observada.", "AQUISIÇÃO DE DADOS")
        latest = df.sort_values("timestamp").groupby("sensor_id", as_index=False).tail(1)
        cards = st.columns(min(max(len(latest), 1), 4))
        for i, (_, row) in enumerate(latest.iterrows()):
            with cards[i % len(cards)]:
                st.markdown(f"#### {row.sensor_id}")
                st.markdown("🟡 **LEITURA NO PERÍODO**")
                st.metric("Temperatura", f"{row.temperatura:.2f} °C")
                st.metric("Umidade", f"{row.umidade:.2f} %")
                st.metric("Pressão", f"{row.pressao:.2f} hPa")
                st.caption(f"Última leitura: {row.timestamp:%d/%m/%Y %H:%M:%S}")
        st.plotly_chart(line_chart(df, "temperatura", "Tendência de temperatura", "Temperatura (°C)"), width="stretch")
        st.caption("O projeto não define limite de atraso de comunicação. O status confirma leitura no recorte, não classifica o equipamento como online/offline.")

    elif page == "📊 Histórico":
        header("Análise Histórica", "Explore as variáveis e compare sensores.", "ANÁLISE DE PROCESSO")
        a, b = st.columns(2)
        with a: variable = st.selectbox("Variável", list(COLUNAS))
        col, unit = COLUNAS[variable]
        with b: series = st.selectbox("Série", ["Comparar sensores"] + sorted(df.sensor_id.dropna().unique().tolist()))
        data = df if series == "Comparar sensores" else df[df.sensor_id == series]
        values = data[col].dropna()
        if values.empty: st.warning("Não há valores válidos para esta variável.")
        else:
            change = f"{(values.iloc[-1] / values.iloc[0] - 1) * 100:+.1f}%" if len(values) > 1 and values.iloc[0] else "—"
            stats = st.columns(5)
            summary = [("MÉDIA", f"{values.mean():.2f} {unit}"), ("MÍNIMO", f"{values.min():.2f} {unit}"), ("MÁXIMO", f"{values.max():.2f} {unit}"), ("DESVIO PADRÃO", f"{values.std():.2f} {unit}" if len(values) > 1 else "—"), ("VARIAÇÃO 1ª→ÚLTIMA", change)]
            for c, (label, value) in zip(stats, summary):
                with c: kpi(label, value)
            st.plotly_chart(line_chart(data, col, f"{variable} ao longo do tempo", f"{variable} ({unit})"), width="stretch")
            fig = px.histogram(data, x=col, color="sensor_id", marginal="box", title=f"Distribuição de {variable}", labels={col: unit, "sensor_id": "Sensor"}, template="plotly_white")
            st.plotly_chart(fig, width="stretch")

    elif page in ("🔮 Manutenção Preditiva", "⚠️ Alarmes"):
        name = "Manutenção Preditiva" if page.startswith("🔮") else "Alarmes e anomalias"
        header(name, "Detecção estatística explicável; não representa previsão de falha real.", "CONDIÇÃO DOS ATIVOS")
        st.warning("Os valores do simulador são sintéticos. O score estatístico sinaliza leituras atípicas em relação à própria distribuição histórica; não confirma defeito nem prevê falhas.")
        events = detect_anomalies(df)
        if events.empty:
            st.info("Nenhuma anomalia estatística identificada, ou histórico insuficiente (mínimo de 20 valores por sensor e variável).")
        else:
            st.metric("Leituras sinalizadas", len(events))
            st.dataframe(events, width="stretch", hide_index=True)
        st.caption("Método: modified z-score robusto (mediana e MAD), sinalização quando |score| > 3,5; somente séries com pelo menos 20 observações e MAD diferente de zero. Score não calibrado como probabilidade de falha. Não há labels para treinar/classificar falhas.")

    elif page == "🧪 Qualidade dos Dados":
        header("Qualidade dos Dados", "Consistência e frequência observadas no período selecionado.", "CONFIABILIDADE DA INFORMAÇÃO")
        fields = ["timestamp", "sensor_id", "temperatura", "umidade", "pressao"]
        nulls = int(df[fields].isna().sum().sum())
        duplicates = int(df.duplicated(subset=fields).sum())
        invalid = int(df.timestamp.isna().sum())
        ks = st.columns(4)
        for c, item in zip(ks, [("REGISTROS", str(len(df))), ("CAMPOS NULOS", str(nulls)), ("DUPLICADOS", str(duplicates)), ("HORÁRIOS INVÁLIDOS", str(invalid))]):
            with c: kpi(*item)
        cadence = []
        for sid, group in df.dropna(subset=["timestamp"]).groupby("sensor_id"):
            times = group.timestamp.drop_duplicates().sort_values()
            gaps = times.diff().dt.total_seconds().dropna()
            cadence.append({"sensor_id": sid, "registros": len(group), "última leitura": times.max(), "intervalo mediano (s)": gaps.median() if len(gaps) else None, "intervalo máximo (s)": gaps.max() if len(gaps) else None})
        st.subheader("Cadência por sensor")
        st.dataframe(pd.DataFrame(cadence), width="stretch", hide_index=True)
        st.caption("Os intervalos descrevem timestamps existentes; sem um timeout configurado, a aplicação não rotula sensores como offline.")

    elif page == "📥 Exportação":
        header("Exportação", "CSV gerado diretamente das leituras filtradas do SQLite.", "EXTRAÇÃO DE DADOS")
        st.write(f"Período: **{period}** · Sensor: **{sensor}** · Registros: **{len(df):,}**".replace(",", "."))
        if len(df) >= 50000: st.warning("Limite de 50.000 registros alcançado. Reduza o período antes de exportar.")
        csv = df.drop(columns=["id"], errors="ignore").to_csv(index=False, sep=";", decimal=",", date_format="%Y-%m-%d %H:%M:%S").encode("utf-8-sig")
        st.download_button("⬇️ Exportar dados para CSV", data=csv, file_name=f"leituras_sensores_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv", disabled=df.empty, type="primary")
        st.caption("Inclui somente o recorte consultado. Separador ;, decimal com vírgula e encoding UTF-8 com BOM para planilhas.")


if refresh:
    @st.fragment(run_every=refresh_seconds)
    def live_panel():
        render()
    live_panel()
else:
    render()
