from typing import Any
import jinja2 as j2
import jinja2.nodes       as j2n
import jinja2.environment as j2e
import jinja2.ext         as j2x
import jinja2.parser      as j2p

class MyNode:
  def __init__(self, t: j2.Template) -> None:
    self.tmp = t
    self.tmp.new_context(self.node_context())

  def config(self, **kwargs):
    print('in config, printing name: ', self.tmp.name)
    [print(arg) for arg in kwargs]
    pass

  def ref(self) -> None:
    pass

  def source(self) -> None:
    pass

  def context_methods(self):
    return [
      self.config,
      self.ref,
      self.source
    ]

  def node_context(self):
    return {
      func.__name__ : func
        for func in self.context_methods()
    }


def main():
  #
  # MACROS
  #
  macro_loader = j2.FileSystemLoader(searchpath='macros')
  macro_env = j2.Environment(loader = macro_loader)
  macro_files = [
    tmp_name 
      for tmp_name in macro_env.list_templates() 
      if not tmp_name.endswith('.pyc')
  ]
  macro_srces = [ 
    macro_loader.get_source(macro_env, file)[0]
      for file in macro_files 
  ]
  macro_asts = [
    macro_env.parse(src) 
      for src in macro_srces
  ]
  macro_nodes = [
    macro for ast in macro_asts 
      for macro in ast.find_all(j2n.Macro)
  ]
  macro_dict = {
    macro.name: macro
      for macro in macro_nodes
  }

  #
  # MODELS 
  # 
  model_loader = j2.FileSystemLoader(searchpath='models')
  model_env       = j2.Environment(loader = model_loader)

  # inject macros into globals
  tmp_globals: dict[str, Any] = model_env.globals
  tmp_globals.update(macro_dict)
  model_env.globals = tmp_globals 

  model_files = [
    t for t in model_env.list_templates() if t.endswith('.sql')
  ]

  nodes = [
    MyNode(model_env.get_template(file))
      for file in model_files 
  ]
  for file in model_files:
    template = model_env.get_template(file)
    node = MyNode(template)
    pass

if __name__ == '__main__':
  main()
