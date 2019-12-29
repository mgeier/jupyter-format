"""Serialize and deserialize Jupyter format."""
__version__ = '0.0.0'

SUFFIX = '.jupyter'


class ParseError(Exception):
    """Exception that is thrown on errors during reading.

    This reports the line number where the error occured.

    """

    def __str__(self):
        if len(self.args) == 2:
            return 'Line {1}: {0}'.format(*self.args)
        return super().__str__()


from ._reader import deserialize
from ._writer import generate_lines, serialize
