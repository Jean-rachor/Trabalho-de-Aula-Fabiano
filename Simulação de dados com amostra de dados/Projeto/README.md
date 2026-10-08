# Monitoramento Industrial

Dashboard Streamlit para as leituras que o `simulator.py` armazena em `Sensores.db`.

## Executar no Windows

No PowerShell, nesta pasta do projeto:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Abra dois terminais nesta mesma pasta:

```powershell
# Terminal 1: gera leituras de demonstração a cada dois segundos
.venv\Scripts\python.exe simulator.py
```

```powershell
# Terminal 2: inicia o dashboard
.venv\Scripts\python.exe -m streamlit run app.py
```

Para parar qualquer processo, use `Ctrl+C` no terminal correspondente.

## Conteúdo e limitações

- O SQLite usado é `Sensores.db`, ao lado dos arquivos Python. O simulador cria a tabela `leitura_sensores` com `timestamp`, `sensor_id`, `temperatura`, `umidade` e `pressao`.
- As leituras geradas pelo simulador são sintéticas e servem para demonstração; não representam medições industriais reais.
- A detecção de anomalias usa modified z-score robusto por sensor e variável (mediana/MAD), com 20 ou mais leituras e corte `|score| > 3,5`. O resultado é somente uma indicação estatística, sem probabilidade calibrada nem previsão de falha.
- Não há eventos rotulados de falha/estado nem limites operacionais definidos. Por isso o painel não calcula disponibilidade, MTBF, MTTR, falhas confirmadas, score de risco industrial ou classificação online/offline.
- Consultas carregam até 50.000 registros por vez; restrinja o período para analisar ou exportar recortes menores.
- O CSV vem das leituras SQLite retornadas pelos filtros atuais, usa `;` como separador e UTF-8 com BOM.
