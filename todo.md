# TODO 

## template compilation
1) Create a jinja environment extension to supply all 
custom tags that are used within blocks

so far the only custom tag I know we use is:

{% test testname(args) %}
{% endtest %}


### project flow
1) define yaml config locations for:
 - model
 - macros
 - tests
 - docs
 - target

parse yaml config for above locations

2) jinja loader required for:
 - macros
 - models
 - tests

