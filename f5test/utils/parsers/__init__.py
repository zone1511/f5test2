import threading

# WORKAROUND for pyparsing concurrency issues:
# The pyparsing module is known to be non-threadsafe!
# Every function or method that calls pyparsing to parse any text MUST be
# synchronized with this lock.
#
# Example:
#
# from f5test.utils.decorators import synchronized_with
#
# @synchronized_with(PYPARSING_LOCK)
# def parser(text):
#     ...
#     return x.parseString(text)

PYPARSING_LOCK = threading.Lock()
