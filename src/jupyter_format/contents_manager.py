"""JupyterLab and Classic Notebook integration.

Add the following line to your ``jupyter_notebook_config.py``::

    c.NotebookApp.contents_manager_class = 'jupyter_format.contents_manager.FileContentsManager'

"""
import notebook.services.contents.filemanager as _fm
import jupyter_format as _jf


class FileContentsManager(_fm.FileContentsManager):

    __doc__ = __doc__

    def get(self, path, content=True, type=None, format=None):
        if type is None and path.endswith(_jf.SUFFIX):
            type = 'notebook'
        return super().get(path, content, type, format)

    def _read_notebook(self, os_path, as_version=4):
        if not os_path.endswith(_jf.SUFFIX):
            return super()._read_notebook(os_path, as_version)

        with self.open(os_path, 'r', encoding='utf-8', newline=None) as f:
            try:
                assert as_version == 4
                return _jf.deserialize(f)
            except Exception as e:
                raise _fm.web.HTTPError(400, str(e))

    def _save_notebook(self, os_path, nb):
        if not os_path.endswith(_jf.SUFFIX):
            return super()._save_notebook(os_path, nb)

        # TODO: raise proper exception on error?
        with self.atomic_writing(os_path, text=True,
                                 newline=None,  # "universal newlines"
                                 encoding='utf-8') as f:
            f.writelines(_jf.generate_lines(nb))
