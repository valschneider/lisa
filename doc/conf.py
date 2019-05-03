# -*- coding: utf-8 -*-
#
# LISA documentation build configuration file, created by
# sphinx-quickstart on Tue Dec 13 14:20:00 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import logging
import os
import re
import subprocess
import sys
import unittest
import textwrap
import json

from docutils import nodes
from sphinx.util.docfields import TypedField
from sphinx import addnodes

# This shouldn't be needed, as using a virtualenv + setup.py should set up the
# sys.path correctly. However that seems to be half broken on ReadTheDocs, so
# manually set it here
sys.path.insert(0, os.path.abspath('../'))

# Import our packages after modifying sys.path
import lisa
from lisa.utils import LISA_HOME
from lisa.doc.helpers import (
    autodoc_process_test_method, autodoc_process_analysis_events
)

# This ugly hack is required because by default TestCase.__module__ is
# equal to 'case', so sphinx replaces all of our TestCase uses to
# unittest.case.TestCase, which doesn't exist in the doc.
for name, obj in vars(unittest).items():
    try:
        m = obj.__module__
        obj.__module__ = 'unittest' if m == 'unittest.case' else m
    except Exception: pass

# This is a hack to prevent :ivar: docs from attempting to create a reference
# Credit goes to https://stackoverflow.com/a/41184353/5096023
def patched_make_field(self, types, domain, items, env=None):
    # type: (List, unicode, Tuple) -> nodes.field
    def handle_item(fieldarg, content):
        par = nodes.paragraph()
        par += addnodes.literal_strong('', fieldarg)  # Patch: this line added
        #par.extend(self.make_xrefs(self.rolename, domain, fieldarg,
        #                           addnodes.literal_strong))
        if fieldarg in types:
            par += nodes.Text(' (')
            # NOTE: using .pop() here to prevent a single type node to be
            # inserted twice into the doctree, which leads to
            # inconsistencies later when references are resolved
            fieldtype = types.pop(fieldarg)
            if len(fieldtype) == 1 and isinstance(fieldtype[0], nodes.Text):
                typename = u''.join(n.astext() for n in fieldtype)
                par.extend(self.make_xrefs(self.typerolename, domain, typename,
                                           addnodes.literal_emphasis))
            else:
                par += fieldtype
            par += nodes.Text(')')
        par += nodes.Text(' -- ')
        par += content
        return par

    fieldname = nodes.field_name('', self.label)
    if len(items) == 1 and self.can_collapse:
        fieldarg, content = items[0]
        bodynode = handle_item(fieldarg, content)
    else:
        bodynode = self.list_type()
        for fieldarg, content in items:
            bodynode += nodes.list_item('', handle_item(fieldarg, content))
    fieldbody = nodes.field_body('', bodynode)
    return nodes.field('', fieldname, fieldbody)

TypedField.make_field = patched_make_field


RTD = (os.getenv('READTHEDOCS') == 'True')

# For ReadTheDocs only: source init_env and get all env var defined by it.
if RTD:
    source_env = {
        **os.environ,
        # LISA_USE_VENV=0 will avoid re-installing LISA automatically,
        # which would be useless.
        'LISA_USE_VENV': '0',
    }
    # If LISA_HOME is set, sourcing the script won't work
    source_env.pop('LISA_HOME', None)

    script = textwrap.dedent(
        """
        source init_env >&2
        python -c 'import os, json; print(json.dumps(dict(os.environ)))'
        """
    )
    out = subprocess.check_output(
        ['bash', '-c', script],
        cwd=LISA_HOME,
        # Reset the environment, including LISA_HOME to allow sourcing without
        # any issue
        env=source_env,
    )
    os.environ.update(json.loads(out))
    print(os.environ)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.imgmath',
    'sphinx.ext.viewcode',
    'sphinx.ext.inheritance_diagram',
    'sphinxcontrib.plantuml',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'LISA'
copyright = u'2017, ARM-Software'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    git_description = subprocess.check_output(
        ['git', 'describe', '--tags', '--match=v??.??'])
    version = re.match('v([0-9][0-9]\.[0-9][0-9]).*', git_description).group(1)
except Exception as e:
    logging.info("Couldn't set project version from git: {}".format(e))
    version = lisa.__version__

version = str(version)
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'LISAdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'LISA.tex', u'LISA Documentation',
   u'ARM-Software', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'lisa', u'LISA Documentation',
     [u'ARM-Software'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'LISA', u'LISA Documentation',
   u'ARM-Software', 'LISA', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

intersphinx_mapping = {
    'python' : ('https://docs.python.org/3', None),
    'pandas' : ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'matplotlib' : ('https://matplotlib.org', None),
    'numpy': ('http://docs.scipy.org/doc/numpy', None),
    # XXX: Doesn't seem to work, might be due to how devlib doc is generated
    'wa' : ('https://devlib.readthedocs.io/en/latest/', None),
    'trappy' : ('https://pythonhosted.org/TRAPpy', None),
    'bart' :   ('https://pythonhosted.org/bart-py/', None),
    'wa' : ('https://workload-automation.readthedocs.io/en/latest/', None),
}

#
# Fix autodoc
#

# Include __init__ docstrings (obviously)
autoclass_content = 'both'

autodoc_member_order = 'bysource'

autodoc_default_options = {
    'show-inheritance' : '', # Show parent class
    'undoc-members' : '',    # Show members even if they don't have docstrings
}
autodoc_inherit_docstrings = True

def setup(app):
    app.connect('autodoc-process-docstring', autodoc_process_test_method)
    app.connect('autodoc-process-docstring', autodoc_process_analysis_events)

# vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab:
