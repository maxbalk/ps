{{
  config(
    bank_transfer="credit_card", 
    gift_card="some_val"
  )
}}

select * 
from {{source('somesrcname', 'sometablename') }} 

