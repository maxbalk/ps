from doctest import master

import enum
import os
from os.path import isfile
import resource
from typing import Any, NamedTuple, cast

import jinja2 as j2
import jinja2.nodes as j2n
import yaml

type CallList = list[tuple[str, str, j2n.Call]]
type ConfCalls = dict[str, dict[str, str]]

class Target(NamedTuple):
  name: str 
  project_name: str 
  profile_name: str 
  type: str 
  schema: str

def extract_calls(
  env: j2.Environment,
  loader: j2.FileSystemLoader,
  template_files: list[str]
) -> CallList:
  call_list: list[tuple[str, str, j2n.Call]] = []
  for file in template_files:
    src: str = loader.get_source(env, file)[0]
    ast: j2n.Template = env.parse(src)
    calls = [
      (file, call.node.__dict__['name'], call)
      for call in ast.find_all(j2n.Call)
    ]
    call_list.extend(calls)
  return call_list

def conf_calls(
  call_list: CallList
) -> ConfCalls:
  ''' filter call list to only config() funcs 
      return dict of config args per model
  '''
  conf_dict: ConfCalls = {}
  conf_list = [call for call in call_list if call[1] == 'config']
  for conf in conf_list:
    if conf[0] in conf_dict:
      raise j2.TemplateError(f"detected multiple config calls in {conf[0]}")
    conf = {
      conf[0].split(os.path.sep)[-1]:  
      { 
        kwarg.key: str(kwarg.value) 
        for kwarg in conf[2].kwargs 
      }
    }
    conf_dict |= conf
  return conf_dict

def extract_macros(
  env: j2.Environment,
  loader: j2.FileSystemLoader,
  template_files: list[str]
) -> dict[str, j2n.Macro]:
  macro_dict: dict[str, j2n.Macro] = {}
  for file in template_files:
    src: str = loader.get_source(env, file)[0]
    ast: j2n.Template = env.parse(src)
    macros = {
      macro.name: macro
      for macro in ast.find_all(j2n.Macro)
    }
    intersect = macro_dict.keys() & macros.keys()
    if intersect:
      raise j2.TemplateError(
        f"""
          detected duplicate macros in the searchpath(s): {','.join(loader.searchpath)}
          duplicate macro names: {intersect}
        """
      )
    macro_dict.update(macros)
  return macro_dict

def ext_templates(
    env: j2.Environment,
    ext: str|tuple[str, ...]
):
  return [
    tmp 
    for tmp in env.list_templates() 
    if tmp.endswith(ext)
  ]

def yaml_file(
  dir: str,
  filename: str
) :
  for ext in ['.yml', '.yaml']:
    path = os.path.join(dir, filename + ext)
    if os.path.isfile(path):
      with open(path) as file:
        data = yaml.safe_load(file)
        return dict(data)
  return {}

def init_target(
  dir: str,
  target: str|None,
  proj_conf: dict[Any, Any],
  prof_conf: dict[Any, Any]
):
  profile_name = proj_conf['profile']
  target_name = target or prof_conf[profile_name]['target']
  return {
      'name': target_name,
      'project_name': proj_conf['name'],
      'profile_name': profile_name,
      'type': prof_conf[profile_name]['outputs'][target_name]['type'],
      'schema': prof_conf[profile_name]['outputs'][target_name]['schema'],
  }

def resource_yaml_files(
  loader: j2.FileSystemLoader,
  resource_type: str,
  conf_files: list[str]
) -> dict[str, Any]:
  '''
    Returns first config block of specified resource type for all yaml files in dir
    We are getting NON rendered templates from this, compile later when resolving full model configs
  '''
  # list all templatable files in FileSystemLoader's dir
  # now we want to get the yaml_file dict
  res = {
      file: result[resource_type]
      for file in conf_files
      if (result := yaml_file(loader.searchpath[0], file[:file.rindex('.')])
      ) is not None
      and resource_type in result
  }
  return res


def yaml_name_tags(
  yaml_confs: dict[str, Any]
):
  nametagconfs = {}
  for filename, resources in yaml_confs.items():
    nametagconfs |= {conf['name']: conf for conf in resources if 'name' in conf}
  return nametagconfs

def yaml_resource_paths(
  project_conf: dict[str, Any],
  resource_type: str
):
  project_name = project_conf['name']
  if not resource_type in project_conf:
    raise yaml.YAMLError(f'resource type key {resource_type} does not exist in the')
  resources = project_conf[resource_type]
  if not isinstance(resources, (dict)):
    raise yaml.YAMLError(f'resource conf should be dict, got {type(resources)}')
  return resources

def path_opts(
  path_conf: dict[str, Any]
):
  return {
    key.removeprefix('+'): val 
    for key, val in path_conf.items() 
    if key.startswith('+')
  }

def apply_path_confs(
  resource_list: list[str],
  resource_path_confs: dict[str, Any],
  project_name: str
):
  universal_opts = path_opts(resource_path_confs)
  proj_confs = resource_path_confs[project_name] if project_name in resource_path_confs else resource_path_confs
  res_confs = {}
  for resource in resource_list:
    dirs = resource.split(os.path.sep)[:1]
    res_name = resource.split(os.path.sep)[-1]
    path_confs = proj_confs
    res_conf = universal_opts | path_opts(path_confs)
    while dirs:
      curdir = dirs.pop(0)
      if curdir not in path_confs:
        break
      dir_conf = path_confs.pop(curdir)
      res_conf |= path_opts(dir_conf)
    res_confs |= {res_name.removesuffix(('.sql')): res_conf}
  return res_confs

def apply_specific_confs(
  base_confs: dict[str, dict[str, Any]],
  specific_confs: dict[str, Any]
):
  spec_confs = base_confs
  for res_name, res_conf in specific_confs.items():
    stripped = res_name.removesuffix(('.sql'))
    if stripped in spec_confs:
      spec_confs[stripped] |= res_conf
    else:
      spec_confs |= {stripped: res_conf}
  return spec_confs


def create_target(
  dir: str,
  target: str|None,
  proj_conf: dict[Any, Any],
  prof_conf: dict[Any, Any]
):
  target_data: dict[str, str] = init_target(
    dir, 
    target,
    proj_conf,
    prof_conf
  )
  target_obj = Target(**target_data)
  return target_obj

def create_macro_dict(
  macro_env: j2.Environment,
  macro_loader: j2.FileSystemLoader
):
  macro_templates = ext_templates(macro_env, ('sql', 'jinja2'))
  macro_dict = extract_macros(
    macro_env,
    macro_loader,
    macro_templates
  )
  return macro_dict

def apply_model_confs(
  model_env: j2.Environment,
  model_loader: j2.FileSystemLoader,
  model_list: list[str],
  project_conf: dict[Any, Any],
  target_obj: Target,
  dir: str
):
  conf_files = ext_templates(model_env, ('yml', 'yaml'))
  yaml_confs = resource_yaml_files(
    model_loader,
    'models',
    conf_files
  )
  path_confs = yaml_resource_paths(
    project_conf,
    'models'
  )
  name_tag_confs = yaml_name_tags(yaml_confs)
  call_list: CallList = extract_calls(model_env, model_loader, model_list)
  conf_dict: ConfCalls = conf_calls(call_list)

  path_confs = apply_path_confs(
    model_list,
    path_confs,
    target_obj.project_name
  )
  named_confs = apply_specific_confs(
    path_confs,
    name_tag_confs
  )
  called_confs = apply_specific_confs(
    named_confs,
    conf_dict
  )
  return called_confs



def main(
  target_name: str|None = None,
  dir:    str      = '.' 
):
  # TARGET
  project_conf = yaml_file(dir, 'dbt_project')
  profile_conf = yaml_file(dir, 'profiles')
  target_obj = create_target(dir, target_name, project_conf, profile_conf)
  # MACROS
  macro_loader = j2.FileSystemLoader(searchpath=os.path.join(dir, 'macros'))
  macro_env = j2.Environment(loader=macro_loader)
  macro_dict = create_macro_dict(macro_env, macro_loader)
  # macro_files = sql_templates(macro_env)
  # MODELS
  model_loader = j2.FileSystemLoader(searchpath=os.path.join(dir, 'models'))
  model_env = j2.Environment(loader=model_loader)
  model_env.globals.update(
    cast(dict[str, Any], macro_dict)
  )
  model_list = ext_templates(model_env, 'sql')
  ## MODEL CONFIGS
  model_confs = apply_model_confs(
    model_env,
    model_loader,
    model_list,
    project_conf,
    target_obj,
    dir
  )

  model_yamls = ext_templates(model_env, ('yml', 'yaml'))
  src_confs = resource_yaml_files(
    model_loader,
    'sources',
    model_yamls
  )
  sources_files = yaml_name_tags(src_confs)
  src_tables = {

  }
  #table_nametags = yaml_name_tags(src_raw)
  #table_specs = apply_specific_confs({}, table_nametags)

  return 0

if __name__ == '__main__':
  main(dir='dbt_project')
