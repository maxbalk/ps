# TODO 

## template compilation
1) Create a jinja environment extension to supply
all custom tags that are used within blocks

so far the only custom tag I know we use is:

{% test testname(args) %}
{% endtest %}

## Resource types
we will support:
 - models
 - macros
 - tests
    - and later, builtin tests like:
        - not_null
        - unique
        - accepted_values
        - relationships

### project flow
1) parse profiles config for
    - target name, other data
        - macros dont need target since theyre not rendered yet
    - maybe environment variables..
        - theyre used for remote connection keys

2) project config for 
    - resource locations
    - clean/target
    - vars

3) parse yaml files for resource configs
    - specs 
        - resource configs come in hierarchical dicts
        - more specific config opts override less specific
        - dir keys must contain dicts
        - configs specific to one model use a `- name: <modelname>` 
            format instead of a plain dir key
    - steps 
        - keep yml config dicts as is 
        - take list of model files, match dirs path to keys 
        - create config opt dict first with dirkeys, then -name opts 
            and finally from the config calls

