from pyspark.sql import SparkSession
import argparse
import platform

parser = argparse.ArgumentParser("pyspark")
parser.add_argument("-e", "--env", default="local")

def setMasterUrl(builder: SparkSession.Builder):
  if platform.system != "Linux":
    builder.master("local[*]")


def spark_session() -> SparkSession:
  builder = (SparkSession.builder
    .appName("test")
    .enableHiveSupport()
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
      "spark.sql.catalog.spark_catalog",
      "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    .config("spark.sql.files.ignoreMissingFiles", "true")
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
  )
  setMasterUrl(builder)
  spark = builder.getOrCreate()
  return spark

spark = spark_session()

df = spark.table("")
df.write
