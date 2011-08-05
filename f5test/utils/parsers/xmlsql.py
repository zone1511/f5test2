"""`mysql -X` XML output parsers"""
from xml.dom.minidom import parseString
from ..lists import collapse_lists
from ...base import Options

class MysqlValueError(ValueError):
    pass


def parse_xmlsql(value):
    if not value:
        return
    
    doc = parseString(value)
    rows = doc.getElementsByTagName('row')

    if len(rows) == 0:
        return

    row1 = rows[0]
    colnames = []
    for field in row1.getElementsByTagName('field'):
        colnames.append(field.getAttribute('name'))

    data = []
    for row in rows:
        tmp = []
        for field in row.getElementsByTagName('field'):
            if len(field.childNodes) > 0 :
                tmp.append(field.childNodes[0].data)
            elif field.hasAttribute('xsi:nil'):
                tmp.append(None)
            else:
                tmp.append('')
        data.append(tmp)

    return colnames, data

def _dict_per_row(results, colNames):
    """yields a dict of values for each row in colNames"""
    if results and len(results) > 1:
        cols = results[0]
        indexes = []
        for colName in colNames:
            try:
                indexes.append(cols.index(colName))
            except ValueError, e:
                raise MysqlValueError("'%s' was not found: %s" %
                                        (colName, e))
        rows = results[1]
        for row in rows:
            values = Options()
            for idx in indexes:
                try:
                    values[cols[idx]] = row[idx]
                except IndexError, e:
                    raise MysqlValueError("idx '%s' was not found: %s" %
                                            (idx, e))
            yield values

def parse_xmlsql_row_dict(results):
    """returns an array of dicts like:
    
    [{'column1': 'val1', 'column2': 'val2'},
     {'column1': 'val1', 'column2': 'val2'}
    ]
    """
    if not results:
        return []
    return _dict_per_row(results, results[0])

def parse_xmlsql_key_array(results):
    """returns a dict with column names as keys and their values
    
    {'column1': ['val1', 'val2'],
     'column2': ['val1', 'val2']
    }
    """
    return collapse_lists(_dict_per_row(results, results[0]))
