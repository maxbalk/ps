from collections import defaultdict
import json
import platform
from typing import Any, NamedTuple

from pyspark.sql import DataFrame, SparkSession

def top_sort(
  parent_map: dict[str, list[str]]
):
  adjl = defaultdict(list, parent_map)
  ordered = []
  visited = set()
  path = set()
  
  def tsutil(
    key: str,
    vals: list[str]
  ):
    if key in path:
      raise ValueError(f'cycle with {key}!')
    if key in visited:
      return

    visited.add(key)
    path.add(key)

    for val in vals:
      tsutil(val, adjl[val])

    path.remove(key)
    ordered.append(key)

  for key, vals in adjl.items():
    if key not in visited:
      tsutil(key, vals)

  return ordered[::-1]

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


def view(spark: SparkSession, sqlQuery: str, relname: str):
  return spark.sql(f"""
    create or replace view {relname} as {sqlQuery}
  """)

def write_table(df: DataFrame, relname: str):
  (df
   .write
   .format('delta')
   .saveAsTable(relname)
  )

def df(spark: SparkSession, sqlQuery: str):
  return spark.sql(sqlQuery)

def materialization(
  spark: SparkSession,
  mat: str,
  query: str,
  relname: str
):
  d = {
    'table': write_table(df(spark, query), relname),
    'view': view(spark, query, relname)
  }
  return d[mat]

class Node(NamedTuple):
  fqn: str
  query: str
  material: str
  relname: str


def main():
  with open('manifest.json') as file:
    manifest = json.load(file)

  sorted: list[str] = [
    node for node in 
    top_sort(manifest['parent_map'])
    if node.startswith('model')
  ]
  models: dict[str, dict[str, Any]] = manifest['nodes']

  nodes = {
    fqn: Node(
      fqn,
      model['compiled_code'],
      model['config']['materialized'],
      model['relation_name']
    )
    for fqn, model in models.items()
  }
  
  spark = spark_session()
  for fqn in sorted:
    node = nodes[fqn]
    materialization(spark, Node.material, Node.query, Node.relname)
    

  return 0

if __name__ == '__main__':
  main()
