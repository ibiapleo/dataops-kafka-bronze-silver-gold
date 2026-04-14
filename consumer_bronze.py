import json
import os
import time
from datetime import datetime

import pandas as pd
from kafka import KafkaConsumer


TOPIC_NAME = "airports_raw"
BOOTSTRAP_SERVERS = "localhost:9092"
GROUP_ID = "bronze-consumer-group"
BRONZE_PATH = "data/bronze/airports"
BATCH_SECONDS = 30


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def flush_batch(records: list[dict]) -> None:
    if not records:
        print("no records to flush")
        return

    ingestion_ts = datetime.utcnow()
    ingestion_date = ingestion_ts.strftime("%Y-%m-%d")
    ingestion_hour = ingestion_ts.strftime("%H")

    df = pd.DataFrame(records)
    df["ingestion_date"] = ingestion_date
    df["ingestion_hour"] = ingestion_hour
    df["ingested_at"] = ingestion_ts.isoformat()

    output_path = os.path.join(
        BRONZE_PATH,
        f"ingestion_date={ingestion_date}",
        f"ingestion_hour={ingestion_hour}",
    )
    ensure_directory(output_path)

    file_name = f"batch_{int(time.time())}.parquet"
    full_path = os.path.join(output_path, file_name)

    df.to_parquet(full_path, index=False)
    print(f"bronze written: {full_path} | rows={len(df)}")


def main():
    ensure_directory(BRONZE_PATH)

    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )

    batch = []
    batch_start = time.time()

    try:
        while True:
            message_pack = consumer.poll(timeout_ms=1000)

            for _, messages in message_pack.items():
                for message in messages:
                    batch.append(message.value)

            if time.time() - batch_start >= BATCH_SECONDS:
                flush_batch(batch)
                consumer.commit()
                batch = []
                batch_start = time.time()

    except KeyboardInterrupt:
        print("stopping consumer...")
        if batch:
            flush_batch(batch)
            consumer.commit()
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
