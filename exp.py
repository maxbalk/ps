from doctest import master
import enum
from os.path import isfile
import jinja2             as j2
import jinja2.nodes       as j2n
import jinja2.environment as j2e
import jinja2.ext         as j2x
import jinja2.parser      as j2p
import yaml
import os

from enum import Enum
from typing import Any, Dict, Generator, cast


class Target():
  def __init__(self, **kwargs):
    for key, val in kwargs.items():
      setattr(self, key, val)

def extract_calls(env, loader):
  for file in env.list_templates():
    if not file.endswith('.pyc'):
      src: str          = loader.get_source(env, file)[0]
      ast: j2n.Template = env.parse(src)
      for call in ast.find_all(j2n.Call):
        # call doesn't look like a word anymore
        call = cast(j2n.Call, call)
        yield str(call.node.__dict__['name']), call

# do more with this to get the calls
def extract_macros(env, loader):
  for file in env.list_templates():
    if not file.endswith('.pyc'):
      src: str          = loader.get_source(env, file)[0]
      ast: j2n.Template = env.parse(src)
      for macro in ast.find_all(j2n.Macro):
        yield str(macro.name), macro

def parse_macros():
  macro_loader = j2.FileSystemLoader(searchpath='macros')
  macro_env = j2.Environment(loader = macro_loader)
  macro_dict = dict(extract_macros(macro_env, macro_loader))
  return macro_dict

def parse_models():
  model_loader  = j2.FileSystemLoader(searchpath='models')
  model_env = j2.Environment(loader = model_loader)
  call_list = list(extract_calls(model_env, model_loader))
  return call_list

def ref_closure(
  my_id: str,
  ref_adj_list: Dict[str, set[str]] = {},
  target: Target|None = None
):
  def inner_ref(obj_id: str):
    if my_id not in ref_adj_list:
      ref_adj_list[my_id] = {obj_id}
    else:
      ref_adj_list[my_id].add(obj_id)
    return obj_id
  return inner_ref

def src_closure(
  my_id: str,
  src_adj_list: Dict[str, set[str]] = {},
  target: Target|None = None
):
  def inner_src(src_name: str, table_name: str):
    fullname = f'{src_name}.{table_name}'
    if my_id not in src_adj_list:
      src_adj_list[my_id] = {fullname}
    else:
      src_adj_list[my_id].add(fullname)
    return fullname 
  return inner_src

def config_closure(my_id: str, config_blocks: Dict[str, Dict[str, str]]):
  def inner_config(**kwargs):
    local_conf = {key: val for key, val in kwargs.items()}
    if my_id not in config_blocks:
      config_blocks[my_id] = local_conf
    else:
      # double config block for model id? 
      pass
    return my_id 
  return inner_config

def model_name(tmpl_name: str) -> str:
  sep = os.path.sep
  pre = tmpl_name[tmpl_name.rindex(sep)+1:] if sep in tmpl_name else tmpl_name
  return pre.removesuffix('.sql')

def preprocess_models(macro_dict: dict[str, j2n.Macro], target: Target):
  model_loader = j2.FileSystemLoader(searchpath='models')
  model_env       = j2.Environment(loader=model_loader)
  res = extract_calls(model_env, model_loader)
  some = list(res)
  model_env.globals.update(
    cast(Dict[str, Any], macro_dict)
  )
  model_filenames = [
    t 
      for t in model_env.list_templates() 
      if t.endswith('.sql')
  ]
  model_templates = [
    model_env.get_template(file)
      for file in model_filenames
  ]
  ref_adj_list = {}
  src_adj_list = {}
  config_blocks = {}
  for tmp in model_templates:
    my_id = model_name(str(tmp.name))
    ref = ref_closure(my_id, ref_adj_list)
    source = src_closure(my_id, src_adj_list)
    config = config_closure(my_id, config_blocks)
    
    ctx = {
      'ref': ref,
      'source': source,
      'config': config
    }
    tmp.render(ctx)
  return ref_adj_list, src_adj_list, config_blocks

def yaml_file(dir: str, filename: str):
  for ext in ['.yml', 'yaml']:
    path = os.path.join(dir, filename + ext)
    if os.path.isfile(path):
      with open(path) as file:
        return yaml.safe_load(file)

def init_target(dir: str, target: str|None):
  proj_conf = cast(Dict[str, Any], yaml_file(dir, 'dbt_project'))
  prof_conf = cast(Dict[str, Any], yaml_file(dir, 'profiles'))
  profile_name = proj_conf['profile']
  target_name = target or prof_conf[profile_name]['target']
  return {
      'name': target_name,
      'project_name': proj_conf['name'],
      'profile_name': profile_name,
      'type': prof_conf[profile_name]['outputs'][target_name]['type'],
      'schema': prof_conf[profile_name]['outputs'][target_name]['schema'],
  }

def resource_yml_files(loader: j2.FileSystemLoader, resource_type: str):
  yamls = []
  files = loader.list_templates()
  return yamls

def main(
  target: str|None = None,
  dir:    str      = '.' 
):
  model_loader = j2.FileSystemLoader(searchpath='models')
  resource_yml_files(model_loader, 'models')
  # TARGET
  target_data: Dict[str, str] = init_target(dir, target)
  target_obj = Target(**target_data)
  # MACROS
  macro_dict = parse_macros()
  # MODELS 
  call_list = parse_models()
  #src_adj, ref_adj, conf_blocks = preprocess_models(macro_dict, target_obj)

if __name__ == '__main__':
  main()
