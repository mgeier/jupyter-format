"""Functions for reading Jupyter files."""
import json
import re

import nbformat

from . import ParseError
from ._common import RE_JSON


def deserialize(source):
    """Convert ``.jupyter`` string representation to Jupyter notebook.

    Lines have to be terminated with ``'\\n'``
    (a.k.a.  :term:`universal newlines` mode).

    If *source* is an iterable, line terminators may be omitted.

    :param source: Content of ``.jupyter`` file.
    :type source: str or iterable of str
    :returns: A notebook node.
    :rtype: nbformat.NotebookNode

    """
    lines = SourceLines(source)
    try:
        nb = parse(lines)
    except ParseError as e:
        if len(e.args) == 1:
            # Add line number
            e.args += lines.current,
        elif len(e.args) == 2:
            # Apply line number offset
            e.args = e.args[0], lines.current - e.args[1]
        raise e
    except Exception as e:
        raise ParseError(type(e).__name__ + ': ' + str(e), lines.current)
    return nb


def parse(lines):
    nb = parse_header(lines)

    for line in lines:
        if check_word('markdown', line):
            cell = nbformat.v4.new_markdown_cell()
        elif line.startswith('code'):
            cell = nbformat.v4.new_code_cell()
            if line not in ('code', 'code '):
                cell.execution_count = check_word_plus_integer('code', line)
        elif check_word('raw', line):
            cell = nbformat.v4.new_raw_cell()
        elif check_word('metadata', line):
            nb.metadata = parse_metadata(lines)
            for _ in lines:
                raise ParseError(
                    'All notebook metadata lines must be indented by 4 spaces '
                    'and no subsequent lines are allowed')
            break
        else:
            raise ParseError(
                "Expected (unindented) cell type or 'metadata', "
                "got {!r}".format(line))

        cell.source = parse_indented_text(lines)

        for line in IndentedLines(1, lines):
            if check_word('metadata', line):
                cell.metadata = parse_metadata(lines)
                # NB: cell metadata must be at the end
                break

            if cell.cell_type in ('markdown', 'raw'):
                # attachments (since v4.1)
                parse_attachment(line, lines, cell)
            elif cell.cell_type == 'code':
                parse_code_output(line, lines, cell)
        nb.cells.append(cell)
    return nb


def parse_header(lines):
    nb = nbformat.v4.new_notebook()

    for line in lines:
        nb.nbformat = check_word_plus_integer('nbformat', line)
        if nb.nbformat != 4:
            raise ParseError('Only v4 notebooks are currently supported')
        break
    else:
        raise ParseError('First line must be "nbformat X"')
    for line in lines:
        nb.nbformat_minor = check_word_plus_integer('nbformat_minor', line)
        break
    else:
        raise ParseError('Second line must be "nbformat_minor Y"')
    return nb


def parse_attachment(line, lines, cell):
    if not line.startswith('attachment'):
        raise ParseError(
            "Only 'attachment' is allowed here, not {!r}".format(line))
    if not hasattr(cell, 'attachments'):
        cell.attachments = {}
    name = check_word_plus_string('attachment', line)
    if name in cell.attachments:
        raise ParseError(
            'Duplicate attachment name: {!r}'.format(name))
    cell.attachments[name] = parse_mime_bundle(lines)


def parse_code_output(line, lines, cell):
    kwargs = {}
    if line.startswith('stream'):
        output_type = 'stream'
        # NB: "name" is required!
        kwargs['name'] = check_word_plus_string('stream', line)
        kwargs['text'] = parse_indented_text(lines)
    elif (check_word('display_data', line) or
            check_word('execute_result', line)):
        output_type = line
        if output_type == 'execute_result':
            kwargs['execution_count'] = cell.execution_count
        kwargs['data'] = parse_mime_bundle(lines)
        for line in IndentedLines(2, lines):
            if not check_word('metadata', line):
                raise ParseError(
                    "Only 'metadata' is allowed here, not {!r}".format(line))
            kwargs['metadata'] = parse_metadata(lines)
            break
    elif line.startswith('error'):
        output_type = 'error'
        # NB: All fields are required
        kwargs['ename'] = check_word_plus_string('error', line)
        # TODO: check for non-empty?
        kwargs['evalue'] = parse_indented_text(lines)
        kwargs['traceback'] = parse_traceback(lines)
    else:
        raise ParseError(
            'Expected output type, got {!r}'.format(line))
    for line in IndentedLines(2, lines):
        raise ParseError('Invalid output data: {!r}'.format(line))
    out = nbformat.v4.new_output(output_type, **kwargs)
    cell.outputs.append(out)


def parse_traceback(lines):
    for line in IndentedLines(2, lines):
        if not check_word('traceback', line):
            raise ParseError(
                "Expected 'traceback', got {!r}".format(line))
        traceback = []
        while True:
            frame = parse_indented_text(lines)
            traceback.append(frame)
            for line in IndentedLines(3, lines):
                if check_word('~', line):
                    break
                raise ParseError(
                    'Invalid traceback separator: {!r}'.format(line))
            else:
                break
        return traceback
    raise ParseError("Missing 'traceback'")


def parse_mime_bundle(lines):
    bundle = {}
    for line in IndentedLines(3, lines):
        mime_type = line
        # TODO: allow whitespace?
        if mime_type != mime_type.strip():
            # TODO: better error message?
            raise ParseError('Invalid MIME type: {!r}'.format(mime_type))
        # TODO: check for repeated MIME type?
        content = parse_indented_text(lines)
        if content:
            content += '\n'
        if RE_JSON.match(mime_type):
            bundle[mime_type] = parse_json(content)
        else:
            if content and content.endswith('\n') and content.strip('\n'):
                content = content[:-1]
            bundle[mime_type] = content
    return bundle


def parse_metadata(lines):
    return parse_json(parse_indented_text(lines))


def parse_json(text):
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # Abuse JSONDecodeError constructor to calculate number of lines:
        total = json.JSONDecodeError('', text, -1).lineno
        raise ParseError(
            'JSON error in column {}: {}'.format(e.colno + 4, e.msg),
            total - e.lineno + 1)
    return data


def parse_indented_text(lines):
    return '\n'.join(IndentedLines(4, lines))


def check_word_plus_integer(word, line):
    m = re.match(word + ' ([0-9]|[1-9][0-9]+)$', line)
    if not m:
        raise ParseError(
            'Expected {!r} followed by a space and an integer'.format(word))
    return int(m.group(1))


def check_word_plus_string(word, line):
    chars = len(word)
    # TODO: check if line[chars + 1] is a space?
    # TODO: use split() or partition()?
    if len(line) < chars + 2 or line[chars] != ' ':
        raise ParseError('Missing string after {!r}'.format(word))
    return line[chars + 1:]


def check_word(word, line):
    if line.startswith(word):
        if line != word:
            raise ParseError('No text allowed after {!r}'.format(word))
        return True
    else:
        return False


class SourceLines:
    """Iterator over source lines.

    Strips trailing newlines, tracks current line number, allows peeking.

    """

    def __init__(self, source):
        if isinstance(source, str):
            source = source.splitlines()
        self._iter = iter(source)
        self.current = -1
        self.advance()

    def peek(self):
        if isinstance(self._next, StopIteration):
            raise self._next
        return self._next

    def advance(self):
        try:
            line = next(self._iter)
            if line.endswith('\n'):
                line = line[:-1]
            self._next = line
        except StopIteration as e:
            self._next = e
        self.current += 1

    def __iter__(self):
        return self

    def __next__(self):
        line = self.peek()
        self.advance()
        return line


class IndentedLines:
    """Iterator adaptor which stops if there is less indentation.

    Blank lines are forwarded as empty lines.

    """

    def __init__(self, indentation, iterator):
        self._indent = indentation
        self._iter = iterator

    def peek(self):
        line = self._iter.peek()
        if line.startswith(' ' * self._indent):
            line = line[self._indent:]
        elif not line.strip():
            line = ''  # Blank line
        else:
            raise StopIteration()
        return line

    def advance(self):
        return self._iter.advance()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.peek()
        self.advance()
        return line

