from pyparsing import (Literal, Word, dictOf, restOfLine, alphas, ParseException)
from ..decorators import synchronized_with
from . import PYPARSING_LOCK


class VersionFileParseException(Exception):
    pass


@synchronized_with(PYPARSING_LOCK)
def colon_pairs_dict(string):
    toplevel = dictOf(Word(alphas + "_") + Literal(": ").suppress(),
                      restOfLine)
    try:
        ret = toplevel.parseString(string).asDict()
        return dict(zip(map(lambda x: x.lower(), ret.keys()), ret.values()))

    except ParseException:
        raise VersionFileParseException(string)


@synchronized_with(PYPARSING_LOCK)
def equals_pairs_dict(string):
    toplevel = dictOf(Word(alphas + "_") + Literal("=").suppress(),
                      restOfLine)
    try:
        ret = toplevel.parseString(string).asDict()
        return dict(zip(map(lambda x: x.lower(), ret.keys()), ret.values()))

    except ParseException:
        raise VersionFileParseException(string)
