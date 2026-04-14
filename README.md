# Workshop Pratico - Data Streaming Local (Kafka + Parquet + Iceberg)

Este projeto implementa a pratica do handout com as camadas Bronze, Silver e Gold.

## 1) Estrutura do projeto

```
.
├── docker-compose.yml
├── requirements.txt
├── producer.py
├── consumer_bronze.py
├── silver_iceberg.py
├── gold_brazil.py
└── data/
    ├── bronze/
    └── warehouse/
```

## 2) Pre-requisitos

- Python 3.10 a 3.12
- Docker e Docker Compose
- Java 17+

Comandos para validar rapidamente:

```bash
python3 --version
docker --version
docker compose version
java -version
```

Se o seu sistema estiver com Python 3.14+, crie o ambiente com Python 3.12 (ex.: `pyenv`) para manter compatibilidade com `pandas`, `pyarrow` e `pyspark` nas versoes deste workshop.

## 3) Preparar ambiente Python

Por que: isolar dependencias da pratica para evitar conflito com pacotes globais.

Comandos:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Subir o Kafka local

Por que: o Kafka sera o barramento de eventos do pipeline.

Comando:

```bash
docker compose up -d
```

Validar se subiu:

```bash
docker ps --filter name=kafka
```


## 5) Criar pastas de saida

Por que: organizar persistencia local das camadas.

Comando:

```bash
mkdir -p data/bronze data/warehouse
```

## 6) Rodar o consumer Bronze (terminal 1)

Por que: ele precisa estar escutando o topico antes do producer enviar os dados.

Comando:

```bash
source .venv/bin/activate
python consumer_bronze.py
```

O que faz:

- Consome o topico `airports_raw` em micro-batches de 30 segundos.
- So comita offsets apos escrever Parquet (confiabilidade basica).
- Escreve em `data/bronze/airports/ingestion_date=.../ingestion_hour=.../batch_....parquet`.

## 7) Rodar o producer (terminal 2)

Por que: simular fluxo "quebradinho" no Kafka (didatica de streaming).

Comando:

```bash
source .venv/bin/activate
python producer.py
```

O que faz:

- Baixa o dataset de aeroportos (OpenFlights).
- Envia eventos em chunks de 25 (`CHUNK_SIZE = 25`).
- Espera 5s entre chunks (`CHUNK_INTERVAL_SECONDS = 5`).
- Espera 0.15s entre mensagens do mesmo chunk (`RECORD_INTERVAL_SECONDS = 0.15`).
- Adiciona `chunk_number` e `chunk_position` para rastreabilidade.

## 8) Validar Bronze

Por que: confirmar que o ingestion por micro-batch gerou arquivos Parquet.

Comando:

```bash
find data/bronze -type f -name "*.parquet" | head
```

## 9) Gerar Silver em Iceberg

Por que: aplicar tipagem, limpeza e deduplicacao para criar camada analitica confiavel.

Comando:

```bash
source .venv/bin/activate
python silver_iceberg.py
```

O que faz:

- Le Bronze em Parquet.
- Converte tipos (`airport_id`, `latitude`, `longitude`, etc.).
- Filtra `airport_id` nulo.
- Mantem apenas `type = 'airport'`.
- Deduplica por `airport_id`.
- Escreve tabela Iceberg `local.silver.airports` em `data/warehouse`.

## 10) Gerar Gold (Brasil)

Por que: criar visao de consumo para regra de negocio especifica.

Comando:

```bash
source .venv/bin/activate
python gold_brazil.py
```

O que faz:

- Le tabela Silver `local.silver.airports`.
- Filtra `country = 'Brazil'`.
- Seleciona colunas principais para consumo.
- Escreve tabela Iceberg `local.gold.airports_br`.
- Mostra contagem por pais para validacao.

## 11) Ordem recomendada de execucao

```bash
source .venv/bin/activate
docker compose up -d
python consumer_bronze.py
# em outro terminal
source .venv/bin/activate
python producer.py
# depois que houver parquet na bronze
source .venv/bin/activate
python silver_iceberg.py
python gold_brazil.py
```

## 12) Encerramento

```bash
docker compose down
```
