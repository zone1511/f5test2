'''
Created on Mar 19, 2015

A basic Python expression builder.

@author: jono
'''
from array import array

__all__ = ['And', 'Or', 'Not', 'Less', 'Greater', 'LessEqual', 'GreaterEqual',
           'Equal', 'NotEqual', 'In', 'NotIn', 'Is', 'IsNot']


class Expression(object):
    __slots__ = ()

    def __str__(self):
        raise NotImplementedError

    @property
    def params(self):
        raise NotImplementedError

    def __and__(self, other):
        if isinstance(other, Empty):
            return self
        return And((self, other))

    def __or__(self, other):
        if isinstance(other, Empty):
            return self
        return Or((self, other))

    def __invert__(self):
        return Not(self)

    def __neg__(self):
        return Neg(self)

    def __pos__(self):
        return Pos(self)

    def __lt__(self, other):
        return Less(self, other)

    def __le__(self, other):
        return LessEqual(self, other)

    def __eq__(self, other):
        return Equal(self, other)

    def is_(self, other):
        return Is(self, other)

    def is_not(self, other):
        return IsNot(self, other)

    # When overriding __eq__, __hash__ is implicitly set to None
    __hash__ = object.__hash__

    def __ne__(self, other):
        return NotEqual(self, other)

    def __gt__(self, other):
        return Greater(self, other)

    def __ge__(self, other):
        return GreaterEqual(self, other)

    def in_(self, values):
        return In(self, values)


class Literal(Expression):
    __slots__ = ('_value')

    def __init__(self, value):
        super(Literal, self).__init__()
        self._value = value

    @property
    def value(self):
        return self._value

    def __str__(self):
        return str(self._value)

    @property
    def params(self):
        return (self._value,)


class String(Literal):
    __slots__ = ('_value', '_quote')

    def __init__(self, value, quote="'"):
        super(String, self).__init__(value.replace(quote, '\\%s' % quote))
        self._quote = quote

    @property
    def value(self):
        return self._value

    def __str__(self):
        return "{0}{1}{0}".format(self._quote, self._value)


class Null(Literal):
    __slots__ = ('_value')

    def __init__(self):
        super(Null, self).__init__('None')

    def __nonzero__(self):
        return False


class Empty(Literal):
    __slots__ = ('_value')

    def __init__(self):
        super(Empty, self).__init__('')

    def __nonzero__(self):
        return False


class Operator(Expression):
    __slots__ = ()

    @property
    def _operands(self):
        return ()

    def _format(self, operand, param=None):
        if isinstance(operand, Expression):
            return str(operand)
        elif isinstance(operand, list):
            return '[' + ', '.join(self._format(o, param)
                                   for o in operand) + ']'
        elif isinstance(operand, tuple):
            return '(' + ', '.join(self._format(o, param)
                                   for o in operand) + ',)'
        elif isinstance(operand, array):
            return '(' + ', '.join((param,) * len(operand)) + ')'
        else:
            return param

    def __str__(self):
        raise NotImplemented

    def __and__(self, other):
        if isinstance(other, And):
            return And([self] + other)
        else:
            return And((self, other))

    def __or__(self, other):
        if isinstance(other, Or):
            return Or([self] + other)
        else:
            return Or((self, other))


class UnaryOperator(Operator):
    __slots__ = 'operand'
    _operator = ''

    def __init__(self, operand):
        self.operand = operand

    @property
    def _operands(self):
        return (self.operand,)

    def __str__(self):
        return '%s %s' % (self._operator, self._format(self.operand))


class BinaryOperator(Operator):
    __slots__ = ('left', 'right')
    _operator = ''

    def __init__(self, left, right):
        self.left = left
        self.right = right

    @property
    def _operands(self):
        return (self.left, self.right)

    def __str__(self):
        if isinstance(self.left, Literal) and isinstance(self.right, Literal):
            fmt = '%s %s %s'
        else:
            fmt = '(%s %s %s)'
        return fmt % (self._format(self.left), self._operator,
                      self._format(self.right))

    def __invert__(self):
        return _INVERT[self.__class__](self.left, self.right)


class NaryOperator(list, Operator):
    __slots__ = ()
    _operator = ''

    @property
    def _operands(self):
        return [x for x in self if not isinstance(x, Empty)]

    def __str__(self):
        ret = (' %s ' % self._operator).join(map(str, self._operands))
        if len(self._operands) > 1:
            return '(' + ret + ')'
        else:
            return ret


class And(NaryOperator):
    __slots__ = ()
    _operator = 'and'


class Or(NaryOperator):
    __slots__ = ()
    _operator = 'or'


class Not(UnaryOperator):
    __slots__ = ()
    _operator = 'not'


class Neg(UnaryOperator):
    __slots__ = ()
    _operator = '-'


class Pos(UnaryOperator):
    __slots__ = ()
    _operator = '+'


class Less(BinaryOperator):
    __slots__ = ()
    _operator = '<'


class Greater(BinaryOperator):
    __slots__ = ()
    _operator = '>'


class LessEqual(BinaryOperator):
    __slots__ = ()
    _operator = '<='


class GreaterEqual(BinaryOperator):
    __slots__ = ()
    _operator = '>='


class Equal(BinaryOperator):
    __slots__ = ()
    _operator = '=='

    @property
    def _operands(self):
        if self.left is Null:
            return (self.right,)
        elif self.right is Null:
            return (self.left,)
        return super(Equal, self)._operands

    def __str__(self):
        if self.left is Null:
            return '(%s is None)' % self.right
        elif self.right is Null:
            return '(%s is None)' % self.left
        return super(Equal, self).__str__()


class NotEqual(Equal):
    __slots__ = ()
    _operator = '!='

    def __str__(self):
        if self.left is Null:
            return '(%s is not None)' % self.right
        elif self.right is Null:
            return '(%s is not None)' % self.left
        return super(Equal, self).__str__()


class Is(BinaryOperator):
    __slots__ = ()
    _operator = 'is'


class IsNot(BinaryOperator):
    __slots__ = ()
    _operator = 'is not'


class In(BinaryOperator):
    __slots__ = ()
    _operator = 'in'


class NotIn(BinaryOperator):
    __slots__ = ()
    _operator = 'not in'


_INVERT = {
    Less: GreaterEqual,
    Greater: LessEqual,
    LessEqual: Greater,
    GreaterEqual: Less,
    Equal: NotEqual,
    NotEqual: Equal,
    In: NotIn
}


if __name__ == '__main__':
    e = Empty()
    e |= (String('a') | String('a') | String('a') | String('a') & String('b'))
    e &= (String('b') & String('b') & String('b') | String('a'))
    e &= Is(String('n'), Null())
    e |= In(String('n'), [Null()])
    e |= ~In(String('n'), (Null(),))
    print e
