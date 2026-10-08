# Monitoramento da qualidade do ar

Aplicação acadêmica para acompanhar, em tempo quase real, indicadores simulados de qualidade do ar em três ambientes: Laboratório, Produção e Escritório. O projeto combina um gerador de leituras, armazenamento local em SQLite e um painel interativo em Streamlit.

## Funcionalidades

- Gera leituras de CO₂, material particulado PM2.5, umidade e temperatura para cada ambiente.
- Registra as leituras em `telemetria.db`, criado automaticamente nesta pasta.
- Exibe os indicadores mais recentes, gráficos de tendência e uma tabela com os registros recentes.
- Atualiza o painel automaticamente; o intervalo pode ser ajustado entre 2 e 10 segundos.
- Usa o modo WAL do SQLite para permitir que o painel consulte o banco enquanto o simulador grava dados.

## Requisitos

- Python 3 instalado e disponível no terminal como `python`.
- Acesso à internet durante a instalação das bibliotecas. O painel também carrega fontes do Google Fonts quando há conexão.

Dependências Python: `streamlit`, `pandas` e `plotly`.

## Instalação no Windows

Abra o PowerShell nesta pasta e crie um ambiente virtual:

```powershell
python -m venv .venv
```

Instale as dependências no ambiente virtual:

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install streamlit pandas plotly
```

## Como executar

O simulador e o painel devem rodar ao mesmo tempo, em dois terminais abertos nesta pasta.

No primeiro terminal, inicie o gerador de dados:

```powershell
.venv\Scripts\python.exe simulator.py
```

No segundo terminal, inicie o painel:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

O Streamlit exibirá um endereço local no terminal e, normalmente, abrirá o painel no navegador. Para encerrar cada processo, pressione `Ctrl+C` no terminal correspondente.

## Estrutura do projeto

```text
Trabalho/
├── app.py          # Painel Streamlit
├── simulator.py    # Geração e gravação das leituras
├── weg-logo.svg    # Logotipo exibido no painel
├── README.md       # Esta documentação
└── telemetria.db   # Banco SQLite criado na primeira execução
```

`telemetria.db` e a pasta `.venv` são criados localmente durante a execução e não precisam ser adicionados ao controle de versão.

## Dados armazenados

O simulador cria a tabela `leitura_ar`, com os campos:

| Campo | Descrição |
| --- | --- |
| `id` | Identificador sequencial da leitura |
| `timestamp` | Data e hora local da geração |
| `ativo_id` | Ambiente monitorado |
| `co2_ppm` | Concentração de CO₂, em partes por milhão |
| `pm25_ugm3` | Concentração de PM2.5, em µg/m³ |
| `umidade_pct` | Umidade relativa, em porcentagem |
| `temperatura_c` | Temperatura, em graus Celsius |

Uma rodada grava uma leitura por ambiente a cada dois segundos. O banco permanece no disco entre execuções; portanto, o histórico cresce continuamente. Para começar uma demonstração sem o histórico anterior, encerre os processos e remova `telemetria.db` antes de iniciar novamente.

## Arquivos principais

- [`app.py`](app.py): interface, filtros por ambiente, métricas, gráficos e consulta ao SQLite.
- [`simulator.py`](simulator.py): configuração das faixas sintéticas e gravação periódica dos dados.
