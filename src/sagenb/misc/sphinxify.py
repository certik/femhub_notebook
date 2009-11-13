#!/usr/bin/env python
r"""
Process docstrings with Sphinx

Processes docstrings with Sphinx. Can also be used as a commandline script:

``python sphinxify.py <text>``

AUTHORS:

- Tim Joseph Dumol (2009-09-29): initial version
"""
#**************************************************
# Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
#
# Distributed under the terms of the BSD License
#**************************************************
import os, hashlib, re, shutil
from tempfile import mkdtemp

from sphinx.application import Sphinx

try:
    from sage.misc.misc import SAGE_DOC
except ImportError:
    SAGE_DOC = None
    

def is_sphinx_markup(docstring):
    """
    Return True if string is a string that contains Sphinx-style ReST markup.
    """
    # this could be made much more clever
    return ("`" in docstring or "::" in docstring)

def sphinxify(docstring):
    r"""
    Runs Sphinx on a docstring, and outputs the processed documentation.

    INPUT:

    - docstring -- string -- a ReST formatted docstring.

    OUTPUT:

    - string -- Sphinx-processed documentation.

    EXAMPLES::

        sage: from sagenb.misc.sphinxify import sphinxify
        sage: sphinxify('A test')
        '<div class="docstring">\n    \n  <p>A test</p>\n\n\n</div>'
        sage: sphinxify('**Testing**\n`monospace`')
        '<div class="docstring"...<strong>Testing</strong>\n<span class="math"...</p>\n\n\n</div>'
    """
    tmpdir = mkdtemp()
    docstring_hash = hashlib.md5(docstring).hexdigest()
    base_name = os.path.join(tmpdir, docstring_hash)
    html_name = base_name + '.html'

    # This is needed for jsMath to work
    docstring = docstring.replace('\\\\', '\\')

    filed = open(base_name + '.rst', 'w')
    filed.write(docstring)
    filed.close()
    
    # Sphinx setup.  The constructor is Sphinx(srcdir,
    # confdir, outdir, doctreedir, buildername,
    # confoverrides, status, warning, freshenv)
    srcdir = tmpdir

    temp_confdir = False
    if SAGE_DOC and os.path.exists(os.path.join(SAGE_DOC, 'en', 'introspect')):
        confdir = os.path.join(SAGE_DOC, 'en', 'introspect')
    else:
        # This may be inefficient.
        # TODO: Find a faster way to do this
        confdir = mkdtemp()
        temp_confdir = True
        generate_configuration(confdir)
        
    doctreedir = os.path.join(srcdir, docstring_hash)
    confoverrides = {'html_context': {}, 'master_doc' : docstring_hash}

    sphinx_app = Sphinx(srcdir, confdir,  srcdir, doctreedir, 'html',
                        confoverrides, None, None, True)

    sphinx_app.build(None, [base_name + '.rst'])
    if os.path.exists(os.path.join(srcdir, docstring_hash) + '.html'):
        new_html = open(html_name, 'r').read()
        new_html = new_html.replace('<pre>', '<pre class="literal-block">')
                
        # Translate URLs for media from something like
        #    "../../media/...path.../blah.png"
        # or
        #    "/media/...path.../blah.png"
        # to
        #    "/doc/static/reference/media/...path.../blah.png"
        new_html = re.sub("""src=['"](/?\.\.)*/?media/([^"']*)['"]""",
                          'src="/doc/static/reference/media/\\2"',
                                  new_html)
    else:
         print "BUG -- error constructing html"
         new_html = '<pre class="introspection">%s</pre>' % docstring

    if temp_confdir:
        shutil.rmtree(confdir, ignore_errors=True)
    shutil.rmtree(tmpdir, ignore_errors=True)

    return new_html

def generate_configuration(directory):
    r"""
    Generates Sphinx configuration at ``directory``.

    EXAMPLES::

        sage: from sagenb.misc.sphinxify import generate_configuration
        sage: import tempfile, os
        sage: tmpdir = tempfile.mkdtemp()
        sage: generate_configuration(tmpdir)
        sage: open(os.path.join(tmpdir, 'conf.py')).read()
        '\n...extensions =...templates_path...source = False\n...'
    """
    conf = r'''
###########################################################
# Taken from  `$SAGE_ROOT$/devel/sage/doc/common/conf.py` #
###########################################################
import sys, os
# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

jsmath_path = 'easy/load.js'

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u""
copyright = u'2005--2009, The Sage Development Team'

#version = '3.1.2'
# The full version, including alpha/beta/rc tags.
#release = '3.1.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

# The reST default role (used for this markup: `text`) to use for all documents.
default_role = 'math'

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = 'sagelogo-word.ico'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'favicon.ico'

# If we're using jsMath, we prepend its location to the static path
# array.  We can override / overwrite selected files by putting them
# in the remaining paths.
if 'SAGE_DOC_JSMATH' in os.environ:
    jsmath_static = os.path.join(SAGE_ROOT, 'local/notebook/javascript/jsmath')
    html_static_path.insert(0, jsmath_static)

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
#htmlhelp_basename = ''


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = []

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = 'sagelogo-word.png'

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''
latex_preamble = '\usepackage{amsmath}\n\usepackage{amsfonts}\n'

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

#####################################################
# add LaTeX macros for Sage
try:
    from sage.misc.latex_macros import sage_latex_macros
except ImportError:
    sage_latex_macros = []

try:
    pngmath_latex_preamble  # check whether this is already defined
except NameError:
    pngmath_latex_preamble = ""
    
for macro in sage_latex_macros:
    # used when building latex and pdf versions
    latex_preamble += macro + '\n'
    # used when building html version
    pngmath_latex_preamble += macro + '\n'

#####################################################
def process_docstring_aliases(app, what, name, obj, options, docstringlines):
    """
    Change the docstrings for aliases to point to the original object.
    """
    basename = name.rpartition('.')[2]
    if hasattr(obj, '__name__') and obj.__name__ != basename:
        docstringlines[:] = ['See :obj:`%s`.' % name]

def process_directives(app, what, name, obj, options, docstringlines):
    """
    Remove 'nodetex' and other directives from the first line of any
    docstring where they appear.
    """
    if len(docstringlines) == 0:
        return
    first_line = docstringlines[0]
    directives = [ d.lower() for d in first_line.split(',') ]
    if 'nodetex' in directives:
        docstringlines.pop(0)

def process_docstring_cython(app, what, name, obj, options, docstringlines):
    """
    Remove Cython's filename and location embedding.
    """
    if len(docstringlines) <= 1:
        return

    first_line = docstringlines[0]
    if first_line.startswith('File:') and '(starting at' in first_line:
        #Remove the first two lines
        docstringlines.pop(0)
        docstringlines.pop(0)

def process_docstring_module_title(app, what, name, obj, options, docstringlines):
    """
    Removes the first line from the beginning of the module's docstring.  This 
    corresponds to the title of the module's documentation page.
    """
    if what != "module":
        return

    #Remove any additional blank lines at the beginning
    title_removed = False
    while len(docstringlines) > 1 and not title_removed:
        if docstringlines[0].strip() != "":
            title_removed = True
        docstringlines.pop(0)

    #Remove any additional blank lines at the beginning
    while len(docstringlines) > 1:
        if docstringlines[0].strip() == "":
            docstringlines.pop(0)
        else:
            break

def skip_NestedClass(app, what, name, obj, skip, options):
    """
    Don't include the docstring for any class/function/object in
    sage.misc.misc whose ``name`` contains "MainClass.NestedClass".
    (This is to avoid some Sphinx warnings when processing
    sage.misc.misc.)  Otherwise, abide by Sphinx's decision.
    """
    skip_nested = str(obj).find("sage.misc.misc") != -1 and name.find("MainClass.NestedClass") != -1
    return skip or skip_nested
        
def setup(app):
    app.connect('autodoc-process-docstring', process_docstring_cython)
    app.connect('autodoc-process-docstring', process_directives)
    app.connect('autodoc-process-docstring', process_docstring_module_title)
    app.connect('autodoc-skip-member', skip_NestedClass)

#################################################################
# Taken from `$SAGE_ROOT$/devel/sage/doc/en/introspect/conf.py` #
#################################################################

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.jsmath']

templates_path = ['templates']
html_static_path = ['static']

html_use_modindex = False
html_use_index = False
html_split_index = False
html_copy_source = False
    '''

    ###############################################################################
    # Taken from `$SAGE_ROOT$/devel/sage/doc/en/introspect/templates/layout.html` #
    ###############################################################################
    layout = r"""
<div class="docstring">
    {% block body %}{% endblock %}
</div>
"""
    os.makedirs(os.path.join(directory, 'templates'))
    os.makedirs(os.path.join(directory, 'static'))
    open(os.path.join(directory, 'conf.py'), 'w').write(conf)
    open(os.path.join(directory, '__init__.py'), 'w').write('')
    open(os.path.join(directory, 'templates', 'layout.html'), 'w').write(layout)
    open(os.path.join(directory, 'static', 'empty'), 'w').write('')

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        print sphinxify(sys.argv[1])
    else:
        print """Usage:
%s 'docstring'

docstring -- docstring to be processed
"""
