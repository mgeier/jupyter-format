"""Serialize and deserialize Jupyter format."""
import json as _json
import re as _re

import nbformat as _nbformat

SUFFIX = '.jupyter'

# Regular expression from nbformat JSON schema:
_RE_JSON = _re.compile('^application/(.*\\+)?json$')


def generate_lines(nb):
    """Generator yielding lines to be written to ``.jupyter`` files.

    Each of the lines has a line separator at the end, therefore it can
    e.g. be used in :meth:`~io.IOBase.writelines`.

    :param nbformat.NotebookNode nb: A notebook node.

    """
    if nb.nbformat != 4:
        raise RuntimeError('Currently, only notebook version 4 is supported')
    yield _line('', 'nbformat', nb.nbformat)
    yield _line('', 'nbformat_minor', nb.nbformat_minor)
    for cell in nb.cells:
        cell_type = cell.cell_type
        if cell_type == 'code' and cell.execution_count is not None:
            yield _line('', 'code', cell.execution_count)
        else:
            yield _line('', cell_type)
        yield from _indented_block(cell.source + '\n')
        if cell_type in ('markdown', 'raw'):
            # attachments (since v4.1)
            for name, data in cell.get('attachments', {}).items():
                yield from _attachment(name, data)
        elif cell_type == 'code':
            for out in cell.outputs:
                yield from _code_cell_output(out)
        else:
            raise RuntimeError('Unknown cell type: {!r}'.format(cell_type))
        if cell.metadata:
            yield from _json_block(' metadata', cell.metadata)
    if nb.metadata:
        yield from _json_block('metadata', nb.metadata)


def serialize(nb):
    """Convert a Jupyter notebook to a string in ``.jupyter`` format.

    :param nbformat.NotebookNode nb: A notebook node.
    :returns: ``.jupyter`` file content.
    :rtype: str

    """
    return ''.join(generate_lines(nb))


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
    lines = _SourceLines(source)
    try:
        nb = _parse(lines)
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


class ParseError(Exception):
    """Exception that is thrown on errors during reading.

    This reports the line number where the error occured.

    """

    def __str__(self):
        if len(self.args) == 2:
            return 'Line {1}: {0}'.format(*self.args)
        return super().__str__()


class _SourceLines:
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


class _IndentedLines:
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


def _parse(lines):
    nb = _parse_header(lines)

    for line in lines:
        if _check_word('markdown', line):
            cell = _nbformat.v4.new_markdown_cell()
        elif line.startswith('code'):
            cell = _nbformat.v4.new_code_cell()
            if line not in ('code', 'code '):
                cell.execution_count = _check_word_plus_integer('code', line)
        elif _check_word('raw', line):
            cell = _nbformat.v4.new_raw_cell()
        elif _check_word('metadata', line):
            nb.metadata = _parse_metadata(lines)
            for _ in lines:
                raise ParseError(
                    'All notebook metadata lines must be indented by 4 spaces '
                    'and no subsequent lines are allowed')
            break
        else:
            raise ParseError(
                "Expected (unindented) cell type or 'metadata', "
                "got {!r}".format(line))

        cell.source = _parse_indented_text(lines)

        for line in _IndentedLines(1, lines):
            if _check_word('metadata', line):
                cell.metadata = _parse_metadata(lines)
                # NB: cell metadata must be at the end
                break

            if cell.cell_type in ('markdown', 'raw'):
                # attachments (since v4.1)
                _parse_attachment(line, lines, cell)
            elif cell.cell_type == 'code':
                _parse_code_output(line, lines, cell)
        nb.cells.append(cell)
    return nb


def _parse_header(lines):
    nb = _nbformat.v4.new_notebook()

    for line in lines:
        nb.nbformat = _check_word_plus_integer('nbformat', line)
        if nb.nbformat != 4:
            raise ParseError('Only v4 notebooks are currently supported')
        break
    else:
        raise ParseError('First line must be "nbformat X"')
    for line in lines:
        nb.nbformat_minor = _check_word_plus_integer('nbformat_minor', line)
        break
    else:
        raise ParseError('Second line must be "nbformat_minor Y"')
    return nb


def _parse_attachment(line, lines, cell):
    if not line.startswith('attachment'):
        raise ParseError(
            "Only 'attachment' is allowed here, not {!r}".format(line))
    if not hasattr(cell, 'attachments'):
        cell.attachments = {}
    name = _check_word_plus_string('attachment', line)
    if name in cell.attachments:
        raise ParseError(
            'Duplicate attachment name: {!r}'.format(name))
    cell.attachments[name] = _parse_mime_bundle(lines)


def _parse_code_output(line, lines, cell):
    kwargs = {}
    if line.startswith('stream'):
        output_type = 'stream'
        # NB: "name" is required!
        kwargs['name'] = _check_word_plus_string('stream', line)
        kwargs['text'] = _parse_indented_text(lines)
    elif (_check_word('display_data', line) or
            _check_word('execute_result', line)):
        output_type = line
        if output_type == 'execute_result':
            kwargs['execution_count'] = cell.execution_count
        kwargs['data'] = _parse_mime_bundle(lines)
        for line in _IndentedLines(2, lines):
            if not _check_word('metadata', line):
                raise ParseError(
                    "Only 'metadata' is allowed here, not {!r}".format(line))
            kwargs['metadata'] = _parse_metadata(lines)
            break
    elif line.startswith('error'):
        output_type = 'error'
        # NB: All fields are required
        kwargs['ename'] = _check_word_plus_string('error', line)
        # TODO: check for non-empty?
        kwargs['evalue'] = _parse_indented_text(lines)
        kwargs['traceback'] = _parse_traceback(lines)
    else:
        raise ParseError(
            'Expected output type, got {!r}'.format(line))
    for line in _IndentedLines(2, lines):
        raise ParseError('Invalid output data: {!r}'.format(line))
    out = _nbformat.v4.new_output(output_type, **kwargs)
    cell.outputs.append(out)


def _parse_traceback(lines):
    for line in _IndentedLines(2, lines):
        if not _check_word('traceback', line):
            raise ParseError(
                "Expected 'traceback', got {!r}".format(line))
        traceback = []
        while True:
            frame = _parse_indented_text(lines)
            traceback.append(frame)
            for line in _IndentedLines(3, lines):
                if _check_word('~', line):
                    break
                raise ParseError(
                    'Invalid traceback separator: {!r}'.format(line))
            else:
                break
        return traceback
    raise ParseError("Missing 'traceback'")


def _parse_mime_bundle(lines):
    bundle = {}
    for line in _IndentedLines(3, lines):
        mime_type = line
        # TODO: allow whitespace?
        if mime_type != mime_type.strip():
            # TODO: better error message?
            raise ParseError('Invalid MIME type: {!r}'.format(mime_type))
        # TODO: check for repeated MIME type?
        content = _parse_indented_text(lines)
        if content:
            content += '\n'
        if _RE_JSON.match(mime_type):
            bundle[mime_type] = _parse_json(content)
        else:
            if content and content.endswith('\n') and content.strip('\n'):
                content = content[:-1]
            bundle[mime_type] = content
    return bundle


def _parse_indented_text(lines):
    return '\n'.join(_IndentedLines(4, lines))


def _check_word_plus_integer(word, line):
    m = _re.match(word + ' ([0-9]|[1-9][0-9]+)$', line)
    if not m:
        raise ParseError(
            'Expected {!r} followed by a space and an integer'.format(word))
    return int(m.group(1))


def _check_word_plus_string(word, line):
    chars = len(word)
    # TODO: check if line[chars + 1] is a space?
    # TODO: use split() or partition()?
    if len(line) < chars + 2 or line[chars] != ' ':
        raise ParseError('Missing string after {!r}'.format(word))
    return line[chars + 1:]


def _check_word(word, line):
    if line.startswith(word):
        if line != word:
            raise ParseError('No text allowed after {!r}'.format(word))
        return True
    else:
        return False


def _parse_json(text):
    if not text:
        return {}
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError as e:
        # Abuse JSONDecodeError constructor to calculate number of lines:
        total = _json.JSONDecodeError('', text, -1).lineno
        raise ParseError(
            'JSON error in column {}: {}'.format(e.colno + 4, e.msg),
            total - e.lineno + 1)
    return data


def _parse_metadata(lines):
    return _parse_json(_parse_indented_text(lines))


def _line(prefix, key, value=None):
    if value is None:
        return '{}{}\n'.format(prefix, key)
    else:
        return '{}{} {}\n'.format(prefix, key, value)


def _mime_bundle(data):
    # TODO: sort MIME types?
    # TODO: alphabetically, by importance?
    for k, v in data.items():
        if _RE_JSON.match(k):
            yield from _json_block('   ' + k, v)
        else:
            if v.endswith('\n') and v.strip('\n'):
                v += '\n'
            yield from _text_block('   ' + k, v)


def _attachment(name, data):
    yield _line(' ', 'attachment', name)
    yield from _mime_bundle(data)


def _code_cell_output(out):
    if out.output_type == 'stream':
        # NB: "name" is required!
        yield _line(' ', 'stream', out.name)
        yield from _indented_block(out.text)
    elif out.output_type in ('display_data', 'execute_result'):
        yield _line(' ', out.output_type)
        # TODO: check if out.execution_count matches cell.execution_count?
        if out.data:
            yield from _mime_bundle(out.data)
        if out.metadata:
            yield from _json_block('  metadata', out.metadata)
    elif out.output_type == 'error':
        yield _line(' ', 'error', out.ename)
        yield from _indented_block(out.evalue)
        yield _line('  ', 'traceback')
        separator = ''
        for frame in out.traceback:
            if separator:
                yield separator
            else:
                separator = '   ~\n'
            for line in frame.splitlines():
                yield '    ' + line + '\n'
    else:
        raise RuntimeError('Unknown output type: {!r}'.format(out.output_type))


def _indented_block(text):
    for line in text.splitlines():
        yield ' ' * 4 + line + '\n'


def _text_block(key, value):
    yield key + '\n'
    yield from _indented_block(value)


def _json_block(key, value):
    yield key + '\n'
    yield from _indented_block(_serialize_json(value))


def _serialize_json(data):
    # Options should be the same as in nbformat!
    return _json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
