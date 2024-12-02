
# Dev lifecycle
  - Local:
    - write transformations
    - unit test using their schemas from dbx
    - smoke the entire dag
  - Dev:
    - dev workspace for user prototyping
    - not for this project
  - Staging:
    - run  bon staging copy of data 
    - run characteristic checks
  - Prod:
    - produce prod data
    - WAP: run output quality checks
  
# project objectives
## tenets to speed up the developer experience
  - Enforce standardizations meet schemas
  - Automate standardization transformations
  - Test data characteristics of std and enriched
  - Data quality outputs and tests

# program interface
 -  main - run transformations
    - env: local, staging, prod
    - list: which transformations
    - upstream/downstream: include parents or children
  
## utils interface
  - "compile"
    - for templating
    - unit tests model design
    - custom variables: {{}} can be given to the template
      with the render context, but custom tags {%%} require
      an extension to be written.
  - unit test
    - tests output structure and if code works 
  - generate model, database and table
  - manage schemas - TBD on how

# transformation interface and design
  - sql or python model
    - jinja templated sql
    - pyspark dataframe
  - compile transformation subclasses into configured models

## developer interface
  - create a python module
  - define config parameters in a config method
    
