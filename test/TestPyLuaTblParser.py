import sys, traceback
sys.path.append('../PyLuaTblParser/')

from PyLuaTblParser import PyLuaTblParser, LuaParseError

def testfile(f):
    p1 = PyLuaTblParser()
    p2 = PyLuaTblParser()
    infile = open(f)
    for line in infile:
        line = line.strip()
        if(len(line) == 0 or line[0] == '#'):
            continue
        try:
            print 'input : ' + line
            p1.load(line)
            p1.dumpLuaTable('test_dump.lua')
            p2.loadLuaTable('test_dump.lua')
            d1 = p1.dumpDict()
            d2 = p2.dumpDict()
            if(d1 != d2):
                print 'd1: ', d1
                print 'd2: ', d2
                raise Exception('Dump Error!')
            print '-----------------------'
        except LuaParseError, e:
            print e
            traceback.print_exc()
            print '-----------------------'
            #sys.exit()
    infile.close()

def testSingleTableFile(f):
    p1 = PyLuaTblParser()
    p2 = PyLuaTblParser()
    infile = open(f)
    try:
        s = infile.read()
        print 'input : ' + s
        p1.load(s)
        p1.dumpLuaTable('test_dump.lua')
        p2.loadLuaTable('test_dump.lua')
        d1 = p1.dumpDict()
        d2 = p2.dumpDict()
        if(d1 != d2):
            print 'd1: ', d1
            print 'd2: ', d2
            raise Exception('Dump Error!')
        print '-----------------------'
    except LuaParseError, e:
        print e
        print '-----------------------'
    infile.close()


def testNilKey():
    p1 = PyLuaTblParser()
    p1.loadLuaTable('test_dump.lua')
    d = {'name':'John', 'Country': {'Name': 'USA', 'Desc': None}, 'Desc':None}
    p1.loadDict(d)
    print p1.dumpDict()
    p1['name'] = None
    print p1.dumpDict()

def test():
    #testNilKey()
    testfile('test.txt')
    '''
    #parser.update({'test':4, 'invalid':{(1, 2):100, 'valid': 48}})
    print parser.dumpDict()
    print '----------Lua dump-----------'
    print parser.dump()
    parser.dumpLuaTable('test_dump.lua')
    '''

if __name__ == '__main__':
    test()