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
        yield file, str(call.node.__dict__['name']), call

# do more with this to get the calls
def extract_macros(env, loader):
  for file in env.list_templates():
    if not file.endswith('.pyc'):
      src: str          = loader.get_source(env, file)[0]
      ast: j2n.Template = env.parse(src)
      for macro in ast.find_all(j2n.Macro):
        yield str(macro.name), macro

def yaml_file(dir: str, filename: str):
  for ext in ['.yml', '.yaml']:
    path = os.path.join(dir, filename + ext)
    if path.endswith('schema.yaml'):
      de = 'bug'
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

# resource type is the top level tag that contains resource config info
def resource_yml_files(loader: j2.FileSystemLoader, resource_type: str):
  '''
    Returns first config block of specified resource type for all yaml files in dir
    We are getting NON rendered templates from this, compile later when resolving full model configs
  '''
  # list all templatable files in FileSystemLoader's dir
  loader_files = loader.list_templates()
  # now we want to get the yaml_file dict
  config_blocks = [
    (file, result[resource_type])
      for file in loader_files
      if (result := cast(Dict[str, Any],
        yaml_file(loader.searchpath[0], file[:file.rindex('.')])
      )) is not None
  ]
  return config_blocks

def conf_calls(call_list: list[tuple[str, str, j2n.Call]]):
  ''' filter call list to only config() funcs 
      return dict of config args per model
  '''
  return {
    conf[0]: {kwarg.key: str(cast(j2n.Const, kwarg.value).value) for kwarg in conf[2].kwargs}
      for conf in call_list
      if conf[1] == 'config'
  }

def main(
  target: str|None = None,
  dir:    str      = '.' 
):
  # MACROS
  macro_loader = j2.FileSystemLoader(searchpath='macros')
  macro_env = j2.Environment(loader=macro_loader)
  macro_dict = dict(
    extract_macros(macro_env, macro_loader)
  )
  # TARGET
  target_data: Dict[str, str] = init_target(dir, target)
  target_obj = Target(**target_data)
  # MODELS
  model_loader = j2.FileSystemLoader(searchpath='models')
  model_env = j2.Environment(loader=model_loader)
  model_env.globals.update(
    cast(Dict[str, Any], macro_dict)
  )
  # MODEL CONFIGS
  model_yml_confs = resource_yml_files(model_loader, 'models')
  call_list = list(
    extract_calls(model_env, model_loader)
  )
  ccs = conf_calls(call_list)
  ''' 
    now that we have the project target info, yaml config blocks, and the config block calls
    we need to unify the model configs. 
    the sql compilation step only relies on creating fully qualified table names using the configs.
    materializations and other opts relevant to Nodes used later

    design goal: compile sql templates into target dir. create Model Nodes separately
                 second compilation step to marry Model Nodes and compiled sql to dataframe
  '''


  return 0

if __name__ == '__main__':
  main()
