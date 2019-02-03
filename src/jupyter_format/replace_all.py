#!/usr/bin/env python3
"""Script to recursively replace ``.ipynb`` with ``.jupyter`` files.

Usage::

    python3 -m jupyter_format.replace_all --recursive --yes

WARNING: This deletes all original files!

Usage to apply this to the whole history of a Git branch::

    git filter-branch --tree-filter "python3 -m jupyter_format.replace_all --recursive --yes"

"""
from pathlib import Path
import sys

from jupyter_format.exporters import JupyterExporter
from nbconvert.writers import FilesWriter


def ipynb_to_jupyter(path):
    """Replace given ``.ipynb`` file with a ``.jupyter`` file.

    WARNING: This deletes the original file!

    :param path: Path to ``.ipynb`` file.
    :type path: os.PathLike or str

    """
    path = Path(path)
    exporter = JupyterExporter()
    nb, resources = exporter.from_filename(str(path))
    writer = FilesWriter()
    writer.write(nb, resources, notebook_name=path.with_suffix('').name)
    path.unlink()


def replace_all_recursive(start_dir, mapfunction=map):
    """Replace all ``.ipynb`` files recursively.

    WARNING: This deletes all original files!

    :param path: Starting directory.
    :type path: os.PathLike or str
    :param mapfunction: :func:`map`-like function that can be provided
        in order to enable parallelization.

    """
    notebooks = Path(start_dir).rglob('*.ipynb')
    for _ in mapfunction(ipynb_to_jupyter, notebooks):
        # NB: A lazy mapfunction must be consumed to produce its side effects
        pass


if __name__ == '__main__':
    if set(sys.argv[1:]) != {'--recursive', '--yes'}:
        sys.exit('This replaces all *.ipynb files recursively! '
                 'Use --recursive --yes to consent.')

    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor() as executor:
        replace_all_recursive('.', mapfunction=executor.map)
