import random
import sqlite3
import time
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("Sensores.db")


def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leitura_sensores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                sensor_id TEXT NOT NULL,
                temperatura REAL NOT NULL,
                umidade REAL NOT NULL,
                pressao REAL NOT NULL
            )
            """
        )


def simular_sensores():
    init_db()
    print("Simulador de sensores em execução. Pressione Ctrl+C para parar.")

    sensores = {
        "Sensor_A": {"temp": (20, 30), "umid": (30, 70), "press": (1000, 1020)},
        "Sensor_B": {"temp": (15, 25), "umid": (40, 80), "press": (990, 1010)},
        "Sensor_C": {"temp": (10, 20), "umid": (50, 90), "press": (980, 1000)},
    }

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            leituras = []

            for sensor_id, limites in sensores.items():
                temperatura = round(random.uniform(*limites["temp"]), 2)
                umidade = round(random.uniform(*limites["umid"]), 2)
                pressao = round(random.uniform(*limites["press"]), 2)
                leituras.append(
                    (timestamp, sensor_id, temperatura, umidade, pressao)
                )

            try:
                with sqlite3.connect(DB_PATH, timeout=10) as conn:
                    conn.executemany(
                        """
                        INSERT INTO leitura_sensores
                            (timestamp, sensor_id, temperatura, umidade, pressao)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        leituras,
                    )
            except sqlite3.OperationalError as erro:
                print(f"Aviso ao acessar o banco de dados: {erro}")
                time.sleep(1)
                continue

            print(f"[{timestamp}] Leituras inseridas no banco de dados.")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nSimulação finalizada.")


if __name__ == "__main__":
    simular_sensores()
