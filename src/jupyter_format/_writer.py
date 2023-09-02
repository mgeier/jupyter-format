"""Functions for writing Jupyter files."""
import json

from ._common import RE_JSON


def generate_lines(nb):
    """Generator yielding lines to be written to ``.jupyter`` files.

    Each of the lines has a line separator at the end, therefore it can
    e.g. be used in :meth:`~io.IOBase.writelines`.

    :param nbformat.NotebookNode nb: A notebook node.

    """
    if nb.nbformat != 4:
        raise RuntimeError('Currently, only notebook version 4 is supported')
    yield line('nbformat', f'{nb.nbformat}.{nb.nbformat_minor}')
    for cell in nb.cells:
        cell_type = cell.cell_type
        arguments = []
        if cell_type == 'code' and cell.execution_count is not None:
            arguments.append(str(cell.execution_count))
        if cell.id is not None:
            arguments.append(f'id:{cell.id}')
        yield line(cell_type, ' '.join(arguments))
        yield from indented_block(cell.source + '\n')
        if cell_type in ('markdown', 'raw'):
            # attachments (since v4.1)
            for name, data in cell.get('attachments', {}).items():
                yield from attachment(name, data)
        elif cell_type == 'code':
            for out in cell.outputs:
                yield from code_cell_output(out)
        else:
            raise RuntimeError(f'Unknown cell type: {cell_type!r}')
        if cell.metadata:
            yield from json_block('- metadata', cell.metadata)
    if nb.metadata:
        yield from json_block('metadata', nb.metadata)


def serialize(nb):
    """Convert a Jupyter notebook to a string in ``.jupyter`` format.

    :param nbformat.NotebookNode nb: A notebook node.
    :returns: ``.jupyter`` file content.
    :rtype: str

    """
    return ''.join(generate_lines(nb))


def attachment(name, data):
    yield line('- attachment', name)
    yield from mime_bundle(data)


def code_cell_output(out):
    if out.output_type == 'stream':
        # NB: "name" is required!
        yield line('- stream', out.name)
        yield from indented_block(out.text)
    elif out.output_type in ('display_data', 'execute_result'):
        # TODO: check if out.execution_count matches cell.execution_count?
        header = f'- {out.output_type}'
        if out.metadata:
            yield from json_block(header, out.metadata)
        else:
            yield line(header)
        if out.data:
            yield from mime_bundle(out.data)
    elif out.output_type == 'error':
        yield line('- error', out.ename)
        yield from indented_block(out.evalue)
        for frame in out.traceback:
            yield '  --\n'
            for l in frame.splitlines():
                yield ' ' * 4 + l + '\n'
    else:
        raise RuntimeError('Unknown output type: {!r}'.format(out.output_type))


def mime_bundle(data):
    # TODO: sort MIME types?
    # TODO: alphabetically, by importance?
    for k, v in data.items():
        if RE_JSON.match(k):
            yield from json_block('  - ' + k, v)
        else:
            if v.endswith('\n') and v.strip('\n'):
                v += '\n'
            yield from text_block('  - ' + k, v)


def line(key, value=''):
    if value:
        return f'{key} {value}\n'
    else:
        return f'{key}\n'


def text_block(key, value):
    yield key + '\n'
    yield from indented_block(value)


def json_block(key, value):
    yield key + '\n'
    yield from indented_block(serialize_json(value))


def indented_block(text):
    for l in text.splitlines():
        yield ' ' * 4 + l + '\n'


def serialize_json(data):
    # Options should be the same as in nbformat!
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
