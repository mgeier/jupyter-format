from setuptools import setup

# "import" __version__
__version__ = 'unknown'
for line in open('src/jupyter_format/__init__.py'):
    if line.startswith('__version__'):
        exec(line)
        break

setup(
    name='jupyter_format',
    version=__version__,
    package_dir={'': 'src'},
    packages=['jupyter_format'],
    install_requires=['nbformat'],
    python_requires='>=3.4',
    author='Matthias Geier',
    author_email='Matthias.Geier@gmail.com',
    description='An Experimental New Storage Format For Jupyter Notebooks',
    long_description=open('README.rst').read(),
    keywords=''.split(),
    url='https://jupyter-format.readthedocs.io/',
    project_urls={
        'Documentation': 'https://jupyter-format.readthedocs.io/',
        'Source Code': 'https://github.com/mgeier/jupyter-format/',
        'Bug Tracker': 'https://github.com/mgeier/jupyter-format/issues/',
    },
    platforms='any',
    classifiers=[
        'Framework :: Jupyter',
        'Intended Audience :: Science/Research',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
    zip_safe=True,
    entry_points={
        'nbconvert.exporters': [
            'jupyter=jupyter_format.exporters:JupyterExporter',
            'custom-from-jupyter=jupyter_format.exporters:TemplateExporter',
            'html-from-jupyter=jupyter_format.exporters:HTMLExporter',
            'slides-from-jupyter=jupyter_format.exporters:SlidesExporter',
            'latex-from-jupyter=jupyter_format.exporters:LatexExporter',
            'pdf-from-jupyter=jupyter_format.exporters:PDFExporter',
            'markdown-from-jupyter=jupyter_format.exporters:MarkdownExporter',
            'python-from-jupyter=jupyter_format.exporters:PythonExporter',
            'rst-from-jupyter=jupyter_format.exporters:RSTExporter',
            'notebook-from-jupyter=jupyter_format.exporters:NotebookExporter',
            'asciidoc-from-jupyter=jupyter_format.exporters:ASCIIDocExporter',
            'script-from-jupyter=jupyter_format.exporters:ScriptExporter',
            # Convenience alias for "notebook-from-jupyter":
            'ipynb-from-jupyter=jupyter_format.exporters:NotebookExporter',
            # Just for completeness's sake (same as "jupyter"):
            'jupyter-from-jupyter=jupyter_format.exporters:JupyterExporter',
        ],
    },
)
