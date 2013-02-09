# represents a hash table with key/value pairs, a put() over
# an existing key replaces the value of that key
from xml.dom.minidom import parseString

def isnumber(n):
    return hasattr(n, '__int__')


class ParsingError(IOError):
    pass

class Dictionary:
    
    def __init__(self, data = {}):
        self.data = {}
        for key in data.keys():
            self.put(key, data[key])
    
    def put(self, name, value):
        if isinstance(value, basestring) or isnumber(value):
            self.data[name] = String(value)
        elif isinstance(value, list):
            anArray = Array()
            for item in value:
                anArray.add(item)
            self.data[name] = anArray
        else:
            self.data[name] = value
    
    def get(self, name):
        return self.data[name]
    
    def __getitem__(self, name):
        return self.get(name)
    
    def keys(self):
        return self.data.keys()
    
    def value(self):
        return self.data
    
    def has_key(self, key):
        return self.data.has_key(key)
    
    def to_string(self):
        strList = []
        strList.append('<dictionary>')
        for key in self.keys():
            strList.append('<entry><key>')
            strList.append(key)
            strList.append('</key><value>')
            try:
                strList.append(self.get(key).to_string())
            except:
                strList.append('<string>')
                strList.append(str(self.get(key)))
                strList.append('</string>')
            strList.append('</value></entry>')
        strList.append('</dictionary>')
        return ''.join(strList)
    
    def read(self, dictElement):
        kids = findDescendents(dictElement, 'entry')
        for i in range (len(kids)):
            keyNode = findDescendent(kids[i], 'key')
            keyValue = getTextValue(keyNode)
            valueNode = findDescendent(kids[i], 'value')
            valueKids = valueNode.childNodes
            for j in range (len(valueKids)):
                valueKid = valueKids[j]
                valueKidName = valueKid.nodeName
                if ("string" == valueKidName):
                    string = String()
                    string.read(valueKid)
                    self.put(keyValue, string)
                elif ("array" == valueKidName):
                    ary = Array()
                    ary.read(valueKid)
                    self.put(keyValue, ary)
                elif ("dictionary" == valueKidName):
                    dictionary = Dictionary()
                    dictionary.read(valueKid)
                    self.put(keyValue, dictionary)
                elif ("table" == valueKidName):
                    table = Table()
                    table.read(valueKid)
                    self.put(keyValue, table)

# represents a table of rows of values
class Table:
    """represent a 2-d table as list of lists"""
    def __init__(self):
        self.cols = []
        self.rows = []
    
    def add_column(self, name):
        self.cols.append(name)
    
    def add_row(self, row = None):
        if row:
            self.rows.append(row)
        else:
            self.rows.append([])
            for row in self.cols:
                self.rows[len(self.rows)-1].append(None)
    
    def value(self):
        return [self.cols, self.rows]
    
    def set_value_by_name(self, rowIndex, colName, value):
        self.rows[rowIndex][self.cols.index(colName)] = value
    
    def get_value_by_name(self, rowIndex, colName):
        return self.rows[rowIndex][self.cols.index(colName)]
    
    def set_value_by_index(self, rowIndex, colIndex, value):
        self.rows[rowIndex][colIndex] = value
    
    def get_value_by_index(self, rowIndex, colIndex):
        return self.rows[rowIndex][colIndex]
    
    def get_row(self, index):
        return self.rows[index]
    
    def to_string(self):
        strList = []
        strList.append('<table><columns>')
        for col in self.cols:
            strList.append('<column>%s</column>' % col)
        strList.append('</columns><rows>')
        for row in self.rows:
            strList.append('<row>')
            for col in row:
                if col:
                    strList.append('<value>%s</value>' % col)
            strList.append('</row>')
        strList.append('</rows></table>')
        return ''.join(strList)
    
    def read(self, tableElement):
        colsNode = findFirstDescendent(tableElement, 'columns')
        colNodes = findDescendents(colsNode, 'column')
        for col in range(len(colNodes)):
            self.add_column(getTextValue(colNodes[col]))
        rowsNode = findFirstDescendent(tableElement, 'rows')
        rowNodes = findDescendents(rowsNode, 'row')
        rowIndex = 0
        for row in range(len(rowNodes)):
            self.add_row()
            valueNodes = findDescendents(rowNodes[row], 'value')
            colIndex = 0
            for value in range(len(valueNodes)):
                self.set_value_by_index(rowIndex, colIndex, 
                    getTextValue(valueNodes[value]))
                colIndex = colIndex + 1
            rowIndex = rowIndex + 1

# represents a list of values
class Array:
    
    def __init__(self, data = []):
        self.data = []
        for item in data:
            self.add(item)
    
    def add(self, value):
        if isinstance(value, dict):
            aDict = Dictionary()
            for key in value.keys():
                aDict.put(key, value.get(key))
            self.data.append(aDict)
        elif isinstance(value, basestring) or isnumber(value):
            self.data.append(String(value))
        else:
            self.data.append(value)
    
    def at(self, index):
        return self.data[index]
    
    def __getitem__(self, index):
        return self.at(index)
    
    def len(self): #@ReservedAssignment
        return len(self.data)
    
    def value(self):
        return self.data
    
    def has_key(self, key):
        return self.data.has_key(key)
    
    def to_string(self):
        strList = []
        strList.append('<array>')
        for i in range(self.len()):
            strList.append('<value>')
            try:
                strList.append(self.at(i).to_string())
            except:
                strList.append('<string>')
                strList.append(str(self.at(i)))
                strList.append('</string>')
            strList.append('</value>')
        strList.append('</array>')
        return ''.join(strList)
    
    def read(self, arrayElement):
        values = findDescendents(arrayElement, 'value')
        for i in range (len(values)):
            value = values[i]
            dicts = findDescendents(value, "dictionary")
            for j in range (len(dicts)):
                aDict = Dictionary()
                aDict.read(dicts[j])
                self.add(aDict)
            arrays = findDescendents(value, "array")
            for j in range (len(arrays)):
                anArray = Array()
                anArray.read(arrays[j])
                self.add(anArray)
            tables = findDescendents(value, "table")
            for j in range (len(tables)):
                aTable = Table()
                aTable.read(tables[j])
                self.add(aTable)
            strings = findDescendents(value, "string")
            for j in range (len(strings)):
                string = String()
                string.read(strings[j])
                self.add(string)

# wraps a string
class String:
    
    def __init__(self, val = ''):
        self.set(val)
    
    def set(self, val): #@ReservedAssignment
        if isinstance(val, basestring):
            self.data = val
        else:
            self.data = str(val)
    
    def value(self):
        return self.data
    
    def to_string(self):
        strList = []
        strList.append('<string>')
        strList.append(self.data)
        strList.append('</string>')
        return ''.join(strList)
    
    def read(self, stringElement):
        self.set(getTextValue(stringElement))

# convert a Dictionary/Array/Table/String to builtin python types
def to_python(val):
    if isinstance(val, String):
        s = val.value()
        return s
    elif isinstance(val, Dictionary):
        d = {}
        for key in val.keys():
            d[key] = to_python(val.get(key))
        return d
    elif isinstance(val, Array):
        a = []
        for i in range(len(val.value())):
            a.append(to_python(val.at(i)))
        return a
    elif isinstance(val, Table):
        return [list(val.value()[0]), list(val.value()[1])]
    else:
        raise ValueError('unrecognized value: %r' % val)

# an instance of Result is returned from parseSTAFResult
class Result:
    def __init__(self):
        self.version = None
        self.resultName = None
        self.resultCode = None
        self.resultString = None
        self.resultData = None

# parse the 'resultData' portion of the XML document
def parseData(rootNode):
    argKids = rootNode.childNodes
    for i in range (len(argKids)):
        node = argKids[i]
        nodeName = node.nodeName
        if ("dictionary" == nodeName):
            aDict = Dictionary()
            aDict.read(node)
            return aDict
        elif ("array" == nodeName):
            anArray = Array()
            anArray.read(node)
            return anArray
        elif ("string" == nodeName):
            aString = String()
            aString.read(node)
            return aString
        elif ("table" == nodeName):
            aTable = Table()
            aTable.read(node)
            return aTable
    return None

# recursively find first descendent of node named descendentName
def findFirstDescendent(node, descendentName):
    if (node.nodeName == descendentName):
        return node
    else:
        kids = node.childNodes
        if (len(kids) > 0):
            for i in range (len(kids)):
                node = findFirstDescendent(kids[i], descendentName)
                if node:
                    return node
        return None

# return first direct descendent of node named descendentName
def findDescendent(node, descendentName):
    kids = node.childNodes
    for i in range (len(kids)):
        kid = kids[i]
        if (descendentName == kid.nodeName):
            return kid
    return None 

# return list of all direct discendents of nodes named descendentName 
def findDescendents(node, descendentName):
    descendents = []
    kids = node.childNodes
    for i in range (len(kids)):
        kid = kids[i]
        if (descendentName == kid.nodeName):
            descendents.append(kid)
    return descendents 

# return append all '#text' element descendents of node
def getTextValue(node):
    text = []
    kids = node.childNodes
    if (len(kids) > 0):
        for i in range (len(kids)):
            kid = kids[i]
            if ("#text" == kid.nodeName):
                text.append(kid.nodeValue)
    return ''.join(text)

def getErrorInfo(responseNode):
    errCodeNode = findDescendent(responseNode, 'errorCode')
    errCode = getTextValue(errCodeNode)
    errMsgNode = findDescendent(responseNode, 'errorMessage')
    errMsg = getTextValue(errMsgNode)
    return errCode, errMsg

def parseDocument(rootNode):
    responseNode = findFirstDescendent(rootNode, "response")
    if responseNode:
        errCode, errMsg = getErrorInfo(responseNode)
        if '0' != errCode:
            raise ParsingError(int(errCode), errMsg)
        args = findDescendent(responseNode, "args")
        return parseData(args)
    else:
        raise ParsingError(-1, 'no response tag found')


# construct XML parser, parse doc and return result
def parseResult(value):
    if not value or len(value) == 0:
        raise ParsingError(-2, "no response received")

    doc = parseString(value)
    return parseDocument(doc)

