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
    1) target name, other data
        - macros dont need target since theyre not rendered yet
    2) maybe environment variables..
        - theyre used for remote connection keys

2) project config for 
    1) resource locations
    2) clean/target
    3) vars

2) jinja loader required for:
 - macros
 - models
 - tests

