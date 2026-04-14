from pyspark.sql import SparkSession
from pyspark.sql import functions as F


BRONZE_PATH = "data/bronze/airports"
WAREHOUSE_PATH = "data/warehouse"


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("silver-airports-iceberg")
        .config(
            "spark.jars.packages",
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1",
        )
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.local.type", "hadoop")
        .config("spark.sql.catalog.local.warehouse", WAREHOUSE_PATH)
        .getOrCreate()
    )


def transform_bronze_to_silver(df):
    return (
        df.withColumn("airport_id", F.col("airport_id").cast("int"))
        .withColumn("latitude", F.col("latitude").cast("double"))
        .withColumn("longitude", F.col("longitude").cast("double"))
        .withColumn("altitude", F.col("altitude").cast("int"))
        .withColumn("timezone", F.col("timezone").cast("double"))
        .withColumn("event_time", F.to_timestamp("event_time"))
        .withColumn("ingested_at", F.to_timestamp("ingested_at"))
        .filter(F.col("airport_id").isNotNull())
        .filter(F.col("type") == F.lit("airport"))
        .dropDuplicates(["airport_id"])
    )


def main():
    spark = build_spark_session()

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.silver")

    bronze_df = spark.read.parquet(BRONZE_PATH)
    silver_df = transform_bronze_to_silver(bronze_df)

    silver_df.writeTo("local.silver.airports").using("iceberg").createOrReplace()

    spark.sql("SELECT count(*) AS total FROM local.silver.airports").show(truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()
