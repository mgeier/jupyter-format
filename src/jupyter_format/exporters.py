"""Exporters for nbconvert."""
import nbconvert.exporters as _exp
import nbformat as _nbformat
import traitlets as _traitlets
import jupyter_format as _jf


class JupyterImportMixin:
    """Allow ``*.jupyter`` files as input to exporters.

    This is used in all exporters as a "mixin" class.

    """

    def from_filename(self, filename, resources=None, **kw):
        if filename.endswith(_jf.SUFFIX):
            if resources is None:
                resources = _exp.ResourcesDict()
            resources.setdefault('output_extension', self.file_extension)
            kw.setdefault('jupyter_format', True)
        return super().from_filename(filename, resources, **kw)

    def from_file(self, file, resources=None, jupyter_format=None, **kw):
        if jupyter_format:
            return self.from_notebook_node(
                _jf.deserialize(file), resources=resources, **kw)
        return super().from_file(file, resources=resources, **kw)


class JupyterExporter(JupyterImportMixin, _exp.Exporter):
    """Convert Jupyter notebooks to ``.jupyter`` format."""

    @_traitlets.default('file_extension')
    def _file_extension_default(self):
        return _jf.SUFFIX

    def from_notebook_node(self, nb, resources=None, **kw):
        if nb.nbformat != 4:
            nb = _nbformat.convert(nb, to_version=4)
        nb, resources = super().from_notebook_node(nb, resources, **kw)
        return _jf.serialize(nb), resources


class TemplateExporter(JupyterImportMixin, _exp.TemplateExporter):
    """See :class:`nbconvert.exporters.TemplateExporter`."""


class HTMLExporter(JupyterImportMixin, _exp.HTMLExporter):
    """See :class:`nbconvert.exporters.HTMLExporter`."""

    export_from_notebook = '.jupyter -> HTML'


class SlidesExporter(JupyterImportMixin, _exp.SlidesExporter):
    """See :class:`nbconvert.exporters.SlidesExporter`."""

    export_from_notebook = '.jupyter -> Reveal.js slides'


class LatexExporter(JupyterImportMixin, _exp.LatexExporter):
    """See :class:`nbconvert.exporters.LatexExporter`."""

    export_from_notebook = '.jupyter -> LaTeX'


class PDFExporter(JupyterImportMixin, _exp.PDFExporter):
    """See :class:`nbconvert.exporters.PDFExporter`."""

    export_from_notebook = '.jupyter -> PDF via LaTeX'


class MarkdownExporter(JupyterImportMixin, _exp.MarkdownExporter):
    """See :class:`nbconvert.exporters.MarkdownExporter`."""

    export_from_notebook = '.jupyter -> Markdown'


class PythonExporter(JupyterImportMixin, _exp.PythonExporter):
    """See :class:`nbconvert.exporters.PythonExporter`."""

    export_from_notebook = '.jupyter -> Python'


class RSTExporter(JupyterImportMixin, _exp.RSTExporter):
    """See :class:`nbconvert.exporters.RSTExporter`."""

    export_from_notebook = '.jupyter -> reST'


class NotebookExporter(JupyterImportMixin, _exp.NotebookExporter):
    """See :class:`nbconvert.exporters.NotebookExporter`."""

    export_from_notebook = '.jupyter -> Notebook'


class ASCIIDocExporter(JupyterImportMixin, _exp.ASCIIDocExporter):

    export_from_notebook = '.jupyter -> AsciiDoc'


class ScriptExporter(JupyterImportMixin, _exp.ScriptExporter):
    pass
