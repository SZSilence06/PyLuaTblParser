# PyLuaTblParser

This is a Lua table parser written in Python. This package is for some assignment.

## Features

This parser can parse Lua table with grammar as follows:

* tableconstructor ::= ‘{’ [fieldlist] ‘}’
* fieldlist ::= field {fieldsep field} [fieldsep]
* field ::= ‘[’ index ‘]’ ‘=’ exp | Name ‘=’ exp | exp
* fieldsep ::= ‘,’ | ‘;’
* exp ::= nil | false | true
* exp ::= Number
* exp ::= String
* exp ::= tableconstructor
* index ::= Number
* index ::= String

This parser is able to deal with:
* Strings as follows
```Lua
'A simple string'
"Another simple string"
'\97lo\10\04923"'
[[This is a long string]]
[===[This is a more complicated long string]=]===]
[=[
    multi-line
    long string
]=]
```
* Comments
```Lua
-- single line comment
--[[long string comment]]
--[=[
    multi-line 
    comment
]=]
{--[==[embedded comment]==] name='Illya'}
```
* Lua numbers
* Any valid table constructor grammar!

## Usage
```Python
from PyLuaTblParser import PyLuaTblParser, LuaParseError
import traceback

a1 = PyLuaTblParser()
a2 = PyLuaTblParser()
a3 = PyLuaTblParser()

try:
    test_str = '''{array = {65,23,5,},dict = {mixed = {43,54.33,false,9,string = "value",},
    array = {3,6,4,},string = "value",},}'''

    file_path = 'table.lua'

    a1.load(test_str)  # load Lua table from string
    a2.loadLuaTable(file_path) # load Lua table from file

    print a1.dump() # dump as string in Lua table format
    a1.dumpLuaTable('dump.lua') # dump to file  
        
    d1 = a1.dumpDict() # dump as Python dict
    a3.loadDict(d1)    # load from Python dict

    a1['string'] = 'another value' # modify the content of the Lua table
    print a1['string']  # get the content of the Lua table

    a1.update({'string' : 'updated value'}) # update the content of the Lua table similarly to dict.update()
```

** Acknowledgements

Thanks to <a href="https://github.com/william-cheung/Lua-Table-Parser">Cheung</a> for the idea and test cases.