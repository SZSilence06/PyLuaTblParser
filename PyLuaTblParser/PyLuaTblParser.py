from copy import deepcopy
from cStringIO import StringIO
from string import printable

_lua_keyword = ['and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'if', \
                'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', \
                'while']

_escape_dict = {'a':'\a', 'b':'\b', 'f':'\f', 'n':'\n', 'r':'\r', 't':'\t', 'v':'\v', '\\':'\\', \
                '"':'"', '\'':'\'', 'z':'\z', '\n':'\n'}
_escape_dict_keys = _escape_dict.keys()

_escape_dict_back = {'\a':'a', '\b':'b', '\f':'f', '\n':'n', '\r':'r', '\t':'t', '\v':'v', '\\':'\\'}
_escape_dict_back_keys = _escape_dict_back.keys()

_TOKEN_UNKNOWN = 0
_TOKEN_NAME = 1
_TOKEN_NUMBER = 2
_TOKEN_STRING = 3
_TOKEN_BOOLEAN = 4
_TOKEN_NONE = 5
_TOKEN_TABLE = 6

_INDENT_STEP = 4

class LuaParseError(Exception):
    pass

def _char2hex(c):
    try:
        return int(c, 16)
    except ValueError:
        return None

def _char2int(c):
    try:
        return int(c)
    except ValueError:
        return None

class _Token:
    def getType(self):
        return self._type

class _TOKEN_UNKNOWN:
    def __init__(self):
        self._type = _TOKEN_UNKNOWN

class _TokenName(_Token):
    def __init__(self, strName):
        self._type = _TOKEN_NAME
        self._strName = strName

    def getValue(self):
        return self._strName

class _TokenNumber(_Token):
    def __init__(self, number):
        self._type = _TOKEN_NUMBER
        self._value = number

    def getValue(self):
        return self._value

class _TokenString(_Token):
    def __init__(self, pystr):
        self._type = _TOKEN_STRING
        self._value = pystr

    def getValue(self):
        return self._value

class _TokenBoolean(_Token):
    def __init__(self, value):
        self._type = _TOKEN_BOOLEAN
        self._value = value

    def getValue(self):
        return self._value

class _TokenNone(_Token):
    def __init__(self):
        self._type = _TOKEN_NONE

    def getValue(self):
        return None

class _TokenTable(_Token):
    def __init__(self, t):
        self._type = _TOKEN_TABLE
        self._value = t

    def getValue(self):
        return self._value

class _Text:
    def __init__(self, text, lIndex, rIndex):
        if(isinstance(text, _Text)):
            self._text = text._text
        else:
            self._text = text
        self._start = lIndex
        self._end = rIndex
        self._length = rIndex - lIndex
        self._current = self._start

    def trim(self):
        index = self._current
        while(index < self._length):
            c = self._text[index]
            if(c.isspace() is False):
                break
            index += 1 
        self._current = index

    def trimComments(self):
        if(self.isCommentNext() == False):
            return

        self.move(2)
        (islongstring, longstring) = self.tryNextLongString()
        if(islongstring):
            return

        c = self.nextChar()
        while c is not None:
            self.moveNext()
            if c == '\n':
                break
            c = self.nextChar()
    
    def trimAll(self):
       self.trim()
       while self.isCommentNext() is True:
           self.trimComments()
           self.trim()       

    def isCommentNext(self):
        oldCurrent = self._current
        c = self.nextChar()
        if(c is not '-'):
            return False
        self.moveNext()
        c = self.nextChar()
        if(c is not '-'):
            self._current = oldCurrent
            return False
        self._current = oldCurrent
        return True

    def nextChar(self):
        if(self._current >= self._end):
            return None
        result = self._text[self._current]
        return result

    def nextTokenText(self):
        token = self.tryNextTokenText()
        self._current = token._end
        return token

    def tryNextTokenText(self):
        self.trimAll()
        start = self._current
        index = self._current
        while(index < self._length):
            c = self._text[index]
            if(c.isspace()):
                break
            index += 1 
        end = index
        return _Text(self._text, start, end)

    def nextTokenChar(self):
        self.trimAll()
        return self._text[self._current]

    def nextTokenBefore(self, clist):
        self.trimAll()

        (islongstring, longstring) = self.tryNextLongString()
        if islongstring:
            return longstring

        c = self.nextTokenChar()
        if(c == '\'' or c == '\"'):
            read_string = self.nextString()
            token = _TokenString(read_string)
            return token
            
        start = self._current
        while True:
            c = self.nextChar()
            if(c is None):
                raise LuaParseError('Expecting ' + str(clist) +', but reached end of the text.')
            if c.isspace() or c in clist or self.isCommentNext():
                break
            self.moveNext()

        end = self._current 
        text = _Text(self, start, end)
        return _Text._parseTokenFromText(text)

    def nextString(self):
        self.trimAll()
        start = self._current
        index = self._current + 1
        while(index < self._length):
            if(self._text[index] == '\\'):
                index += 2
            else:
                if(self._text[index] == self._text[start]):
                    index += 1
                    break
                index += 1
        else:
            raise LuaParseError("End of string not found.")
        end = index
        self._current = end
        return self._parseString(self._text[start:end])

    def tryNextLongString(self):
        oldCurrent = self._current
        self.trimAll()
        if(self.nextChar() is not '['):
            self._current = oldCurrent
            return (False, None)
        self.moveNext()
        c = self.nextChar()
        if(c is not '[' and c is not '='):
            self._current = oldCurrent
            return (False, None)

        level = self.computeLongStringLevel()                    
        textBegin = self._current
        textEnd = textBegin
        while self.isEndOfLongString(level) == False:
            textEnd += 1
            self.moveNext()
        return (True, _TokenString(self._text[textBegin:textEnd]))
           
    def computeLongStringLevel(self):
        level = 0
        while True:
            c = self.nextChar()
            self.moveNext()
            if(c is '['):
                break
            if(c is not '='):
                raise LuaParseError("Expecting '=' or '[' before." + c)
            level += 1
        return level

    def isEndOfLongString(self, level):
        oldCurrent = self._current
        c = self.nextChar()
        if c is not ']':
            return False
        
        self.moveNext()
        c = self.nextChar()
        if c is not ']' and c is not '=':
            self._current = oldCurrent
            return False

        endLevel = 0
        while True:
            c = self.nextChar()
            self.moveNext()
            if(c is ']'):
                break
            if(c is not '='):
                self._current = oldCurrent
                return False
            endLevel += 1

        if level == endLevel:
            return True
        self._current = oldCurrent
        return False


    def moveNext(self):
        if(self._current >= self._end):
            raise Exception('Already reaches the end of the text!')
        self._current += 1

    def move(self, step):
        self._current += step

    def length(self):
        return self._length

    def __str__(self):
        return self._text[self._start:self._end]

    @staticmethod
    def _parseTokenFromText(text):
        tokenStr = str(text)
        if(len(tokenStr) == 0):
            return None
        if(tokenStr == 'nil'):
            return _TokenNone()
        if(tokenStr == 'true'):
            return _TokenBoolean(True)
        if(tokenStr == 'false'):
            return _TokenBoolean(False)

        (isNumber, number) = _Text._tryParseNumber(tokenStr)
        if(isNumber):
            return _TokenNumber(number)
        
        if _Text._isLuaName(tokenStr):
            return _TokenName(tokenStr)

        message =  'Unrecognized token \'' + tokenStr + '\''
        raise LuaParseError(message)

    @staticmethod
    def _tryParseNumber(s):
        if(len(s) > 2 and s[0] is '0' and s[1] in ['x', 'X']):
            try:
                number = int(s, 16)
                return(True, number)
            except Exception:
                try:
                    number = float.fromhex(s)
                    return(True, number)
                except Exception:
                    pass
        try:
            number = int(s)
            return(True, number)
        except Exception:
            try:
                number = float(s)
                return(True, number)
            except Exception:
                return (False, None)

    @staticmethod
    def _parseString(s):
        chars = []
        length = len(s) - 1
        index = 0
        while index < length - 1:
            index += 1
            c = s[index]
            if c != '\\':
                chars.append(c)
                continue
            index += 1
            c = s[index]
            if c in _escape_dict_keys:
                chars.append(_escape_dict[c])
            elif c is 'z':
                while c.isspace() is False:
                    index += 1
                    c = s[index]
                index -= 1
            elif c is 'x':
                if(index + 2 >= length):
                    raise LuaParseError("There must be at least two hex numbers after '\\x'!")
                hex1 = _char2hex(s[index + 1])
                hex2 = _char2hex(s[index + 2])
                if(hex1 is None or hex2 is None):
                    raise LuaParseError("There must be at least two hex numbers after '\\x'!")
                chars.append(chr(hex1 * 16 + hex2))
                index += 2
            elif c.isdigit():
                digit_count = 0
                while digit_count < 3:
                    digit_count += 1
                    index_2 = index + digit_count
                    if(index_2 >= length or not s[index_2].isdigit()):
                        break
                asciiCode = 0
                for i in range(digit_count):
                    asciiCode *= 10
                    asciiCode += _char2int(s[index + i])
                chars.append(chr(asciiCode))
                index += digit_count - 1
            else:
                chars.append(c)
        return ''.join(chars)

    @staticmethod
    def _isLuaName(s):
        if s[0].isdigit():
            return False
        for c in s:
            if(c.isalpha() == False and c != '_'):
                return False
        if s in _lua_keyword:
            return False
        return True

class PyLuaTblParser:
    #----------constructor--------------------
    def __init__(self):
        self._dict = {}
        pass

    #----------public functions---------------
    def load(self, s):
        ''' Load lua table s. 
        No return value.
        Throws LuaParseError when the table has grammar errors.    
        '''
        text = s.strip()
        if(len(text) == 0):
            return
        self._text = _Text(text, 0, len(text))
        self._dict = self._nextTable().getValue()

    def dump(self):
       ''' Dump a string according to the content of the lua table.
       Returns the dumped string.
       '''
       self._indent = 0 
       output = StringIO()
       self._dumpItem(output, self._dict)
       return output.getvalue()

    def loadLuaTable(self, f):
        '''Read Lua table from file f.
        No return value.
        Throws LuaParseError when the table has grammar errors.    
        '''
        infile = open(f)
        self.load(infile.read())
        infile.close()

    def dumpLuaTable(self, f):
        ''' Dump the content of the table to the file f in Lua table format.
        If the file already exists, rewrite it.
        Throws IOError when failed to write file.
        '''
        outfile = open(f, 'w')
        outfile.write(self.dump())
        outfile.close()

    def loadDict(self, d):
        ''' Read contents of a dict d an save it into the class.
        Only handle keys with types as number and string.
        '''
        self._dict = self._loadDict(d)

    def dumpDict(self):
        '''Returns a dict containing contents of the class.
        '''
        return deepcopy(self._dict)

    def update(self, d):
        '''Update content of the lua table according to dict d like dict.update()
        '''
        for key, value in d.iteritems():
            self[key] = value

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        if((isinstance(key, int) or isinstance(key, float) or isinstance(key, basestring)) 
            and value is not None):
            if(isinstance(value, dict)):
                self._dict[key] = self._loadDict(value)
            elif(isinstance(value, list)):
                self._dict[key] = self._loadList(value)
            else:
                self._dict[key] = value
    #----------private functions---------------
    def _nextTable(self):
        self._text.trimAll()
        c = self._text.nextChar()
        if(c != '{'):
            message =  'Expecting \'{\' when parsing table. Got \'' + c + '\''
            raise LuaParseError(message)
        self._text.moveNext()
        self._text.trimAll()
        if(self._text.nextChar() == '}'):
            self._text.moveNext()
            return _TokenTable([])
        
        table = self._nextFieldList()
        if(self._text.nextChar() != '}'):
            message =  'Expecting \'}\' when parsing table. Got \'' + str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)
        self._text.moveNext()

        if(isinstance(table, dict)):
            self._clearNilKey(table)
        return _TokenTable(table)

    def _nextFieldList(self):
        result = {}
        arrayIndex = 1
        hasKey = False
        while True:
            omit = False
            (key, value) = self._nextField()
            if(key is None):
                key = arrayIndex
                arrayIndex += 1
            else:
                hasKey = True
                if(value is None or (isinstance(key, int) and  key < arrayIndex)):
                    omit = True
            if(omit is False):
                result[key] = value
            hasNextField = self._hasNextField()
            if(hasNextField == False):
                break
        if(hasKey):
            return result
        return result.values()

    def _hasNextFieldSeparator(self):
        self._text.trimAll()
        c = self._text.nextChar()
        if(c == ',' or c == ';'):
            self._text.moveNext()
            return True
        elif(c == '}'):
            return False
        else:
            message =  'Expecting \',\' or \';\' when seeking for next field separator. Got \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)

    def _hasNextField(self):
        self._text.trimAll()
        hasNextSeparator = self._hasNextFieldSeparator()
        if(hasNextSeparator):
            self._text.trimAll()
            if(self._text.nextChar() != '}'):
                return True
        return False

    def _nextField(self):
        key = None
        value = None
        c = self._text.nextTokenChar()
        if(c == '{'):
            key = self._nextTable()
        elif(c == '['):
            (islongstring, longstring) = self._text.tryNextLongString()
            if(islongstring):
                key = longstring
            else:   
                self._text.moveNext()
                key = self._nextIndex()
                if(self._text.nextTokenChar() != '='):
                    raise LuaParseError('Expecting \'=\' before \'' + str(self._text.nextChar()) + '\'')
                self._text.moveNext()
                value = self._nextValue()
                return (key, value)
        else:
            key = self._text.nextTokenBefore(['=', ',', ';', '}'])
            if(key is None):
                message =  'Expecting field or key before \'' + \
                    str(self._text.nextChar()) + '\''
                raise LuaParseError(message)
        c = self._text.nextTokenChar()
        if(c == '='):
            self._text.moveNext()
            key = self._asName(key)
            value = self._nextValue()
        else:
            value = self._asValue(key)
            key = None
        return (key, value)

    def _nextIndex(self):
        token = self._text.nextTokenBefore([']'])
        if(token is None):
            message =  'Expecting index before \'' + \
                str(self._text.nextChar()) + '\''
            raise LuaParseError(message)
        if(self._text.nextTokenChar() != ']'):
            message =  'Expecting \']\' before \'' + \
                str(self._text.nextChar()) + '\''
            raise LuaParseError(message)
        self._text.moveNext()

        if(token.getType() == _TOKEN_NONE):
            message =  'Table key cannot be nil! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)    
        if(token.getType() == _TOKEN_BOOLEAN):
            message =  'Table key cannot be boolean! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)
        if(token.getType() == _TOKEN_NAME):
            message =  'Table key cannot be name! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)    
        return token.getValue()
    
    def _nextValue(self):
        value = None
        token = None
        c = self._text.nextTokenChar()
        if(c == '{'):
            value = self._nextTable().getValue()
        else:
            token = self._text.nextTokenBefore([',', ';', '}'])
            if(token is None):
                message =  'Expecting value before \'' + \
                    str(self._text.nextChar()) + '\''
                raise LuaParseError(message)         
            value = self._asValue(token)
        return value

    def _nextString(self):
        return self._text.nextString()

    @staticmethod
    def _asValue(token):
        if(token.getType() == _TOKEN_NAME):
            message =  'Lua name cannot appear as value! At \'' + \
                token.getValue() + '\''
            raise LuaParseError(message)
        return token.getValue()  

    def _asName(self, token):
        if(token.getType() == _TOKEN_TABLE):
            message =  'Table key cannot be table! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)
        if(token.getType() == _TOKEN_BOOLEAN):
            message =  'Table key cannot be boolean! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)
        if(token.getType() == _TOKEN_NONE):
            message =  'Table key cannot be nil! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)    
        if(token.getType() == _TOKEN_BOOLEAN):
            message =  'Table key cannot be boolean! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)   
        if(token.getType() == _TOKEN_NUMBER):
            message =  'Table key cannot be number! Got ' + str(token.getValue()) + ' Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message) 
        if(token.getType() == _TOKEN_STRING):
            message =  'Table key cannot be string! Before \'' + \
                str(self._text.nextTokenText()) + '\''
            raise LuaParseError(message)
        return token.getValue()

    def _dumpItem(self, stream, item):
        if(isinstance(item, list)):
            self._dumpList(stream, item)
        elif(isinstance(item, dict)):
            self._dumpDict(stream, item)
        elif(isinstance(item, basestring)):
            self._dumpString(stream, item)
        elif(item is True):
            stream.write('true')
        elif(item is False):
            stream.write('false')
        elif(item is None):
            stream.write('nil')
        else:
            stream.write(str(item))

    def _dumpString(self, stream, s):
        length = len(s)
        stream.write('\'')
        for index in xrange(length):
            c = s[index]
            if c == "'":
                stream.write('\\')
                stream.write(c)
            elif c in _escape_dict_back_keys:
                stream.write('\\')
                stream.write(_escape_dict_back[c])
            elif c not in printable:
                stream.write('\\')
                stream.write(str(ord(c)))
            else:
                stream.write(c)
        stream.write('\'')

    def _dumpList(self, stream, l):
        stream.write('{ ')
        length = len(l)
        for index in xrange(length):
            self._dumpItem(stream, l[index])
            if(index < length - 1):
                stream.write(',')
            stream.write(' ')
        stream.write('}')

    def _dumpDict(self, stream, d):
        stream.write('{ ')
        length = len(d)
        k = d.keys()
        v = d.values()
        if(length > 0):
            self._changeLine(stream, _INDENT_STEP)
        for index in xrange(length):
            stream.write('[')
            self._dumpItem(stream, k[index])
            stream.write('] = ')
            self._dumpItem(stream, v[index])
            if(index < length - 1):
                stream.write(',')
                self._changeLine(stream, 0)
            else:
                self._changeLine(stream, -_INDENT_STEP)
        stream.write('}')

    def _changeLine(self, stream, indent):
        stream.write('\n')
        self._indent += indent
        for i in xrange(self._indent):
            stream.write(' ')

    @staticmethod
    def _loadDict(d):
        result = {}
        for key, value in d.iteritems():
            v = None
            if((isinstance(key, int) or isinstance(key, float) or isinstance(key, basestring))
                and value is not None):
                if(isinstance(value, dict)):
                    v = PyLuaTblParser._loadDict(value)
                elif(isinstance(value, list)):
                    v = PyLuaTblParser._loadList(value)
                else:
                    v = value
                result[key] = v
        return result

    @staticmethod
    def _loadList(l):
        result = []
        for item in l:
            if isinstance(item, dict):
                result.append(PyLuaTblParser._loadDict(item))
            elif(isinstance(item, list)):
                result.append(PyLuaTblParser._loadList(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def _clearNilKey(d):
        nilKeys = []
        for key, value in d.iteritems():
            if value is None:
                nilKeys.append(key)
        for key in nilKeys:
            d.pop(key)

if __name__ == '__main__':
    a1 = PyLuaTblParser()
    a2 = PyLuaTblParser()
    a3 = PyLuaTblParser()

    test_str = r'{array = {65,23,5,},dict = {mixed = {43,54.33,false,9,string = "value",},array = {3,6,4,},string = "value",},}'
    a1.load(test_str)
    d1 = a1.dumpDict()

    a2.loadDict(d1)
    file_path = "dump.lua"
    a2.dumpLuaTable(file_path)
    a3.loadLuaTable(file_path)

    d3 = a3.dumpDict()
    



    
    