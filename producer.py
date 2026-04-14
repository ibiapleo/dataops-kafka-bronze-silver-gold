import csv
import io
import json
import time
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer


DATASET_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
TOPIC_NAME = "airports_raw"
BOOTSTRAP_SERVERS = "localhost:9092"

# Fast mode para cargas maiores durante validacao da pratica.
CHUNK_SIZE = 25
CHUNK_INTERVAL_SECONDS = 0.2
RECORD_INTERVAL_SECONDS = 0.0

COLUMNS = [
    "airport_id",
    "name",
    "city",
    "country",
    "iata",
    "icao",
    "latitude",
    "longitude",
    "altitude",
    "timezone",
    "dst",
    "tz_database_timezone",
    "type",
    "source",
]


def normalize_value(value: str):
    if value == r"\N":
        return None
    return value


def chunked(iterable, chunk_size: int):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def load_dataset_rows():
    response = requests.get(DATASET_URL, timeout=60)
    response.raise_for_status()

    content = response.text
    reader = csv.reader(io.StringIO(content))

    for row in reader:
        if len(row) != len(COLUMNS):
            continue

        payload = {column: normalize_value(value) for column, value in zip(COLUMNS, row)}
        payload["event_time"] = datetime.now(timezone.utc).isoformat()
        yield payload


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: str(key).encode("utf-8"),
    )

    total_sent = 0

    for chunk_number, records_chunk in enumerate(chunked(load_dataset_rows(), CHUNK_SIZE), start=1):
        print(f"\nEnviando chunk {chunk_number} com {len(records_chunk)} registros...")

        for record_index, record in enumerate(records_chunk, start=1):
            record["chunk_number"] = chunk_number
            record["chunk_position"] = record_index

            producer.send(
                TOPIC_NAME,
                key=record["airport_id"],
                value=record,
            )

            total_sent += 1
            if record_index == 1 or record_index % 500 == 0 or record_index == len(records_chunk):
                print(
                    f"sent airport_id={record['airport_id']} "
                    f"chunk={chunk_number} pos={record_index}"
                )
            time.sleep(RECORD_INTERVAL_SECONDS)

        producer.flush()
        print(
            f"Chunk {chunk_number} enviado com sucesso. "
            f"Total acumulado: {total_sent}"
        )
        time.sleep(CHUNK_INTERVAL_SECONDS)

    producer.close()
    print(f"\nEnvio concluido. Total de registros enviados: {total_sent}")


if __name__ == "__main__":
    main()
