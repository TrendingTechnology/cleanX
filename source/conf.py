# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
import sys, subprocess
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'cleanX'
copyright = '2021, doctormakeda@gmail.com'
author = 'doctormakeda@gmail.com'

# The full version, including alpha/beta/rc tags
try:
    tag = subprocess.check_output([
        'git',
        '--no-pager',
        'describe',
        '--abbrev=0',
        '--tags',
    ]).strip().decode()
except subprocess.CalledProcessError as e:
    print(e.output)
    tag = 'v0.0.0'

release = tag[1:]


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.imgmath',
    'sphinx.ext.intersphinx',

    # third-party
    'sphinx_click',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'nature'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

extlinks = {}

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__,__iter__,__reduce__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'inherited-members': True,
}

intersphinx_mapping = {
    'python': (
        'https://docs.python.org/{.major}'.format(
            sys.version_info,
        ),
        None,
    ),
    'numpy': ('https://docs.scipy.org/doc/numpy/', None),
    'matplotlib': ('http://matplotlib.org', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'pydicom': (
        'https://pydicom.github.io/pydicom/stable/',
        None,
    ),
}


def is_error(obj):
    return isinstance(obj, Exception)


conditionally_ignored = {
    '__reduce__': is_error,
    '__init__': is_error,
    'with_traceback': is_error,
    'args': is_error,
}

def skip_member_handler(app, objtype, membername, member, skip, options):
    ignore_checker = conditionally_ignored.get(membername)
    if ignore_checker:
        frame = sys._getframe()
        while frame.f_code.co_name != 'filter_members':
            frame = frame.f_back

        suspect = frame.f_locals['self'].object
        return not ignore_checker(suspect)
    return skip


def setup(app):
    app.connect('autodoc-skip-member', skip_member_handler)
