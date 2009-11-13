r"""
Inspect Python, Sage, and Cython objects.

This module extends parts of Python's inspect module to Cython objects.

AUTHORS:

- originally taken from Fernando Perez's IPython
- William Stein (extensive modifications)
- Nick Alexander (extensions)
- Nick Alexander (testing)

EXAMPLES::

    sage: from sagenb.misc.sageinspect import *

Test introspection of modules defined in Python and Cython files:

Cython modules::

    sage: sage_getfile(sage.rings.rational)
    '.../rational.pyx'

    sage: sage_getdoc(sage.rings.rational).lstrip()
    'Rational Numbers...'

    sage: sage_getsource(sage.rings.rational)[5:]
    'Rational Numbers...'

Python modules::

    sage: import sagenb.misc.sageinspect
    sage: sage_getfile(sagenb.misc.sageinspect)
    '.../sageinspect.py'

    sage: print sage_getdoc(sagenb.misc.sageinspect).lstrip()[:40]
    Inspect Python, Sage, and Cython objects

    sage: sage_getsource(sagenb.misc.sageinspect).lstrip()[5:-1]
    'Inspect Python, Sage, and Cython objects...'

Test introspection of classes defined in Python and Cython files:

Cython classes::

    sage: sage_getfile(sage.rings.rational.Rational)
    '.../rational.pyx'

    sage: sage_getdoc(sage.rings.rational.Rational).lstrip()
    'A Rational number...'

    sage: sage_getsource(sage.rings.rational.Rational)
    'cdef class Rational...'

Python classes::

    sage: sage_getfile(sage.misc.attach.Attach)
    '.../attach.py'

    sage: sage_getdoc(sage.misc.attach.Attach).lstrip()
    "Attach a file to a running instance of Sage..."

    sage: sage_getsource(sage.misc.attach.Attach)
    'class Attach:...'

Python classes with no docstring, but an __init__ docstring::

    sage: class Foo:
    ...     def __init__(self):
    ...         'docstring'
    ...         pass
    ...
    sage: sage_getdoc(Foo)
    'docstring'

Test introspection of functions defined in Python and Cython files:

Cython functions::

    sage: sage_getdef(sage.rings.rational.make_rational, obj_name='mr')
    'mr(s)'

    sage: sage_getfile(sage.rings.rational.make_rational)
    '.../rational.pyx'

    sage: sage_getdoc(sage.rings.rational.make_rational).lstrip()
    "Make a rational number ...

    sage: sage_getsource(sage.rings.rational.make_rational, True)[4:]
    'make_rational(s):...'

Python functions::

    sage: sage_getdef(sagenb.misc.sageinspect.sage_getfile, obj_name='sage_getfile')
    'sage_getfile(obj)'

    sage: sage_getfile(sagenb.misc.sageinspect.sage_getfile)
    '.../sageinspect.py'

    sage: sage_getdoc(sagenb.misc.sageinspect.sage_getfile).lstrip()
    "Get the full file name associated to ``obj`` as a string..."

    sage: sage_getsource(sagenb.misc.sageinspect.sage_getfile)[4:]
    'sage_getfile(obj):...'

Unfortunately, there is no argspec extractable from builtins::

    sage: sage_getdef(''.find, 'find')
    'find( [noargspec] )'

    sage: sage_getdef(str.find, 'find')
    'find( [noargspec] )'
"""

import inspect
import os
EMBEDDED_MODE = False

def isclassinstance(obj):
    r"""
    Checks if argument is instance of non built-in class

    INPUT: ``obj`` - object

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import isclassinstance
        sage: isclassinstance(int)
        False
        sage: isclassinstance(FreeModule)
        True
        sage: isclassinstance(SteenrodAlgebra)
        True
    """
    return (hasattr(obj, '__class__') and \
            hasattr(obj.__class__, '__module__') and \
            obj.__class__.__module__ not in ('__builtin__', 'exceptions'))


SAGE_ROOT = os.environ["SAGE_ROOT"]
    
import re
# Parse strings of form "File: sage/rings/rational.pyx (starting at line 1080)"
# "\ " protects a space in re.VERBOSE mode.
__embedded_position_re = re.compile(r'''
\A                                          # anchor to the beginning of the string
File:\ (?P<FILENAME>.*?)                    # match File: then filename
\ \(starting\ at\ line\ (?P<LINENO>\d+)\)   # match line number
\n?                                         # if there is a newline, eat it
(?P<ORIGINAL>.*)                            # the original docstring is the end
\Z                                          # anchor to the end of the string
''', re.MULTILINE | re.DOTALL | re.VERBOSE)

def _extract_embedded_position(docstring):
    r"""
    If docstring has a Cython embedded position, return a tuple
    (original_docstring, filename, line).  If not, return None.

    INPUT: ``docstring`` (string)

    EXAMPLES::

       sage: from sagenb.misc.sageinspect import _extract_embedded_position
       sage: import inspect
       sage: _extract_embedded_position(inspect.getdoc(var))[1][-21:]
       'sage/calculus/var.pyx'
        
    AUTHOR:
        -- William Stein
        -- Extensions by Nick Alexander
    """
    if docstring is None:
        return None
    res = __embedded_position_re.match(docstring)
    if res is not None:
        #filename = '%s/local/lib/python/site-packages/%s' % (SAGE_ROOT, res.group('FILENAME'))
        filename = '%s/devel/sage/%s' % (SAGE_ROOT, res.group('FILENAME'))
        lineno = int(res.group('LINENO'))
        original = res.group('ORIGINAL')
        return (original, filename, lineno)
    return None

def _extract_source(lines, lineno):
    r"""
    Given a list of lines or a multiline string and a starting lineno,
    _extract_source returns [source_lines].  [source_lines] is the smallest
    indentation block starting at lineno.

    INPUT:

    - ``lines`` - string or list of strings
    - ``lineno`` - positive integer

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import _extract_source
        sage: s2 = "#hello\n\n  class f():\n    pass\n\n#goodbye"
        sage: _extract_source(s2, 3)
        ['  class f():\n', '    pass\n']
    """
    if lineno < 1:
        raise ValueError, "Line numbering starts at 1! (tried to extract line %s)" % lineno
    lineno -= 1
    
    if isinstance(lines, str):
        lines = lines.splitlines(True) # true keeps the '\n'
    if len(lines) > 0:
        # Fixes an issue with getblock
        lines[-1] += '\n'

    return inspect.getblock(lines[lineno:])

def _sage_getargspec_cython(source):
    r"""
    inspect.getargspec from source code.  That is, get the names and
    default values of a function's arguments.

    INPUT: ``source`` - a string of Cython code

    OUTPUT: a tuple (``args``, None, None, ``argdefs``), where
    ``args`` is the list of arguments and ``argdefs`` is their default
    values (as strings, so 2 is represented as '2', etc.).

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import _sage_getargspec_cython
        sage: _sage_getargspec_cython("def init(self, x=None, base=0):")
        (['self', 'x', 'base'], None, None, (None, 0))
        sage: _sage_getargspec_cython("def __init__(self, x=None, unsigned int base=0):")
        (['self', 'x', 'base'], None, None, (None, 0))

    AUTHOR:
    
    - Nick Alexander
    """
    try:
        defpos = source.find('def ')
        assert defpos > -1
        colpos = source.find(':')
        assert colpos > -1
        defsrc = source[defpos:colpos]
        
        lparpos = defsrc.find('(')
        assert lparpos > -1
        rparpos = defsrc.rfind(')')
        assert rparpos > -1

        argsrc = defsrc[lparpos+1:rparpos]

        # Now handle individual arguments
        # XXX this could break on embedded strings or embedded functions
        args = argsrc.split(',')

        # Now we need to take care of default arguments
        # XXX this could break on embedded strings or embedded functions with default arguments
        argnames = [] # argument names
        argdefs  = [] # default values
        for arg in args:
            s = arg.split('=')
            argname = s[0]

            # Cython often has type information; we split off the right most
            # identifier to discard this information
            argname = argname.split()[-1]
            # Cython often has C pointer symbols before variable names
            argname.lstrip('*')
            argnames.append(argname)
            if len(s) > 1:
                defvalue = s[1]
                # eval defvalue so we aren't just returning strings
                argdefs.append(eval(defvalue))

        if len(argdefs) > 0:
            argdefs = tuple(argdefs)
        else:
            argdefs = None

        return (argnames, None, None, argdefs)
    except:
        raise ValueError, "Could not parse cython argspec"

def sage_getfile(obj):
    r"""
    Get the full file name associated to ``obj`` as a string.

    INPUT: ``obj``, a Sage object, module, etc.

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import sage_getfile
        sage: sage_getfile(sage.rings.rational)[-23:]
        'sage/rings/rational.pyx'
        sage: sage_getfile(Sq)[-41:]
        'sage/algebras/steenrod_algebra_element.py'

    AUTHOR:
    - Nick Alexander
    """
    # We try to extract from docstrings, because Python's inspect
    # will happily report compiled .so files
    d = inspect.getdoc(obj)
    pos = _extract_embedded_position(d)
    if pos is not None:
        (_, filename, _) = pos
        return filename

    # The instance case
    if isclassinstance(obj):
        return inspect.getabsfile(obj.__class__)
    # No go? fall back to inspect.
    return inspect.getabsfile(obj)

def sage_getargspec(obj):
    r"""
    Return the names and default values of a function's arguments.

    INPUT: ``obj``, a function

    OUTPUT: A tuple of four things is returned: ``(args, varargs, varkw,
    defaults)``.  ``args`` is a list of the argument names (it may contain
    nested lists).  ``varargs`` and ``varkw`` are the names of the * and
    ** arguments or None.  ``defaults`` is an n-tuple of the default
    values of the last n arguments.

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import sage_getargspec
        sage: sage_getargspec(identity_matrix)
        (['ring', 'n', 'sparse'], None, None, (0, False))
        sage: sage_getargspec(Poset)
        (['data', 'element_labels', 'cover_relations'], None, None, (None, None, False))
        sage: sage_getargspec(factor)
        (['n', 'proof', 'int_', 'algorithm', 'verbose'],
         None,
         'kwds',
         (None, False, 'pari', 0))

    AUTHORS:
    
    - William Stein: a modified version of inspect.getargspec from the
      Python Standard Library, which was taken from IPython for use in Sage.
    - Extensions by Nick Alexander
    """
    if not callable(obj):
        raise TypeError, "obj is not a code object"
    
    if inspect.isfunction(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = obj.im_func
    elif isclassinstance(obj):
        return sage_getargspec(obj.__class__.__call__)
    elif inspect.isclass(obj):
        return sage_getargspec(obj.__call__)
    else:
        # Perhaps it is binary and defined in a Cython file
        source = sage_getsource(obj, is_binary=True)
        if source:
            return _sage_getargspec_cython(source)
        else:
            func_obj = obj

    # Otherwise we're (hopefully!) plain Python, so use inspect
    try:
        args, varargs, varkw = inspect.getargs(func_obj.func_code)
    except AttributeError:
        args, varargs, varkw = inspect.getargs(func_obj)
    try:
        defaults = func_obj.func_defaults
    except AttributeError:
        defaults = tuple([])
    return args, varargs, varkw, defaults

def sage_getdef(obj, obj_name=''):
    r"""
    Return the definition header for any callable object.

    INPUT:

    - ``obj`` - function
    - ``obj_name`` - string (optional, default '')

    ``obj_name`` is prepended to the output.

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import sage_getdef
        sage: sage_getdef(identity_matrix)
        '(ring, n=0, sparse=False)'
        sage: sage_getdef(identity_matrix, 'identity_matrix')
        'identity_matrix(ring, n=0, sparse=False)'

    Check that trac ticket #6848 has been fixed::

        sage: sage_getdef(RDF.random_element)
        '(min=-1, max=1)'

    If an exception is generated, None is returned instead and the
    exception is suppressed.
        
    AUTHORS:
    
    - William Stein
    - extensions by Nick Alexander
    """
    try:
        spec = sage_getargspec(obj)
        s = str(inspect.formatargspec(*spec))
        s = s.strip('(').strip(')').strip()
        if s[:4] == 'self':
            s = s[4:]
        s = s.lstrip(',').strip()
        # for use with typesetting the definition with the notebook:
        # sometimes s contains "*args" or "**keywds", and the
        # asterisks confuse ReST/sphinx/docutils, so escape them:
        # change * to \*, and change ** to \**.
        if EMBEDDED_MODE:
            s = s.replace('**', '\\**')  # replace ** with \**
            t = ''
            while True:  # replace * with \*
                i = s.find('*')
                if i == -1:
                    break
                elif i > 0 and s[i-1] == '\\':
                    if s[i+1] == "*":
                        t += s[:i+2]
                        s = s[i+2:]
                    else:
                        t += s[:i+1]
                        s = s[i+1:]
                    continue 
                elif i > 0 and s[i-1] == '*':
                    t += s[:i+1]
                    s = s[i+1:]
                    continue
                else:
                    t += s[:i] + '\\*'
                    s = s[i+1:]
            s = t + s
        return obj_name + '(' + s + ')'
    except (AttributeError, TypeError, ValueError):
        return '%s( [noargspec] )'%obj_name

def sage_getdoc(obj, obj_name=''):
    r"""
    Return the docstring associated to ``obj`` as a string.

    INPUT: ``obj``, a function, module, etc.: something with a docstring.

    If ``obj`` is a Cython object with an embedded position in its
    docstring, the embedded position is stripped.

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import sage_getdoc
        sage: sage_getdoc(identity_matrix)[5:39]
        'Return the `n x n` identity matrix'

    AUTHORS:
    
    - William Stein
    - extensions by Nick Alexander
    """
    if obj is None: return ''
    try:
        from sage.misc.sagedoc import format
    except ImportError:
        # Fallback
        def format(s, *args, **kwds):
            return s
        
    r = None
    try:
        r = obj._sage_doc_()
    except AttributeError:
        r = obj.__doc__

    #Check to see if there is an __init__ method, and if there
    #is, use its docstring.
    if r is None and hasattr(obj, '__init__'):
        r = obj.__init__.__doc__

    if r is None:
        return ''

    s = format(str(r), embedded=EMBEDDED_MODE)

    # If there is a Cython embedded position, it needs to be stripped
    pos = _extract_embedded_position(s)
    if pos is not None:
        s, _, _ = pos

    # Fix object naming
    if obj_name != '':
        i = obj_name.find('.')
        if i != -1:
            obj_name = obj_name[:i]
        s = s.replace('self.','%s.'%obj_name)

    return s

def sage_getsource(obj, is_binary=False):
    r"""
    Return the source code associated to obj as a string, or None.

    INPUT:

    - ``obj`` - function, etc.
    - ``is_binary`` - boolean, ignored

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import sage_getsource
        sage: sage_getsource(identity_matrix, True)[4:45]
        'identity_matrix(ring, n=0, sparse=False):'
        sage: sage_getsource(identity_matrix, False)[4:45]
        'identity_matrix(ring, n=0, sparse=False):'
    
    AUTHORS:

    - William Stein
    - extensions by Nick Alexander
    """
    #First we should check if the object has a _sage_src_
    #method.  If it does, we just return the output from
    #that.  This is useful for getting pexpect interface
    #elements to behave similar to regular Python objects
    #with respect to introspection.
    try:
        return obj._sage_src_()
    except (AttributeError, TypeError):
        pass

    t = sage_getsourcelines(obj, is_binary)
    if not t:
        return None
    (source_lines, lineno) = t
    return ''.join(source_lines)    

def sage_getsourcelines(obj, is_binary=False):
    r"""
    Return a pair ([source_lines], starting line number) of the source
    code associated to obj, or None.

    INPUT:

    - ``obj`` - function, etc.
    - ``is_binary`` - boolean, ignored

    OUTPUT: (source_lines, lineno) or None: ``source_lines`` is a list
    of strings, and ``lineno`` is an integer.

    At this time we ignore ``is_binary`` in favour of a 'do our best' strategy.

    EXAMPLES::

        sage: from sagenb.misc.sageinspect import sage_getsourcelines
        sage: sage_getsourcelines(matrix, True)[1]
        33
        sage: sage_getsourcelines(matrix, False)[0][0][4:]
        'matrix(*args, **kwds):\n'

    AUTHORS:
    
    - William Stein
    - Extensions by Nick Alexander
    """

    try:
        return obj._sage_src_lines_()
    except (AttributeError, TypeError):
        pass

    # Check if we deal with instance
    if isclassinstance(obj):
        obj=obj.__class__
        
    # If we can handle it, we do.  This is because Python's inspect will
    # happily dump binary for cython extension source code.
    d = inspect.getdoc(obj)
    pos = _extract_embedded_position(d)
    if pos is None:
        return inspect.getsourcelines(obj)

    (orig, filename, lineno) = pos
    try:
        source_lines = open(filename).readlines()
    except IOError:
        return None
    return _extract_source(source_lines, lineno), lineno



__internal_teststring = '''
import os                                  # 1
# preceding comment not include            # 2
def test1(a, b=2):                         # 3
    if a:                                  # 4
        return 1                           # 5
    return b                               # 6
# intervening comment not included         # 7
class test2():                             # 8
    pass                                   # 9
    # indented comment not included        # 10
# trailing comment not included            # 11
def test3(b,                               # 12
          a=2):                            # 13
    pass # EOF                             # 14'''

def __internal_tests():
    r"""
    Test internals of the sageinspect module.

    EXAMPLES::
    
        sage: from sagenb.misc.sageinspect import *
        sage: from sagenb.misc.sageinspect import _extract_source, _extract_embedded_position, _sage_getargspec_cython, __internal_teststring

    If docstring is None, nothing bad happens::
    
        sage: sage_getdoc(None)
        ''

        sage: sage_getsource(sage)
        "...all..."

    A cython function with default arguments (one of which is a string)::
    
        sage: sage_getdef(sage.rings.integer.Integer.factor, obj_name='factor')
        "factor(algorithm='pari', proof=True, limit=None)"

    A cython method without an embedded position can lead to surprising errors::
    
        sage: sage_getsource(sage.rings.integer.Integer.__init__, is_binary=True)
        Traceback (most recent call last):
        ...
        TypeError: arg is not a module, class, method, function, traceback, frame, or code object

        sage: sage_getdef(sage.rings.integer.Integer.__init__, obj_name='__init__')
        '__init__( [noargspec] )'

    Test _extract_source with some likely configurations, including no trailing
    newline at the end of the file::
    
        sage: s = __internal_teststring.strip()
        sage: es = lambda ls, l: ''.join(_extract_source(ls, l)).rstrip()
        
        sage: print es(s, 3)
        def test1(a, b=2):                         # 3
            if a:                                  # 4
                return 1                           # 5
            return b                               # 6

        sage: print es(s, 8)
        class test2():                             # 8
            pass                                   # 9

        sage: print es(s, 12)
        def test3(b,                               # 12
                  a=2):                            # 13
            pass # EOF                             # 14

    Test _sage_getargspec_cython with multiple default arguments and a type::
    
        sage: _sage_getargspec_cython("def init(self, x=None, base=0):")
        (['self', 'x', 'base'], None, None, (None, 0))
        sage: _sage_getargspec_cython("def __init__(self, x=None, base=0):")
        (['self', 'x', 'base'], None, None, (None, 0))
        sage: _sage_getargspec_cython("def __init__(self, x=None, unsigned int base=0):")
        (['self', 'x', 'base'], None, None, (None, 0))
    
    Test _extract_embedded_position:
    
    We cannot test the filename since it depends on SAGE_ROOT.

    Make sure things work with no trailing newline::
    
        sage: _extract_embedded_position('File: sage/rings/rational.pyx (starting at line 1080)')
        ('', '.../rational.pyx', 1080)

    And with a trailing newline::
        
        sage: s = 'File: sage/rings/rational.pyx (starting at line 1080)\n'
        sage: _extract_embedded_position(s)
        ('', '.../rational.pyx', 1080)

    And with an original docstring::

        sage: s = 'File: sage/rings/rational.pyx (starting at line 1080)\noriginal'
        sage: _extract_embedded_position(s)
        ('original', '.../rational.pyx', 1080)

    And with a complicated original docstring::

        sage: s = 'File: sage/rings/rational.pyx (starting at line 1080)\n\n\noriginal test\noriginal'
        sage: _extract_embedded_position(s)
        ('\n\noriginal test\noriginal', ..., 1080)

        sage: s = 'no embedded position'
        sage: _extract_embedded_position(s) is None
        True
    """    
