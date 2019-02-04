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
    license='MIT',
    keywords=''.split(),
    url='',
    platforms='any',
    classifiers=[
        'Framework :: Jupyter',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
    zip_safe=True,
    entry_points={
        'nbconvert.exporters': [
            'jupyter=jupyter_format.exporters:JupyterExporter',
            'custom_from_jupyter=jupyter_format.exporters:TemplateExporter',
            'html_from_jupyter=jupyter_format.exporters:HTMLExporter',
            'slides_from_jupyter=jupyter_format.exporters:SlidesExporter',
            'latex_from_jupyter=jupyter_format.exporters:LatexExporter',
            'pdf_from_jupyter=jupyter_format.exporters:PDFExporter',
            'markdown_from_jupyter=jupyter_format.exporters:MarkdownExporter',
            'python_from_jupyter=jupyter_format.exporters:PythonExporter',
            'rst_from_jupyter=jupyter_format.exporters:RSTExporter',
            'notebook_from_jupyter=jupyter_format.exporters:NotebookExporter',
            'asciidoc_from_jupyter=jupyter_format.exporters:ASCIIDocExporter',
            'script_from_jupyter=jupyter_format.exporters:ScriptExporter',
            # Just for completeness's sake (same as "jupyter"):
            'jupyter_from_jupyter=jupyter_format.exporters:JupyterExporter',
        ],
    },
)
