from pyparsing import (Literal, Word, dictOf, restOfLine, alphas, ParseException)

class VersionFileParseException(Exception):
    pass

def colon_pairs_dict(string):
    toplevel = dictOf(Word(alphas + "_") + Literal(": ").suppress(),
                      restOfLine)
    try:
        ret = toplevel.parseString(string).asDict()
        return dict(zip(map(lambda x:x.lower(), ret.keys()), ret.values()))

    except ParseException:
        raise VersionFileParseException(string)


def equals_pairs_dict(string):
    toplevel = dictOf(Word(alphas + "_") + Literal("=").suppress(),
                      restOfLine)
    try:
        ret = toplevel.parseString(string).asDict()
        return dict(zip(map(lambda x:x.lower(), ret.keys()), ret.values()))

    except ParseException:
        raise VersionFileParseException(string)
