'''
Created on Mar 24, 2013

Inspired by: parsePythonValue.py example
http://pyparsing.wikispaces.com/file/view/parsePythonValue.py/31712649/parsePythonValue.py

@author: jono
'''
from pyparsing import *
from ..decorators import synchronized_with
from . import PYPARSING_LOCK


@synchronized_with(PYPARSING_LOCK)
def parser(text):
    cvtInt = lambda toks: int(toks[0])
    cvtReal = lambda toks: float(toks[0])
    cvtTuple = lambda toks: tuple(toks.asList())
    cvtDict = lambda toks: dict(toks.asList())

    # define punctuation as suppressed literals
    lparen, rparen, lbrack, rbrack, lbrace, rbrace, colon = \
        map(Suppress, "()[]{}:")

    identifier = Word(alphanums + "_")
    integer = Combine(Optional(oneOf("+ -")) + Word(nums))\
        .setName("integer")\
        .setParseAction(cvtInt)
    real = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
                   Optional(Word(nums)) +
                   Optional(oneOf("e E") + Optional(oneOf("+ -")) + Word(nums)))\
        .setName("real")\
        .setParseAction(cvtReal)
    tupleStr = Forward()
    listStr = Forward()
    dictStr = Forward()

    listItem = real | integer | quotedString.setParseAction(removeQuotes) | \
                Group(listStr) | tupleStr | dictStr | identifier

    tupleStr << (Suppress("(") + Optional(delimitedList(listItem)) +
                Optional(Suppress(",")) + Suppress(")"))
    tupleStr.setParseAction(cvtTuple)

    listStr << (lbrack + Optional(delimitedList(listItem) +
                Optional(Suppress(","))) + rbrack)

    dictEntry = Group(listItem + colon + listItem)
    dictStr << (lbrace + Optional(delimitedList(dictEntry) + \
        Optional(Suppress(","))) + rbrace)
    dictStr.setParseAction(cvtDict)

    argItem = Group(
                    OneOrMore((identifier + Suppress("=") + listItem)
                              .setParseAction(cvtTuple)))

    return argItem.parseString(text)[0]


if __name__ == '__main__':
    test = """argument_1 = [123, [{foo: bar}], {'value': 3.14}]
              _arg2=(_bb_1, 100)
              argument__3 = 'some quoted string'"""

    print "Input:", test.strip()
    result = parser(test)
    print "Result:"
    for name, value in result:
        print "  %s = %r" % (name, value)
