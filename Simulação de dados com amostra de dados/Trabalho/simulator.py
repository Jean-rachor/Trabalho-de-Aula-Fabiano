"""Simulador contínuo de qualidade do ar para três ambientes internos."""

import random
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().with_name("telemetria.db")
INTERVAL_SECONDS = 2

AMBIENTES = {
    "Laboratório": {"co2": (520, 780), "pm25": (3, 12), "umidade": (42, 56), "temperatura": (21, 24)},
    "Produção": {"co2": (650, 1050), "pm25": (5, 19), "umidade": (38, 53), "temperatura": (23, 28)},
    "Escritório": {"co2": (480, 920), "pm25": (2, 10), "umidade": (40, 60), "temperatura": (21, 26)},
}


def init_db():
    """Cria o schema e ativa WAL para permitir leitura simultânea."""
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS leitura_ar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ativo_id TEXT NOT NULL,
                co2_ppm REAL NOT NULL,
                pm25_ugm3 REAL NOT NULL,
                umidade_pct REAL NOT NULL,
                temperatura_c REAL NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leitura_ar_tempo ON leitura_ar(timestamp)")


def gerar_leitura(limites):
    """Gera valores sintéticos dentro de faixas plausíveis para demonstração."""
    return (
        round(random.uniform(*limites["co2"]), 1),
        round(random.uniform(*limites["pm25"]), 2),
        round(random.uniform(*limites["umidade"]), 1),
        round(random.uniform(*limites["temperatura"]), 1),
    )


def simular():
    init_db()
    print(f"Simulador ativo: {len(AMBIENTES)} ambientes, gravação a cada {INTERVAL_SECONDS}s. Ctrl+C para encerrar.")
    while True:
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        leituras = [(timestamp, ativo, *gerar_leitura(limites)) for ativo, limites in AMBIENTES.items()]
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.executemany(
                    """INSERT INTO leitura_ar
                       (timestamp, ativo_id, co2_ppm, pm25_ugm3, umidade_pct, temperatura_c)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    leituras,
                )
            print(f"[{timestamp}] {len(leituras)} leituras inseridas.")
        except sqlite3.OperationalError as exc:
            print(f"Aviso SQLite: {exc}. Nova tentativa em 1 segundo.")
            time.sleep(1)
            continue
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        simular()
    except KeyboardInterrupt:
        print("\nSimulação encerr")
