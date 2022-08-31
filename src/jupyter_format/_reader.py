"""Functions for reading Jupyter files."""
import json
import re

import nbformat

from . import ParseError
from ._common import RE_JSON


def deserialize(source):
    """Convert ``.jupyter`` string representation to Jupyter notebook.

    Lines have to be terminated with ``'\\n'``
    (a.k.a. :term:`universal newlines` mode).

    If *source* is an iterable, line terminators may be omitted.

    :param source: Content of ``.jupyter`` file.
    :type source: str or iterable of str
    :returns: A notebook node.
    :rtype: nbformat.NotebookNode

    """
    return Parser(source).parse()


def code_output(line, lines, cell):
    kwargs = {}
    if line.startswith('stream'):
        output_type = 'stream'
        # NB: "name" is required!
        kwargs['name'] = word_plus_string('stream', line)
        kwargs['text'] = indented_block(lines)
    elif (word('display_data', line) or
            word('execute_result', line)):
        output_type = line
        if output_type == 'execute_result':
            kwargs['execution_count'] = cell.execution_count
        kwargs['data'] = mime_bundle(lines)
        for line in indented(2, lines):
            if not word('output_metadata', line):
                raise ParseError(
                    "Only 'output_metadata' is allowed here, not {!r}"
                    .format(line))
            kwargs['metadata'] = metadata(lines)
            break
    elif line.startswith('error'):
        output_type = 'error'
        # NB: All fields are required
        kwargs['ename'] = word_plus_string('error', line)
        # TODO: check for non-empty?
        kwargs['evalue'] = indented_block(lines)
        kwargs['traceback'] = traceback(lines)
    else:
        raise ParseError(
            'Expected output type, got {!r}'.format(line))
    for line in indented(2, lines):
        raise ParseError('Invalid output data: {!r}'.format(line))
    out = nbformat.v4.new_output(output_type, **kwargs)
    cell.outputs.append(out)


def traceback(lines):
    for line in indented(2, lines):
        if not word('traceback', line):
            raise ParseError(
                "Expected 'traceback', got {!r}".format(line))
        traceback = []
        while True:
            frame = indented_block(lines)
            traceback.append(frame)
            for line in indented(3, lines):
                if word('-', line):
                    break
                raise ParseError(
                    'Invalid traceback separator: {!r}'.format(line))
            else:
                break
        return traceback
    raise ParseError("Missing 'traceback'")


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


class Parser:

    def __init__(self, source):
        if isinstance(source, str):
            source = source.splitlines()
        self._iter = iter(source)
        self.current_number = 0
        self.advance()

    def current_line(self):
        if isinstance(self._next, StopIteration):
            raise self._next
        return self._next

    def advance(self):
        try:
            self._next = next(self._iter).rstrip('\n')
        except StopIteration as e:
            self._next = e
        self.current_number += 1

    def parse(self):
        try:
            nb = self.parse_without_exception_handling()
        except ParseError as e:
            if len(e.args) == 1:
                # Add line number
                e.args += self.current_number,
            elif len(e.args) == 2:
                # Apply line number offset
                e.args = e.args[0], self.current_number - e.args[1]
            raise e
        except Exception as e:
            raise ParseError(
                type(e).__name__ + ': ' + str(e), self.current_number) from e
        return nb

    def parse_without_exception_handling(self):
        nb = self.parse_header()
        for cell in CellParser(self):
            nb.cells.append(cell)
        nb.metadata.update(self.parse_notebook_metadata())

        # TODO: check trailing garbage

        #'All notebook metadata lines must be indented by 4 spaces '
        #'and no subsequent lines are allowed')
        #raise ParseError(
        #    'Unexpected content after notebook metadata: {next_line!r}', i)

        return nb

    def parse_header(self):
        try:
            line = self.current_line()
            line = line.rstrip()
            name, _, version = line.partition(' ')
            major, _, minor = version.partition('.')
            major = parse_integer(major)
            minor = parse_integer(minor)
            if name != 'nbformat' or None in (major, minor):
                raise ParseError(
                    "Expected 'nbformat X.Y', with integers X and Y, "
                    f'got {line!r}')
        except StopIteration:
            raise ParseError('First line missing, expected "nbformat X.Y"')
        if nb.nbformat != 4:
            raise ParseError('Only v4 notebooks are currently supported')
        nb = nbformat.v4.new_notebook()
        nb.nbformat = major
        nb.nbformat_minor = minor
        self.advance()
        return nb

    def parse_indented_block(self):
        """Parse block of text that's indented by 4 spaces.

        Blank lines are included as empty lines.

        """
        lines = []
        while True:
            try:
                line = self.current_line()
            except StopIteration:
                break
            if line.startswith(' ' * 4):
                lines.append(line[4:])
            elif not line.strip():
                lines.append('')  # Blank line
            else:
                break
            self.advance()
        return '\n'.join(lines)

    def parse_mime_bundle(self):
        bundle = {}
        for mime_type, data in MimeTypeParser(self):
            if mime_type in bundle:
                # TODO: this will have the wrong line number:
                raise ParseError(f'Duplicate MIME type: {mime_type!r}')
            bundle[mime_type] = data
        return bundle

    def parse_notebook_metadata(self):
        try:
            line = self.current_line()
        except StopIteration:
            return {}
        # TODO: this has been checked before?
        assert line.rstrip() = 'metadata'
        self.advance()
        # TODO: check for empty data?
        return parse_json(self.parse_indented_block())


class CellParser:

    def __init__(self, parser):
        self._parser = parser

    def __next__(self):
        p = self._parser
        # NB: This may raise StopIteration:
        line = p.current_line()
        cell_type, _, arguments = line.partition(' ')
        if cell_type == 'metadata':
            # This will be handled afterwards
            raise StopIteration

        if cell_type == 'markdown':
            cell = nbformat.v4.new_markdown_cell()
        elif cell_type == 'code':
            cell = nbformat.v4.new_code_cell()
        elif cell_type == 'raw':
            cell = nbformat.v4.new_raw_cell()
        else:
            # TODO: error handling

            #"Expected (unindented) cell type or 'metadata', "
            #"got {!r}".format(line))
            raise NotImplementedError

        # Additional whitespace between arguments is allowed for convenience:
        arguments = arguments.split()
        if cell_type == 'code' and len(arguments) >= 1:
            cell.execution_count = parse_integer(arguments[0])
            if cell.execution_count is not None:
                del arguments[0]
        # TODO: check nbformat_minor if IDs are supported?
        if len(arguments) == 1:
            cell.id = arguments[0]
        elif len(arguments) > 1:
            raise ParseError(
                f'Too many arguments for {cell_type} cell: {line!r}')

        # First line has been parsed successfully
        p.advance()

        cell.source = p.parse_indented_block()

        if cell.cell_type in ('markdown', 'raw'):
            # attachments (since v4.1)
            for name, attachment in AttachmentParser(p):
                if name in cell.attachments:
                    raise ParseError(f'Duplicate attachment name: {name!r}')
                cell.attachments[name] = attachment
        elif cell.cell_type == 'code':
            for output in p.parse_outputs():
                cell.outputs.append(output)
        cell.metadata.update(p.parse_cell_metadata())
        return cell


class AttachmentParser:

    def __init__(self, parser):
        self._parser = parser

    def __next__(self):
        p = self._parser
        # NB: This may raise StopIteration:
        line = p.current_line()
        prefix, _, name = line.partition('- attachment ')
        name = name.strip()
        if prefix or not name:
            raise StopIteration
        p.advance()
        return name, p.parse_mime_bundle()


class MimeTypeParser:

    def __init__(self, parser):
        self._parser = parser

    def __next__(self):
        p = self._parser
        # NB: This may raise StopIteration:
        line = p.current_line()
        prefix, _, mime_type = line.partition('  - ')
        mime_type = mime_type.strip()
        if prefix or not mime_type:
            raise StopIteration
        p.advance()
        content = p.parse_indented_block()
        if not content:
            raise ParseError(f'no content for MIME type {mime_type}')
        if RE_JSON.match(mime_type):
            # TODO: + \n?
            content = parse_json(content + '\n')
        elif content.endswith('\n') and content.strip('\n'):
            content = content[:-1]
        return mime_type, content


def parse_integer(text):
    """Parse a valid integer or return None."""
    # NB: Leading zeros and +/- are not allowed.
    return re.fullmatch('[0-9]|[1-9][0-9]+', text) and int(text)
