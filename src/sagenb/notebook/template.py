# -*- coding: utf-8 -*-
"""
HTML Templating for the Notebook

AUTHORS:

- Bobby Moretti (2007-07-18): initial version

- Timothy Clemans and Mike Hansen (2008-10-27): major update
"""
#############################################################################
#       Copyright (C) 2007 William Stein <wstein@gmail.com>
#  Distributed under the terms of the GNU General Public License (GPL)
#  The full text of the GPL is available at:
#                  http://www.gnu.org/licenses/
#############################################################################

import jinja
import sys

from sagenb.misc.misc import SAGE_VERSION, DATA


TEMPLATE_PATH = DATA + '/templates/'
env = jinja.Environment(loader=jinja.FileSystemLoader(TEMPLATE_PATH))

def contained_in(container):
    """
    Given a container, returns a function which takes an environment,
    context, and value and returns True if that value is in the
    container and False otherwise.  This is registered and used as a
    test in the templates.

    INPUT:

    - ``container`` - a container, e.g., a list or dictionary

    EXAMPLES::

        sage: from sagenb.notebook.template import contained_in
        sage: f = contained_in([1,2,3])
        sage: f(None, None, 2)
        True
        sage: f(None, None, 4)
        False
    """
    def wrapped(env, context, value):
        return value in container
    return wrapped
    
env.tests['contained_in'] = contained_in

#A dictionary containing the default context
#The values in this dictionary will be updated
#by the 
default_context = {'sitename': 'Sage Notebook',
                   'sage_version': SAGE_VERSION}

def template(filename, **user_context): 
    """
    Returns HTML, CSS, etc., for a template file rendered in the given
    context.

    INPUT:

    - ``filename`` - a string; the filename of the template relative
      to ``sagenb/data/templates``

    - ``user_context`` - a dictionary; the context in which to evaluate
      the file's template variables

    OUTPUT:
      
    - a string - the rendered HTML, CSS, etc.

    EXAMPLES::

        sage: from sagenb.notebook.template import template
        sage: s = template('yes_no.html'); type(s)
        <type 'str'>
        sage: 'Yes' in s
        True

        sage: from sagenb.notebook.template import template
        sage: u = unicode('Are Gröbner bases awesome?','utf-8')
        sage: s = template('yes_no.html',message=u)
        sage: 'Gr\xc3\xb6bner' in s
        True
    """
    try:
        tmpl = env.get_template(filename)
    except jinja.exceptions.TemplateNotFound:
        return "Notebook Bug -- missing template %s"%filename
    context = dict(default_context)
    context.update(user_context)
    r = tmpl.render(**context) 
    return r.encode('utf-8')
