project = 'Jupyter Format'
author = 'Matthias Geier'

extensions = [
    'nbsphinx',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_last_updated_by_git',
]

highlight_language = 'none'
master_doc = 'index'
exclude_patterns = ['my-new-notebook.*']

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'nbconvert': ('https://nbconvert.readthedocs.io/en/latest', None),
    'nbformat': ('https://nbformat.readthedocs.io/en/latest', None),
}

default_role = 'any'

autodoc_inherit_docstrings = False

# -- nbsphinx-related options ---------------------------------------------

nbsphinx_custom_formats = {
    '.jupyter': 'jupyter_format.deserialize',
}

nbsphinx_execute_arguments = ['--InlineBackend.figure_formats={"svg", "pdf"}']

jinja_define = """
{% set docname = 'doc/' + env.doc2path(env.docname, base=None) %}
{% set latex_href = ''.join([
    '\href{https://github.com/mgeier/jupyter-format/blob/',
    env.config.release,
    '/',
    docname | escape_latex,
    '}{\sphinxcode{\sphinxupquote{',
    docname | escape_latex,
    '}}}',
]) %}
"""

nbsphinx_prolog = jinja_define + r"""
.. raw:: html

    <div class="admonition note">
      This page was generated from
      <a class="reference external" href="https://github.com/mgeier/jupyter-format/blob/{{ env.config.release|e }}/{{ docname|e }}">{{ docname|e }}</a>.
      Interactive online version:
      <span style="white-space: nowrap;"><a href="https://mybinder.org/v2/gh/mgeier/jupyter-format/{{ env.config.release|e }}?filepath={{ docname|e }}"><img alt="Binder badge" src="https://mybinder.org/badge_logo.svg" style="vertical-align:text-bottom"></a>.</span>
    </div>

.. raw:: latex

    \nbsphinxstartnotebook{\scriptsize\noindent\strut
    \textcolor{gray}{The following section was generated from {{ latex_href }}
    \dotfill}}
"""

nbsphinx_epilog = jinja_define + r"""
.. raw:: latex

    \nbsphinxstopnotebook{\scriptsize\noindent\strut
    \textcolor{gray}{\dotfill\ {{ latex_href }} ends here.}}
"""

# -- Get version information and date from Git ----------------------------

try:
    from subprocess import check_output
    release = check_output(['git', 'describe', '--tags', '--always'])
    release = release.decode().strip()
    today = check_output(['git', 'show', '-s', '--format=%ad', '--date=short'])
    today = today.decode().strip()
except Exception:
    release = '<unknown>'
    today = '<unknown date>'

# -- Options for HTML output ----------------------------------------------

html_title = project + ' version ' + release
html_theme = 'insipid'
html_show_copyright = False
html_permalinks_icon = '§'
html_copy_source = False

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    'papersize': 'a4paper',
    'printindex': '',
    'sphinxsetup': r"""
        VerbatimColor={HTML}{F5F5F5},
        VerbatimBorderColor={HTML}{E0E0E0},
        noteBorderColor={HTML}{E0E0E0},
        noteborder=1.5pt,
        warningBorderColor={HTML}{E0E0E0},
        warningborder=1.5pt,
        warningBgColor={HTML}{FBFBFB},
    """,
    'preamble': r"""
\usepackage[sc,osf]{mathpazo}
\linespread{1.05}  % see http://www.tug.dk/FontCatalogue/urwpalladio/
\renewcommand{\sfdefault}{pplj}  % Palatino instead of sans serif
\IfFileExists{zlmtt.sty}{
    \usepackage[light,scaled=1.05]{zlmtt}  % light typewriter font from lmodern
}{
    \renewcommand{\ttdefault}{lmtt}  % typewriter font from lmodern
}
""",
}

latex_documents = [
    (master_doc, 'Jupyter-Format.tex', project, author, 'howto'),
]

latex_show_urls = 'footnote'
latex_show_pagerefs = True
