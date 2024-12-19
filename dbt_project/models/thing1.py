import pyspark
from Transformation import ITransform
from dataclasses import dataclass
from config import config
some = 'var'

def some_f() -> str:
  return "no"

def some_l():
  return [""]

my_sources: list[str] = [
  "source1", 
  "source2"
]

@dataclass
class Thing1(ITransform):
  something: str
  somethingelse = 0

  def sources_list(self) -> list[str]: [
    "asdf"
  ]

  def dest_table(self):
    return 1


