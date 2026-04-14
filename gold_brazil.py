from pyspark.sql import SparkSession
from pyspark.sql import functions as F


WAREHOUSE_PATH = "data/warehouse"


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("gold-brazil-airports")
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


def main():
    spark = build_spark_session()

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.gold")

    silver_df = spark.table("local.silver.airports")

    gold_df = (
        silver_df.filter(F.col("country") == F.lit("Brazil")).select(
            "airport_id",
            "name",
            "city",
            "country",
            "iata",
            "icao",
            "latitude",
            "longitude",
            "timezone",
            "tz_database_timezone",
        )
    )

    gold_df.writeTo("local.gold.airports_br").using("iceberg").createOrReplace()

    spark.sql(
        """
        SELECT country, count(*) AS total_airports
        FROM local.gold.airports_br
        GROUP BY country
        """
    ).show(truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
