from copy import deepcopy

_trim_separators = [' ', '\n', '\t']
_lua_keyword = ['and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'if', \
                'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', \
                'while']

_TOKEN_UNKNOWN = 0
_TOKEN_NAME = 1
_TOKEN_NUMBER = 2
_TOKEN_STRING = 3

class LuaParseError(Exception):
    pass

class _Token:
    def __init__(self):
        self._type = _TOKEN_UNKNOWN

    def getType(self):
        return self._type

class _TokenName(_Token):
    def __init__(self, text):
        self._type = _TOKEN_NAME
        self._text = text

    def getValue(self):
        return str(text)

class _TokenString(_Token):
    def __init__(self, text):
        self._type = _TOKEN_STRING
        self._text = text

    def getValue(self):
        return str(text)

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
            if(c not in _trim_separators):
                break
            index += 1 
        self._current = index

    def nextChar(self):
        if(self._current >= self._end):
            raise Exception('Already reaches the end of the text!')
        result = self._text[self._current]
        return result

    def nextToken(self):
        token = self.tryNextToken()
        self._current = token._end
        return token

    def tryNextToken(self):
        self.trim()
        start = self._current
        index = self._current
        while(index < self._length):
            c = self._text[index]
            if(c in _trim_separators):
                break
            index += 1 
        end = index
        return _Text(self._text, start, end)

    def nextTokenChar(self):
        self.trim()
        return self._text[self._current]

    def nextTokenBefore(self, clist):
        self.trim()
        start = self._current
        index = self._current
        while(index < self._length and self._text[index] not in clist and self._text[index] not in _trim_separators):
            index += 1 
        end = index 
        self._current = index
        return _Text(self, start, end)

    def nextString(self):
        self.trim()
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
        return eval(self._text[start:end])

    def moveNext(self):
        self._current += 1

    def move(self, step):
        self._current += step

    def length(self):
        return self._length

    def __str__(self):
        return self._text[self._start:self._end]

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
        self._text = _Text(text, 0, len(text))
        self._dict = self._nextTable()
        pass

    def dump(self):
       ''' Dump a string according to the content of the lua table.
       Returns the dumped string.
       '''
       pass

    def loadLuaTable(self, f):
        '''Read Lua table from file f.
        No return value.
        Throws LuaParseError when the table has grammar errors.    
        '''
        infile = open(f)
        self.load(f.read())
        f.close()

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
        self._dict = deepcopy(d)
        pass

    def dumpDict(self):
        '''Returns a dict containing contents of the class.
        '''
        return deepcopy(self._dict)

    #----------private functions---------------
    def _nextTable(self):
        self._text.trim()
        c = self._text.nextChar()
        if(c != '{'):
            message =  'Expecting \'{\' when parsing table. Got \'' + str(self._text.nextToken()) + '\''
            raise LuaParseError(message)
        self._text.moveNext()
        self._text.trim()
        if(self._text.nextChar() == '}'):
            return {}
        
        result = self._nextFieldList()
        if(self._text.nextChar() != '}'):
            message =  'Expecting \'}\' when parsing table. Got \'' + str(self._text.nextToken()) + '\''
            raise LuaParseError(message)
        self._text.moveNext()
        return result

    def _nextFieldList(self):
        result = {}
        arrayIndex = 1
        hasKey = False
        while True:
            (key, value) = self._nextField()
            if(key is None):
                key = arrayIndex
                arrayIndex += 1
            else:
                hasKey = True
            result[key] = value
            hasNextField = self._hasNextField()
            if(hasNextField == False):
                break
        if(hasKey):
            return result
        return result.values()

    def _hasNextFieldSeparator(self):
        self._text.trim()
        c = self._text.nextChar()
        if(c == ',' or c == ';'):
            self._text.moveNext()
            return True
        elif(c == '}'):
            return False
        else:
            message =  'Expecting \',\' or \';\' when seeking for next field separator. Got \'' + \
                str(self._text.nextToken()) + '\''
            raise LuaParseError(message)

    def _hasNextField(self):
        self._text.trim()
        hasNextSeparator = self._hasNextFieldSeparator()
        if(hasNextSeparator):
            self._text.trim()
            if(self._text.nextChar() != '}'):
                return True
        return False

    def _nextField(self):
        key = None
        value = None
        c = self._text.nextTokenChar()
        if(c == '{'):
            key = self._nextTable()
        elif(c == '\'' or c == '\"'):
            key = self._nextString()
            if(self._text.nextTokenChar() == '='):
                message = 'String cannot be key in lua table! Detected in string \'' + key + '\''
                raise LuaParseError(message)
        else:
            key = self._text.nextTokenBefore(['=', ',', ';', '}'])
            if(key.length() == 0):
                message =  'Expecting field or key before \'' + \
                    str(self._text.nextChar()) + '\''
                raise LuaParseError(message)
            key = self._parseToken(key)

        c = self._text.nextTokenChar()
        value = None
        if(c == '='):
            self._text.moveNext()
            value = self._nextValue()
        else:
            value = key
            key = None
        return (key, value)

    def _nextValue(self):
        value = None
        c = self._text.nextTokenChar()
        if(c == '{'):
            value = self._nextTable()
        elif(c == '\'' or c == '\"'):
            value = self._nextString()
        else:
            value = self._text.nextTokenBefore([',', ';', '}'])
            if(value.length() == 0):
                message =  'Expecting value before \'' + \
                    str(self._text.nextChar()) + '\''
                raise LuaParseError(message)
            value = self._parseToken(value)
        return value

    def _nextString(self):
       return self._text.nextString()

    @staticmethod
    def _parseToken(token):
        tokenStr = str(token)
        if(tokenStr == 'nil'):
            return None
        if(tokenStr == 'true'):
            return True
        if(tokenStr == 'false'):
            return False

        (isNumber, number) = PyLuaTblParser._tryParseNumber(tokenStr)
        if(isNumber):
            return number
        
        if PyLuaTblParser._isLuaName(tokenStr):
            return tokenStr

        message =  'Unrecognized token \'' + tokenStr + '\''
        raise LuaParseError(message)

    @staticmethod
    def _tryParseNumber(s):
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
    def _tryParseString(s):
        try:
            result = eval(s)
            if(not isinstance(result, basestring)):
                return (False, None)
            return (True, result)
        except SyntaxError:
            return (False, None)

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

if __name__ == '__main__':
    parser = PyLuaTblParser()

    infile = open('test.lua')
    text1 = infile.read()
    infile.close()

    parser.load(text1)
    print parser.dumpDict()



    
    
