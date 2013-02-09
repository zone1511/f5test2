from pyparsing import Literal, Word, Group, ZeroOrMore, alphanums, OneOrMore, \
    Combine, Forward, lineEnd, Optional, dblQuotedString, removeQuotes, \
    ParseException, nums


class TMSHParseException(Exception):
    pass


def tmsh_to_dict(string):
    LBRA = Literal("{").suppress()
    RBRA = Literal("}").suppress()
    EOL = lineEnd.suppress()
    tmshString = Word(alphanums + '!#$%&()*+,-./:;<=>?@[\]^_`|~')
    intNumber = Word(nums).setParseAction(lambda s, l, t: [int(t[0])])
    NONE = Literal("none").setParseAction(lambda s, l, t: [None])

    tmshKey = intNumber ^ tmshString | dblQuotedString.setParseAction(removeQuotes)
    tmshValue = NONE | tmshKey

    def toSet(s, loc, t):
        return set(t[0])

    tmshSet = LBRA + Group(OneOrMore(Combine(tmshKey).setWhitespaceChars(' '))).setParseAction(toSet) + RBRA

    def toDict(d, l):
        if not l[0] in d:
            d[l[0]] = {}

        for v in l[1:]:
            if type(v) == list:
                toDict(d[l[0]], v)
            else:
                d[l[0]] = v

    def trueDefault(s, loc, t):
        return len(t) and t or True

    singleKeyValue = Forward()
    singleKeyValue << (
                Group(
                    tmshKey + (
                                # A toggle value (i.e. key without value).
                                EOL.setParseAction(trueDefault) |
                                # A set of values on a single line.
                                tmshSet |
                                # A normal value or another singleKeyValue group.
                                Optional(tmshValue | LBRA + ZeroOrMore(singleKeyValue) + RBRA)
                               )
                )
    )

    multiKeysOneValue = Forward()
    multiKeysOneValue << (
                Group(
                    tmshKey + (
                                multiKeysOneValue |
                                tmshSet |
                                LBRA + ZeroOrMore(singleKeyValue) + RBRA
                              )
                )
    )

    toplevel = OneOrMore(multiKeysOneValue)

    if not string:
        return {}

    # now parse data and print results
    try:
        data = toplevel.parseString(string)
    except ParseException:
        raise TMSHParseException(string)

    h = {}
    for x in data.asList():
        toDict(h, x)
    return h
