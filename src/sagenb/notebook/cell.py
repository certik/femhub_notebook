"""
A Cell.

A cell is a single input/output block. Worksheets are built out of
a list of cells.
"""

###########################################################################
#       Copyright (C) 2006 William Stein <wstein@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#                  http://www.gnu.org/licenses/
###########################################################################

import os, shutil
from cgi import escape
import re

from   sagenb.misc.misc import (word_wrap, SAGE_DOC,
                                strip_string_literals,
                                set_restrictive_permissions)

from   jsmath import math_parse

# Maximum number of characters allowed in output.  This is
# needed avoid overloading web browser.  For example, it
# should be possible to gracefully survive:
#    while True:
#       print "hello world"
# On the other hand, we don't want to loose the output of big matrices
# and numbers, so don't make this too small.

MAX_OUTPUT = 32000
MAX_OUTPUT_LINES = 120

TRACEBACK = 'Traceback (most recent call last):'

# This regexp matches "cell://blah..." in a non-greedy way (the ?), so
# we don't get several of these combined in one.
re_cell = re.compile('"cell://.*?"')
re_cell_2 = re.compile("'cell://.*?'")   # same, but with single quotes

JEDITABLE_TINYMCE = True

# Introspection.  The cache directory is a module-scope variable set
# in the first call to Cell.set_introspect_html().
import errno, hashlib, time
from sphinx.application import Sphinx
_SAGE_INTROSPECT = None

class Cell_generic:
    def is_interactive_cell(self):
        """
        Returns True if this cell contains the use of interact either as a
        function call or a decorator.
        
        EXAMPLES::
        
            sage: from sagenb.notebook.cell import Cell_generic
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: Cell_generic.is_interactive_cell(C)
            False
        """
        return False

    def delete_output(self):
        """
        Delete all output in this cell. This is not executed - it is an
        abstract function that must be overwritten in a derived class.
        
        EXAMPLES: This function just raises a NotImplementedError, since it
        most be defined in derived class.
        
        ::
        
            sage: C = sagenb.notebook.cell.Cell_generic()
            sage: C.delete_output()
            Traceback (most recent call last):
            ...
            NotImplementedError
        """
        raise NotImplementedError

    def html_new_cell_before(self):
        """
        Returns the HTML code for inserting a new cell before self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: print C.html_new_cell_before()
            <div class="insert_new_cell" id="insert_new_cell_before0">...
        """
        return """<div class="insert_new_cell" id="insert_new_cell_before%(id)s">
                 </div>
<script type="text/javascript">
$("#insert_new_cell_before%(id)s").plainclick(function(e) {insert_new_cell_before(%(id)s);});
$("#insert_new_cell_before%(id)s").shiftclick(function(e) {insert_new_text_cell_before(%(id)s);});
</script>"""%{'id': self.id()}

    def html_new_cell_after(self):
        """
        Returns the HTML code for inserting a new cell after self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: print C.html_new_cell_after()
            <div class="insert_new_cell" id="insert_new_cell_after0">...
        """
        return """<div class="insert_new_cell" id="insert_new_cell_after%(id)s">
                 </div>
<script type="text/javascript">
$("#insert_new_cell_after%(id)s").plainclick(function(e) {insert_new_cell_after(%(id)s);});
$("#insert_new_cell_after%(id)s").shiftclick(function(e) {insert_new_text_cell_after(%(id)s);});
</script>"""%{'id': self.id()}


class TextCell(Cell_generic):
    def __init__(self, id, text, worksheet):
        """
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C == loads(dumps(C))
            True
        """
        self.__id = int(id)
        self.__text = text
        self.__worksheet = worksheet

    def __repr__(self):
        """
        String representation of this text cell.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.__repr__()
            'TextCell 0: 2+3'
        """
        return "TextCell %s: %s"%(self.__id, self.__text)

    def delete_output(self):
        """
        Delete all output in this cell. This does nothing since text cells
        have no output.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C
            TextCell 0: 2+3
            sage: C.delete_output()
            sage: C
            TextCell 0: 2+3
        """
        pass # nothing to do -- text cells have no output

    def set_input_text(self, input_text):
        """
        Sets the input text of self to be input_text.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C
            TextCell 0: 2+3
            sage: C.set_input_text("3+2")
            sage: C
            TextCell 0: 3+2
        """
        self.__text = input_text
        
    def set_worksheet(self, worksheet, id=None):
        """
        Sets the worksheet object of self to be worksheet and optionally
        changes the id of self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: W = "worksheet object"
            sage: C.set_worksheet(W)
            sage: C.worksheet()
            'worksheet object'
            sage: C.set_worksheet(None, id=2)
            sage: C.id()
            2
        """
        self.__worksheet = worksheet
        if id is not None:
            self.__id = id

    def worksheet(self):
        """
        Returns the worksheet object associated to self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', 'worksheet object')
            sage: C.worksheet()
            'worksheet object'
        """
        return self.__worksheet

    def html(self, ncols=0, do_print=False, do_math_parse=True, editing=False):
        """
        Returns an HTML version of self as a string.

        INPUT:
           
        - ``do_math_parse`` - bool (default: True)
          If True, call math_parse (defined in cell.py)
          on the html. 

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.html()
            '<div class="text_cell" id="cell_text_0">2+3...'
            sage: C.set_input_text("$2+3$")
            sage: C.html(do_math_parse=True)
            '<div class="text_cell" id="cell_text_0"><span class="math">2+3</span>...'
        """
        s = '<span id="cell_outer_%s">'%self.__id

        if not do_print:
            s += self.html_new_cell_before()

        s += """<div class="text_cell" id="cell_text_%s">%s</div>"""%(
            self.__id, 
            self.html_inner(ncols=ncols, do_print=do_print, do_math_parse=do_math_parse, editing=editing))

        if JEDITABLE_TINYMCE and hasattr(self.worksheet(),'is_published') and not self.worksheet().is_published() and not self.worksheet().docbrowser() and not do_print:

            try:
                z = ((self.__text).decode('utf-8')).encode('ascii', 'xmlcharrefreplace')
            except Exception, msg:
                print msg
                # better to get the worksheet at all than to get a blank screen and nothing.
                z = self.__text
            
            s += """<script>$("#cell_text_%s").unbind('dblclick').editable(function(value,settings) {
evaluate_text_cell_input(%s,value,settings);
return(value);
}, { 
      tooltip   : "",
      placeholder : "",
//      type   : 'textarea',
      type   : 'mce',
      onblur : 'ignore',
      select : false,
      submit : 'Save changes',
      cancel : 'Cancel changes',
      event  : "dblclick",
      style  : "inherit",
      data   : %r
  });
</script>"""%(self.__id,self.__id, z)


        if editing and not do_print:
            s += """<script>$("#cell_text_%s").trigger('dblclick');</script>"""%self.__id

        s += '</span>'
        return s

    def html_inner(self,ncols=0, do_print=False, do_math_parse=True, editing=False):
        """
        Returns an HTML version of the content of self as a string.

        INPUT:
        
        - ``do_math_parse`` - bool (default: True)
          If True, call math_parse (defined in cell.py)
          on the html. 

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.html_inner()
            '2+3...'
            sage: C.set_input_text("$2+3$")
            sage: C.html_inner(do_math_parse=True)
            '<span class="math">2+3</span>...'
        """
        t = self.__text
        if do_math_parse:
            # Do dollar sign math parsing
            try:
                t = math_parse(t)
            except Exception, msg:
                # Since there is no guarantee the user's input/output
                # is in any way valid, and we don't want to stop the
                # server process (which is doing this work).
                pass
        s = """%s"""%t
        return s
        

    def plain_text(self, prompts=False):
        """
        Returns a plain text version of self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.plain_text()
            '2+3'
        """
        return self.__text

    def edit_text(self):
        """
        Returns the text to be displayed in the Edit window.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.edit_text()
            '2+3'
        """
        return self.__text

    def id(self):
        """
        Returns self's ID.

        OUTPUT:

        - int -- self's ID.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.id()
            0
        """
        return self.__id

    def is_auto_cell(self):
        """
        Returns True if self is automatically evaluated.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.is_auto_cell()
            False
        """
        return False

    def __cmp__(self, right):
        """
        Compares cells by ID.
        
        EXAMPLES::
        
            sage: C1 = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C2 = sagenb.notebook.cell.TextCell(0, '3+2', None)
            sage: C3 = sagenb.notebook.cell.TextCell(1, '2+3', None)
            sage: C1 == C1
            True
            sage: C1 == C2
            True
            sage: C1 == C3
            False
        """
        return cmp(self.id(), right.id())

    def set_cell_output_type(self, typ='wrap'):
        """
        This does nothing for TextCells.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.TextCell(0, '2+3', None)
            sage: C.set_cell_output_type("wrap")
        """
        pass # ignored
                   

class Cell(Cell_generic):
    def __init__(self, id, input, out, worksheet):
        """
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C == loads(dumps(C))
            True
        """
        self.__id    = int(id)
        self.__out   = str(out).replace('\r','')
        self.__worksheet = worksheet
        self.__interrupted = False
        self.__completions = False
        self.has_new_output = False
        self.__no_output_cell = False
        self.__asap = False
        self.__version = -1
        self.set_input_text(str(input).replace('\r',''))
        
    def set_asap(self, asap):
        """
        Set whether this cell is evaluated as soon as possible.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.is_asap()
            False
            sage: C.set_asap(True)
            sage: C.is_asap()
            True
        """
        self.__asap = bool(asap)

    def is_asap(self):
        """
        Return True if this is an asap cell, i.e., evaluation of it is done
        as soon as possible.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.is_asap()
            False
            sage: C.set_asap(True)
            sage: C.is_asap()
            True
        """
        try:
            return self.__asap
        except AttributeError:
            self.__asap = False
            return self.__asap

    def delete_output(self):
        """
        Delete all output in this cell.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None); C
            Cell 0; in=2+3, out=5
            sage: C.delete_output()
            sage: C
            Cell 0; in=2+3, out=
        """
        self.__out = ''
        self.__out_html = ''
        self.__evaluated = False

    def evaluated(self):
        r"""
        Return True if this cell has been successfully evaluated in a
        currently running session.
        
        This is not about whether the output of the cell is valid given the
        input.
        
        OUTPUT:
        
        
        -  ``bool`` - whether or not this cell has been
           evaluated in this session
        
        
        EXAMPLES: We create a worksheet with a cell that has wrong output::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: W.edit_save('Sage\n{{{\n2+3\n///\n20\n}}}')
            sage: C = W.cell_list()[0]
            sage: C
            Cell 0; in=2+3, out=
            20
        
        We re-evaluate that input cell::
        
            sage: C.evaluate()
            sage: W.check_comp(wait=9999)
            ('d', Cell 0; in=2+3, out=
            5
            )
        
        Now the output is right::
        
            sage: C
            Cell 0; in=2+3, out=
            5
        
        And the cell is considered to have been evaluated.
        
        ::
        
            sage: C.evaluated()
            True
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        # Cells are never considered evaluated in a new session.
        if not self.worksheet().compute_process_has_been_started():
            self.__evaluated = False
            return False

        # Figure out if the worksheet is using the same sage
        # session as this cell.  (I'm not sure when this would
        # be False.)
        same_session = self.worksheet().sage() is self.sage()
        try:
            # Always not evaluated if sessions are different.
            if not same_session:
                self.__evaluated = False
                return False
            return self.__evaluated
        except AttributeError:
            # Default assumption is that cell has not been evaluated. 
            self.__evaluated = False
            return False

    def set_no_output(self, no_output):
        """
        Sets whether or not this is an no_output cell, i.e., a cell for
        which we don't care at all about the output.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.is_no_output()
            False
            sage: C.set_no_output(True)
            sage: C.is_no_output()
            True
        """
        self.__no_output = bool(no_output)

    def is_no_output(self):
        """
        Return True if this is an no_output cell, i.e., a cell for which
        we don't care at all about the output.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.is_no_output()
            False
            sage: C.set_no_output(True)
            sage: C.is_no_output()
            True
        """
        try:
            return self.__no_output
        except AttributeError:
            self.__no_output = False
            return self.__no_output

    def set_cell_output_type(self, typ='wrap'):
        """
        Sets the cell output type.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.cell_output_type()
            'wrap'
            sage: C.set_cell_output_type('nowrap')
            sage: C.cell_output_type()
            'nowrap'
        """
        self.__type = typ

    def cell_output_type(self):
        """
        Returns the cell output type.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.cell_output_type()
            'wrap'
            sage: C.set_cell_output_type('nowrap')
            sage: C.cell_output_type()
            'nowrap'
        """
        try:
            return self.__type
        except AttributeError:
            self.__type = 'wrap'
            return self.__type

    def set_worksheet(self, worksheet, id=None):
        """
        Sets the worksheet object of self to be worksheet and optionally
        changes the id of self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: W = "worksheet object"
            sage: C.set_worksheet(W)
            sage: C.worksheet()
            'worksheet object'
            sage: C.set_worksheet(None, id=2)
            sage: C.id()
            2
        """
        self.__worksheet = worksheet
        if id is not None:
            self.set_id(id)

    def worksheet(self):
        """
        Returns the worksheet object associated to self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', 'worksheet object')
            sage: C.worksheet()
            'worksheet object'
        """
        return self.__worksheet

    def update_html_output(self, output=''):
        """
        Update the list of files with html-style links or embeddings for
        this cell.
        
        For interactive cells the html output section is always empty,
        mainly because there is no good way to distinguish content (e.g.,
        images in the current directory) that goes into the interactive
        template and content that would go here.

        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'plot(sin(x),0,5)', '', W)
            sage: C.evaluate()
            sage: W.check_comp(wait=9999)
            ('d', Cell 0; in=plot(sin(x),0,5), out=
            <html><font color='black'><img src='cell://sage0.png'></font></html>
            <BLANKLINE>
            )
            sage: C.update_html_output()
            sage: C.output_html()
            '<img src="/home/sage/0/cells/0/sage0.png?...">'
        """
        if self.is_interactive_cell():
            self.__out_html = ""
        else:
            self.__out_html = self.files_html(output)

    def id(self):
        """
        Returns the id of self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.id()
            0
        """
        return self.__id

    def set_id(self, id):
        """
        Sets the id of self to id.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.set_id(2)
            sage: C.id()
            2
        """
        self.__id = int(id)

    def worksheet(self):
        """
        Returns the workseet associated to self.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.worksheet() is W
            True
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return self.__worksheet

    def worksheet_filename(self):
        """
        Returns the filename of the worksheet associated to self.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.worksheet_filename()
            'sage/0'
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return self.__worksheet.filename()


    def notebook(self):
        """
        Returns the notebook object associated to self.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.notebook() is nb
            True
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return self.__worksheet.notebook()

    def directory(self):
        """
        Returns the directory associated to self. If the directory doesn't
        already exist, then this method creates it.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.directory()
            '.../worksheets/sage/0/cells/0'
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        dir = self._directory_name()
        if not os.path.exists(dir):
            os.makedirs(dir)
        set_restrictive_permissions(dir)
        return dir

    def _directory_name(self):
        """
        Returns a string of the directory associated to self.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C._directory_name()
            '.../worksheets/sage/0/cells/0'
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return os.path.join(self.__worksheet.directory(), 'cells', str(self.id()))


    def __cmp__(self, right):
        """
        Compares cells by their IDs.
        
        EXAMPLES::
        
            sage: C1 = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C2 = sagenb.notebook.cell.Cell(0, '3+2', '5', None)
            sage: C3 = sagenb.notebook.cell.Cell(1, '2+3', '5', None)
            sage: C1 == C1
            True
            sage: C1 == C2
            True
            sage: C1 == C3
            False
        """
        return cmp(self.id(), right.id())

    def __repr__(self):
        """
        Returns a string representation of self.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None); C
            Cell 0; in=2+3, out=5
        """
        return 'Cell %s; in=%s, out=%s'%(self.__id, self.__in, self.__out)

    def word_wrap_cols(self):
        """
        Returns the number of columns for word wrapping. This defaults to
        70, but the default setting for a notebook is 72.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.word_wrap_cols()
            70
        
        ::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.word_wrap_cols()
            72
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        try:
            return self.notebook().conf()['word_wrap_cols']
        except AttributeError:
            return 70
        
    def plain_text(self, ncols=0, prompts=True, max_out=None):
        r"""
        Returns the plain text version of self.

        EXAMPLES::

            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: len(C.plain_text())
            11
        """
        if ncols == 0:
            ncols = self.word_wrap_cols()
        s = ''

        input_lines = self.__in
        pr = 'sage: '
            
        if prompts:
            input_lines = input_lines.splitlines()
            has_prompt = False
            if pr == 'sage: ':
                for v in input_lines:
                    w = v.lstrip()
                    if w[:5] == 'sage:' or w[:3] == '>>>' or w[:3] == '...':
                        has_prompt = True
                        break
            else:
                # discard first line since it sets the prompt
                input_lines = input_lines[1:]

            if has_prompt:
                s += '\n'.join(input_lines) + '\n'
            else:
                in_loop = False
                for v in input_lines:
                    if len(v) == 0:
                        pass
                    elif len(v.lstrip()) != len(v):  # starts with white space
                        in_loop = True
                        s += '...   ' + v + '\n'
                    elif v[:5] == 'else:':
                        in_loop = True
                        s += '...   ' + v + '\n'
                    else:
                        if in_loop:
                            s += '...\n'
                            in_loop = False
                        s += pr + v + '\n'
        else:
            s += self.__in

        if prompts:
            msg = TRACEBACK
            if self.__out.strip().startswith(msg):
                v = self.__out.strip().splitlines()
                w = [msg, '...']
                for i in range(1,len(v)):
                    if not (len(v[i]) > 0 and v[i][0] == ' '):
                        w = w + v[i:]
                        break
                out = '\n'.join(w)
            else:
                out = self.output_text(ncols, raw=True, html=False)
        else:
            out = self.output_text(ncols, raw=True, html=False, allow_interact=False)
            out = '///\n' + out.strip()

        if not max_out is None and len(out) > max_out:
            out = out[:max_out] + '...'

        # Get rid of spurious carriage returns 
        s = s.strip('\n')
        out = out.strip('\n').strip('\r').strip('\r\n')
        s = s + '\n' + out

        if not prompts:
            s = s.rstrip('\n')
        return s
    
    def edit_text(self, ncols=0, prompts=False, max_out=None):
        r"""
        Returns the text displayed in the Edit window.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.edit_text()
            '{{{id=0|\n2+3\n///\n5\n}}}'
        """
        s = self.plain_text(ncols, prompts, max_out)
        return '{{{id=%s|\n%s\n}}}'%(self.id(), s)

    def is_last(self):
        """
        Returns True if self is the last cell in the worksheet.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "2^2"); C
            Cell 1; in=2^2, out=
            sage: C.is_last()
            True
            sage: C = W.get_cell_with_id(0)
            sage: C.is_last()
            False
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return self.__worksheet.cell_list()[-1] == self

    def next_id(self):
        """
        Returns the id of the next cell in the worksheet associated to
        self. If self is not in the worksheet or self is the last cell in
        the cell_list, then the id of the first cell is returned.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "2^2")
            sage: C = W.get_cell_with_id(0)
            sage: C.next_id()
            1
            sage: C = W.get_cell_with_id(1)
            sage: C.next_id()
            0
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        L = self.__worksheet.cell_list()
        try:
            k = L.index(self)
        except ValueError:
            print "Warning -- cell %s no longer exists"%self.id()
            return L[0].id()
        try:
            return L[k+1].id()
        except IndexError:
            return L[0].id()

    def interrupt(self):
        """
        Record that the calculation running in this cell was interrupted.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "2^2")
            sage: C.interrupt()
            sage: C.interrupted()
            True
            sage: C.evaluated()
            False
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        self.__interrupted = True
        self.__evaluated = False

    def interrupted(self):
        """
        Returns True if the evaluation of this cell has been interrupted.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "2^2")
            sage: C.interrupt()
            sage: C.interrupted()
            True
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return self.__interrupted

    def computing(self):
        """
        Returns True if self is in its worksheet's queue.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "2^2")
            sage: C.computing()
            False
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        return self in self.__worksheet.queue()

    def is_interactive_cell(self):
        r"""
        Return True if this cell contains the use of interact either as a
        function call or a decorator.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "@interact\ndef f(a=slider(0,10,1,5):\n    print a^2")
            sage: C.is_interactive_cell()
            True
            sage: C = W.new_cell_after(C.id(), "2+2")
            sage: C.is_interactive_cell()
            False
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        # Do *not* cache
        s = strip_string_literals(self.input_text())
        if len(s) == 0: return False
        s = s[0]
        return bool(re.search('(?<!\w)interact\s*\(.*\).*', s) or re.search('\s*@\s*interact\s*\n', s))

    def is_interacting(self):
        r"""
        Returns True if this cell is currently interacting with the user.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "@interact\ndef f(a=slider(0,10,1,5):\n    print a^2")
            sage: C.is_interacting()
            False
        """
        return hasattr(self, 'interact')

    def stop_interacting(self):
        """
        Stops interaction with user.

        TODO: Add doctests for :meth:`stop_interacting`.            
        """
        if self.is_interacting():
            del self.interact

    def set_input_text(self, input):
        """
        Sets the input text of self to be the string input.
        
        TODO: Add doctests for the code dealing with interact.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = W.new_cell_after(0, "2^2")
            sage: C.evaluate()
            sage: W.check_comp(wait=9999)
            ('d', Cell 1; in=2^2, out=
            4
            )
            sage: C.version()
            0
        
        ::
        
            sage: C.set_input_text('3+3')
            sage: C.input_text()
            '3+3'
            sage: C.evaluated()
            False
            sage: C.version()
            1
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        # Stuff to deal with interact
        if input.startswith('%__sage_interact__'):
            self.interact = input[len('%__sage_interact__')+1:]
            self.__version = self.version() + 1
            return
        elif self.is_interacting():
            try:
                del self.interact
                del self._interact_output
            except AttributeError:
                pass

        # We have updated the input text so the cell can't have 
        # been evaluated. 
        self.__evaluated = False
        self.__version = self.version() + 1
        self.__in = input
        if hasattr(self, '_html_cache'):
            del self._html_cache

        #Run get the input text with all of the percent
        #directives parsed
        self._cleaned_input = self.parse_percent_directives()
        
    def input_text(self):
        """
        Returns self's input text.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.input_text()
            '2+3'
        """
        return self.__in

    def cleaned_input_text(self):
        r"""
        Returns the input text with all of the percent directives
        removed.  If the cell is interacting, then the interacting
        text is returned.

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '%hide\n%maxima\n2+3', '5', None)
            sage: C.cleaned_input_text()
            '2+3'

        """
        if self.is_interacting():
            return self.interact
        else:
            return self._cleaned_input

    def parse_percent_directives(self):
        r"""
        Returns a string which consists of the input text of this cell
        with the percent directives at the top removed.  As it's doing
        this, it computes a list of all the directives and which
        system (if any) the cell should be run under.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '%hide\n%maxima\n2+3', '5', None)
            sage: C.parse_percent_directives()
            '2+3'
            sage: C.percent_directives()
            ['hide', 'maxima']
        
        """
        self._system = None
        text = self.input_text().splitlines()
        directives = []
        i = 0
        for i, line in enumerate(text):
            line = line.strip()
            if not line.startswith('%'):
                #Handle the #auto case here for now
                if line == "#auto":
                    pass
                else:
                    break
            elif line in ['%auto', '%hide', '%hideall', '%save_server', '%time', '%timeit']:
                # We do not consider any of the above percent
                # directives as specifying a system.
                pass
            else:
                self._system = line[1:]
                
            directives.append(line[1:])
            
        self._percent_directives = directives
        return "\n".join(text[i:]).strip()
            
    def percent_directives(self):
        r"""
        Returns a list of all the percent directives that appear
        in this cell.

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '%hide\n%maxima\n2+3', '5', None)
            sage: C.percent_directives()
            ['hide', 'maxima']
        
        """
        return self._percent_directives

    def system(self):
        r"""
        Returns the system used to evaluate this cell. The system
        is specified by a percent directive like '%maxima' at
        the top of a cell.

        If no system is explicitly specified, then None is returned
        which tells the notebook to evaluate the cell using the
        worksheet's default system.

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '%maxima\n2+3', '5', None)
            sage: C.system()
            'maxima'
            sage: prefixes = ['%hide', '%time', '']
            sage: cells = [sagenb.notebook.cell.Cell(0, '%s\n2+3'%prefix, '5', None) for prefix in prefixes]
            sage: [(C, C.system()) for C in cells if C.system() is not None]
            []
        """
        return self._system


    def is_auto_cell(self):
        r"""
        Returns True if self is an auto cell.
        
        An auto cell is a cell that is automatically evaluated when the
        worksheet starts up.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.is_auto_cell()
            False
            sage: C = sagenb.notebook.cell.Cell(0, '#auto\n2+3', '5', None)
            sage: C.is_auto_cell()
            True
        """
        return 'auto' in self.percent_directives()

    def changed_input_text(self):
        """
        Returns the changed input text for the cell. If there was any
        changed input text, then it is reset to " before this method
        returns.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.changed_input_text()
            ''
            sage: C.set_changed_input_text('3+3')
            sage: C.input_text()
            '3+3'
            sage: C.changed_input_text()
            '3+3'
            sage: C.changed_input_text()
            ''
            sage: C.version()
            0
        """
        try:
            t = self.__changed_input
            del self.__changed_input
            return t
        except AttributeError:
            return ''

    def set_changed_input_text(self, new_text):
        """
        Note that this does not update the version of the cell. This is
        typically used for things like tab completion.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.set_changed_input_text('3+3')
            sage: C.input_text()
            '3+3'
            sage: C.changed_input_text()
            '3+3'
        """
        self.__changed_input = new_text
        self.__in = new_text

    def set_output_text(self, output, html, sage=None):
        r"""
        Sets the output text for self.

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: len(C.plain_text())
            11
            sage: C.set_output_text('10', '10')
            sage: len(C.plain_text())
            12
        """
        if output.count('<?__SAGE__TEXT>') > 1:
            html = '<h3><font color="red">WARNING: multiple @interacts in one cell disabled (not yet implemented).</font></h3>'
            output = ''

        # In interacting mode, we just save the computed output
        # (do not overwrite). 
        if self.is_interacting():
            self._interact_output = (output, html)
            return
        
        if hasattr(self, '_html_cache'):
            del self._html_cache

        output = output.replace('\r','')
        # We do not truncate if "notruncate" or "Output truncated!" already
        # appears in the output.  This notruncate tag is used right now
        # in sage.server.support.help.
        if 'notruncate' not in output and 'Output truncated!' not in output and \
               (len(output) > MAX_OUTPUT or output.count('\n') > MAX_OUTPUT_LINES):
            url = ""
            if not self.computing():
                file = os.path.join(self.directory(), "full_output.txt")
                open(file,"w").write(output)
                url = "<a target='_new' href='%s/full_output.txt' class='file_link'>full_output.txt</a>"%(
                    self.url_to_self())
                html+="<br>" + url
            lines = output.splitlines()
            start = '\n'.join(lines[:MAX_OUTPUT_LINES/2])[:MAX_OUTPUT/2]
            end = '\n'.join(lines[-MAX_OUTPUT_LINES/2:])[-MAX_OUTPUT/2:]
            warning = 'WARNING: Output truncated!  '
            if url:
                # make the link to the full output appear at the top too.
                warning += '\n<html>%s</html>\n'%url
            output = warning + '\n\n' + start + '\n\n...\n\n' + end
        self.__out = output
        if not self.is_interactive_cell():
            self.__out_html = html
        self.__sage = sage

    def sage(self):
        """
        TODO: Figure out what exactly this does.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.sage() is None
            True
        """
        try:
            return self.__sage
        except AttributeError:
            return None

    def output_html(self):
        """
        Returns the HTML for self's output.

        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.output_html()
            ''
            sage: C.set_output_text('5', '<strong>5</strong>')
            sage: C.output_html()
            '<strong>5</strong>'
        """
        try:
            return self.__out_html
        except AttributeError:
            self.__out_html = ''
            return ''
    
    def process_cell_urls(self, urls):
        """
        Processes URLs of the form ``'cell://.*?'`` by replacing the
        protocol with the path to self and appending self's version
        number.

        INPUT:

        - ``urls`` - a string

        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.process_cell_urls('"cell://foobar"')
            '/home/sage/0/cells/0/foobar?0"'
        """
        end = '?%d"'%self.version()
        begin = self.url_to_self()
        for s in re_cell.findall(urls) + re_cell_2.findall(urls):
            urls = urls.replace(s,begin + s[7:-1] + end)
        return urls

    def output_text(self, ncols=0, html=True, raw=False, allow_interact=True):
        """
        Returns the text for self's output.

        INPUT:

        - ``ncols`` -- maximum number of columns
            
        - ``html`` -- boolean stating whether to output HTML
            
        - ``raw`` -- boolean stating whether to output raw text
          (takes precedence over HTML)

        - ``allow_interact`` -- boolean stating whether to allow interaction

        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.output_text()
            '<pre class="shrunk">5</pre>'
            sage: C.output_text(html=False)
            '<pre class="shrunk">5</pre>'
            sage: C.output_text(raw=True)
            '5'
        """
        if allow_interact and hasattr(self, '_interact_output'):
            # Get the input template
            z = self.output_text(ncols, html, raw, allow_interact=False)
            if not '<?__SAGE__TEXT>' in z or not '<?__SAGE__HTML>' in z:
                return z
            if ncols:
                # Get the output template
                try:
                    # Fill in the output template
                    output,html = self._interact_output
                    output = self.parse_html(output, ncols)
                    z = z.replace('<?__SAGE__TEXT>', output)
                    z = z.replace('<?__SAGE__HTML>', html)
                    return z
                except (ValueError, AttributeError), msg:
                    print msg
                    pass
            else:
                # Get rid of the interact div to avoid updating the wrong output location
                # during interact.
                return ''

        is_interact = self.is_interactive_cell()
        if is_interact and ncols == 0:
            if 'Traceback (most recent call last)' in self.__out:
                s = self.__out.replace('cell-interact','')
                is_interact=False
            else:
                return '<h2>Click to the left again to hide and once more to show the dynamic interactive window</h2>'
        else:
            s = self.__out
        
        if raw:
            return s

        if html:
            s = self.parse_html(s, ncols)

        if not is_interact and not self.is_html() and len(s.strip()) > 0:
            s = '<pre class="shrunk">' + s.strip('\n') + '</pre>'
            
        return s.strip('\n')

    def parse_html(self, s, ncols):
        r"""
        Parse HTML for output.

        INPUT:
       
        - ``s`` -- the input string containing HTML
            
        - ``ncols`` -- maximum number of columns
            
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.parse_html('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">\n<html><head></head><body>Test</body></html>', 80)
            '&lt;!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0...Test</body>'
        """
        def format(x):
            return word_wrap(escape(x), ncols)

        def format_html(x):
            return self.process_cell_urls(x)

        # if there is an error in the output,
        # specially format it.
        if not self.is_interactive_cell():
            s = format_exception(format_html(s), ncols)

        # Everything not wrapped in <html> ... </html> should be
        # escaped and word wrapped.
        t = ''
        while len(s) > 0:
            i = s.find('<html>')
            if i == -1:
                t += format(s)
                break
            j = s.find('</html>')
            if j == -1:
                t += format(s[:i])
                break
            t += format(s[:i]) + format_html(s[i+6:j])
            s = s[j+7:]
        t = t.replace('</html>','')

        # Get rid of the <script> tags, since we do not want them to
        # be evaluated twice.  They are only evaluated in the wrapped
        # version of the output.
        if ncols == 0:
            while True:
                i = t.lower().find('<script>')
                if i == -1: break
                j = t[i:].lower().find('</script>')
                if j == -1: break
                t = t[:i] + t[i+j+len('</script>'):]
                
        return t
        

    def has_output(self):
        """
        Returns True if there is output for this cell.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.has_output()
            True
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '', None)
            sage: C.has_output()
            False
        """
        return len(self.__out.strip()) > 0

    def is_html(self):
        r"""
        Returns True if this is an HTML cell. An HTML cell whose system is
        'html' and is typically specified by ``%html``.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, "%html\nTest HTML", None, None)
            sage: C.system()
            'html'
            sage: C.is_html()
            True
            sage: C = sagenb.notebook.cell.Cell(0, "Test HTML", None, None)
            sage: C.is_html()
            False

        """
        try:
            return self.__is_html
        except AttributeError:
            return self.system() == 'html'

    def set_is_html(self, v):
        """
        Sets whether or not this cell is an HTML cell.
        
        This is called by check_for_system_switching in worksheet.py.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.is_html()
            False
            sage: C.set_is_html(True)
            sage: C.is_html()
            True
        """
        self.__is_html = v

    #################
    # Introspection #
    #################
    def set_introspect_html(self, html, completing=False, verbose=False, raw=False):
        """
        If ``verbose`` is True, print verbose output about notebook
        introspection to the command-line.  However, the argument
        ``verbose`` is not easily accessible now -- if you need to
        debug, you have to edit this file, changing its value to True,
        and run 'sage -b'.

        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'sage?', '', W)
            sage: C.introspect()
            False
            sage: C.evaluate(username='sage')
            sage: W.check_comp(9999)
            ('d', Cell 0; in=sage?, out=)
            sage: C.set_introspect_html('foobar')
            sage: C.introspect_html()
            '<div class="docstring"><pre>foobar</pre></div>'
            sage: C.set_introspect_html('`foobar`')
            sage: C.introspect_html()
            '<div class="docstring">...<span class="math">foobar</span>...</div>'
        """
        self.__introspect_html = html
        self.introspection_status = 'done'
        
    def get_introspection_status(self):
        try:
            return self.__introspection_status
        except AttributeError:
            return None

    def set_introspection_status(self, value):
        self.__introspection_status = value

    introspection_status = property(get_introspection_status, set_introspection_status)
        
        
    def introspect_html(self):
        """
        Returns HTML for introspection.

        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'sage?', '', W)
            sage: C.introspect()
            False
            sage: C.evaluate(username='sage')
            sage: W.check_comp(9999)
            ('d', Cell 0; in=sage?, out=)
            sage: C.introspect_html()
            u'<div class="docstring">...</pre></div>'
        """
        if not self.introspect():
            return ''
        try:
            return self.__introspect_html
        except AttributeError:
            self.__introspect_html = ''
            return ''

    def introspect(self):
        """
        Returns self's introspection text.
        
        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'sage?', '', W)
            sage: C.introspect()
            False
            sage: C.evaluate(username='sage')
            sage: W.check_comp(9999)
            ('d', Cell 0; in=sage?, out=)
            sage: C.introspect()
            ['sage?', '']
        """
        try:
            return self.__introspect
        except AttributeError:
            return False

    def unset_introspect(self):
        """
        Unsets self's introspection text.
        
        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'sage?', '', W)
            sage: C.introspect()
            False
            sage: C.evaluate(username='sage')
            sage: W.check_comp(9999)
            ('d', Cell 0; in=sage?, out=)
            sage: C.introspect()
            ['sage?', '']
            sage: C.unset_introspect()
            sage: C.introspect()
            False
        """
        self.__introspect = False

    def set_introspect(self, before_prompt, after_prompt):
        """
        Set self's introspection text.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.set_introspect("a", "b")
            sage: C.introspect()
            ['a', 'b']
        """
        self.__introspect = [before_prompt, after_prompt]

    def evaluate(self, introspect=False, time=None, username=None):
        r"""
        INPUT:
        
        
        -  ``username`` - name of user doing the evaluation
        
        -  ``time`` - if True return time computation takes
        
        -  ``introspect`` - either False or a pair
           [before_cursor, after_cursor] of strings.
        
        
        EXAMPLES:

        We create a notebook, worksheet, and cell and evaluate it
        in order to compute `3^5`::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: W.edit_save('Sage\n{{{\n3^5\n}}}')
            sage: C = W.cell_list()[0]; C
            Cell 0; in=3^5, out=
            sage: C.evaluate(username='sage')
            sage: W.check_comp(wait=9999)
            ('d', Cell 0; in=3^5, out=
            243
            )
            sage: C
            Cell 0; in=3^5, out=
            243        
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        self.__interrupted = False
        self.__evaluated = True
        if time is not None:
            self.__time = time
        self.__introspect = introspect
        self.__worksheet.enqueue(self, username=username)
        self.__type = 'wrap'
        dir = self.directory()
        for D in os.listdir(dir):
            F = os.path.join(dir, D)
            try:
                os.unlink(F)
            except OSError:
                try:
                    shutil.rmtree(F)
                except:
                    pass
                
    def version(self):
        """
        Returns the version number of this cell.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.version()
            0
            sage: C.set_input_text('2+3')
            sage: C.version()
            1
        """
        try:
            return self.__version
        except AttributeError:
            self.__version = 0
            return self.__version

    def time(self):
        r"""
        Returns True if the time it takes to evaluate this cell should be
        printed.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: C.time()
            False
            sage: C = sagenb.notebook.cell.Cell(0, '%time\n2+3', '5', None)
            sage: C.time()
            True
        """
        return ('time' in self.percent_directives() or
                'timeit' in self.percent_directives() or
                getattr(self, '__time', False))

    def doc_html(self, wrap=None, div_wrap=True, do_print=False):
        """
        Modified version of ``self.html`` for the doc browser.
        This is a hack and needs to be improved. The problem is how to get
        the documentation html to display nicely between the example cells.
        The type setting (jsMath formatting) needs attention too.

        TODO: Remove this hack (:meth:`doc_html`)
        """
        self.evaluate()
        if wrap is None:
            wrap = self.notebook().conf()['word_wrap_cols']
        evaluated = self.evaluated()
        if evaluated:
            cls = 'cell_evaluated'
        else:
            cls = 'cell_not_evaluated'

        html_in  = self.html_in(do_print=do_print)
        introspect = "<div id='introspect_div_%s' class='introspection'></div>"%self.id()
        #html_out = self.html_out(wrap, do_print=do_print)
        html_out = self.html()
        s = html_out
        if div_wrap:
            s = '\n\n<div id="cell_outer_%s" class="cell_visible"><div id="cell_%s" class="%s">'%(self.id(), self.id(), cls) + s + '</div></div>'
        return s
   
    def html(self, wrap=None, div_wrap=True, do_print=False):
        r"""
        Returns the HTML for self.

        INPUT:

        - ``wrap`` - None or an integer stating column position to wrap lines. Defaults to
          configuration if not given.

        - ``div_wrap`` - a boolean stating whether to wrap ``div``.

        - ``do_print`` - a boolean stating whether the HTML is for
          print or not.

        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.html()
            '\n\n<div id="cell_outer_0" cl...</div>'
        """
        if do_print:
            wrap = 68
            div_wrap = 68
        key = (wrap,div_wrap,do_print)

        if wrap is None:
            wrap = self.notebook().conf()['word_wrap_cols']
        evaluated = self.evaluated()
        if evaluated or do_print:
            cls = 'cell_evaluated'
        else:
            cls = 'cell_not_evaluated'

        html_in  = self.html_in(do_print=do_print)
        introspect = "<div id='introspect_div_%s' class='introspection'></div>"%self.id()
        html_out = self.html_out(wrap, do_print=do_print)

        if 'hideall' in self.percent_directives():
            s = html_out
        else:
            s = html_in + introspect + html_out

        if div_wrap:
            s = '\n\n<div id="cell_outer_%s" class="cell_visible"><div id="cell_%s" class="%s">'%(self.id(), self.id(), cls) + s + '</div></div>'
            
        #self._html_cache[key] = s
        return s

    def html_in(self, do_print=False, ncols=80):
        """
        Returns the HTML code for the input of this cell.
        
        EXAMPLES::
        
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', None)
            sage: print C.html_in()
            <div class="insert_new_cell" id="insert_new_cell_0"...</a>
        """
        s = ''
        id = self.__id
        t = self.__in.rstrip()

        cls = "cell_input_hide" if 'hide' in self.percent_directives() else "cell_input"
    
        if not do_print:
            s += self.html_new_cell_before()

        r = max(1, number_of_rows(t.strip(), ncols))

        if do_print:
            if 'hide' in self.percent_directives():
                return ''

            tt = escape(t).replace('\n','<br>').replace('  ',' &nbsp;') + '&nbsp;'
            s += '<div class="cell_input_print">%s</div>'%tt
        else:
            s += """
               <textarea class="%s" rows=%s cols=%s
                  id         = 'cell_input_%s'
                  onKeyPress = 'return input_keypress(%s,event);'
                  onKeyDown  = 'return input_keydown(%s,event);'
                  onKeyUp    = 'return input_keyup(%s, event);'
                  onBlur     = 'cell_blur(%s); return true;'
                  onFocus    = 'cell_focused(this,%s); return true;'
               >%s</textarea>
            """%(cls, r, ncols, id, id, id, id, id, id, t)

        if not do_print:
           s+= '<a href="javascript:evaluate_cell(%s,0)" class="eval_button" id="eval_button%s" alt="Click here or press shift-return to evaluate">evaluate</a>'%(id,id)

        t = escape(t)+" "
        
        return s


    def url_to_self(self):
        """
        Returns a notebook URL for this cell.

        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.url_to_self()
            '/home/sage/0/cells/0'
        
        """
        try:
            return self.__url_to_self
        except AttributeError:
            self.__url_to_self = '/home/%s/cells/%s'%(self.worksheet_filename(), self.id())
            return self.__url_to_self

    def files(self):
        """
        Returns a list of all the files in self's directory.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'plot(sin(x),0,5)', '', W)
            sage: C.evaluate()
            sage: W.check_comp(wait=9999)
            ('d', Cell 0; in=plot(sin(x),0,5), out=
            <html><font color='black'><img src='cell://sage0.png'></font></html>
            <BLANKLINE>
            )
            sage: C.files()
            ['sage0.png']
        
        ::
        
            sage: import shutil; shutil.rmtree(nb.directory())
        """
        dir = self.directory()
        D = os.listdir(dir)
        return D

    def delete_files(self):
        """
        Deletes all of the files associated with this cell.
        
        EXAMPLES::
        
            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'plot(sin(x),0,5)', '', W)
            sage: C.evaluate()
            sage: W.check_comp(wait=9999)
            ('d', Cell 0; in=plot(sin(x),0,5), out=
            <html><font color='black'><img src='cell://sage0.png'></font></html>
            <BLANKLINE>
            )
            sage: C.files()
            ['sage0.png']
            sage: C.delete_files()
            sage: C.files()
            []
        """
        try:
            dir = self._directory_name()
        except AttributeError:
            return
        if os.path.exists(dir):
            shutil.rmtree(dir, ignore_errors=True)



    def files_html(self, out):
        """
        Returns HTML to display the files in self's directory.

        INPUT:

        - ``out`` - string to exclude files.
          Format: To exclude bar, foo, ... ``'cell://bar cell://foo ...'``

        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, 'plot(sin(x),0,5)', '', W)
            sage: C.evaluate()
            sage: W.check_comp(wait=9999)
            ('d', Cell 0; in=plot(sin(x),0,5), out=
            <html><font color='black'><img src='cell://sage0.png'></font></html>
            <BLANKLINE>
            )
            sage: C.files_html('')
            '<img src="/home/sage/0/cells/0/sage0.png?...">'
        """
        import time
        D = self.files()
        D.sort()
        if len(D) == 0:
            return ''
        images = []
        files  = []
        # The question mark trick here is so that images will be reloaded when
        # the async request requests the output text for a computation.
        # This is inspired by http://www.irt.org/script/416.htm/.
        for F in D:
            if 'cell://%s'%F in out:
                continue
            url = os.path.join(self.url_to_self(), F)
            if F.endswith('.png') or F.endswith('.bmp') or \
                    F.endswith('.jpg') or F.endswith('.gif'):
                images.append('<img src="%s?%d">'%(url, time.time()))
            elif F.endswith('.obj'):
                images.append("""<a href="javascript:sage3d_show('%s', '%s_%s', '%s');">Click for interactive view.</a>"""%(url, self.__id, F, F[:-4]))
            elif F.endswith('.mtl') or F.endswith(".objmeta"):
                pass # obj data
            elif F.endswith('.svg'):
                images.append('<embed src="%s" type="image/svg+xml" name="emap">'%url)
            elif F.endswith('.jmol'):
                # If F ends in -size500.jmol then we make the viewer applet with size 500.
                i = F.rfind('-size')
                if i != -1:
                    size = F[i+5:-5]
                else:
                    size = 500

                if self.worksheet().docbrowser():
                    jmol_name = os.path.join(self.directory(), F)
                    jmol_file = open(jmol_name, 'r')
                    jmol_script = jmol_file.read()
                    jmol_file.close()
                    
                    jmol_script = jmol_script.replace('defaultdirectory "', 'defaultdirectory "' + self.url_to_self() + '/')

                    jmol_file = open(jmol_name, 'w')
                    jmol_file.write(jmol_script)
                    jmol_file.close()
                    
                script = '<div><script>jmol_applet(%s, "%s?%d");</script></div>' % (size, url, time.time())
                images.append(script)
            elif F.endswith('.jmol.zip'):
                pass # jmol data
            elif F.endswith('.canvas3d'):
                script = '<div><script>canvas3d.viewer("%s");</script></div>' % url
                images.append(script)
            else:
                link_text = str(F)
                if len(link_text) > 40:
                    link_text = link_text[:10] + '...' + link_text[-20:]
                files.append('<a target="_new" href="%s" class="file_link">%s</a>'%(url, link_text))
        if len(images) == 0:
            images = ''
        else:
            images = "%s"%'<br>'.join(images)
        if len(files)  == 0:
            files  = ''
        else:
            files  = ('&nbsp'*3).join(files)
        return images + files

    def html_out(self, ncols=0, do_print=False):
        r"""
        Returns the HTML for self's output.

        INPUT:
        
        - ``do_print`` -- a boolean stating whether to output HTML
          for print

        - ``ncols`` -- the number of columns

        EXAMPLES::

            sage: nb = sagenb.notebook.notebook.Notebook(tmp_dir())
            sage: nb.add_user('sage','sage','sage@sagemath.org',force=True)
            sage: W = nb.create_new_worksheet('Test', 'sage')
            sage: C = sagenb.notebook.cell.Cell(0, '2+3', '5', W)
            sage: C.html_out()
            '\n...<div class="cell_output_div">\n...</div>'
        """
        if do_print and self.cell_output_type() == 'hidden':
            return '<pre>\n</pre>'
        
        out_nowrap = self.output_text(0, html=True)

        out_html = self.output_html()
        if self.introspect():
            out_wrap = out_nowrap
        else:
            out_wrap = self.output_text(ncols, html=True)
            
        typ = self.cell_output_type()
        
        if self.computing():
            cls = "cell_div_output_running"
        else:
            cls = 'cell_div_output_' + typ

        top = '<div class="%s" id="cell_div_output_%s">'%(
                         cls, self.__id)

        if do_print:
            prnt = "print_"
        else:
            prnt = ""

        out_wrap   = '<div class="cell_output_%s%s" id="cell_output_%s">%s</div>'%(
            prnt, typ, self.__id, out_wrap)
        if not do_print:
            out_nowrap = '<div class="cell_output_%snowrap_%s" id="cell_output_nowrap_%s">%s</div>'%(
                prnt, typ, self.__id, out_nowrap)
        out_html   = '<div class="cell_output_html_%s" id="cell_output_html_%s">%s </div>'%(
            typ, self.__id, out_html)

        if do_print:
            out = out_wrap + out_html
        else:
            out = out_wrap + out_nowrap + out_html
            
        s = top + out + '</div>'

        r = ''
        r += '&nbsp;'*(7-len(r))
        tbl = """
               <div class="cell_output_div">
               <table class="cell_output_box"><tr>
               <td class="cell_number" id="cell_number_%s" %s>
                 %s
               </td>
               <td class="output_cell">%s</td></tr></table></div>"""%(
                   self.__id,
                   '' if do_print else 'onClick="cycle_cell_output_type(%s);"'%self.__id,
                   r, s)

        return tbl
    


########

def format_exception(s0, ncols):
    r"""
    Make it so exceptions don't appear expanded by default.
    
    INPUT:
    
    
    -  ``s0`` - string
    
    -  ``ncols`` - integer
    
    
    OUTPUT: string
    
    If s0 contains "notracebacks" then this function always returns s0
    
    EXAMPLES::
    
        sage: sagenb.notebook.cell.format_exception(sagenb.notebook.cell.TRACEBACK,80)
        '\nTraceback (click to the left for traceback)\n...\nTraceback (most recent call last):'
        sage: sagenb.notebook.cell.format_exception(sagenb.notebook.cell.TRACEBACK + "notracebacks",80)
        'Traceback (most recent call last):notracebacks'
    """
    s = s0.lstrip()
    # Add a notracebacks option -- if it is in the string then tracebacks aren't shrunk.
    # This is currently used by the sage.server.support.help command. 
    if TRACEBACK not in s or 'notracebacks' in s:
        return s0
    if ncols > 0:
        s = s.strip()
        w = s.splitlines()
        for k in range(len(w)):
            if TRACEBACK in w[k]:
                break
        s = '\n'.join(w[:k]) + '\nTraceback (click to the left for traceback)' + '\n...\n' + w[-1]
    else:
        s = s.replace("exec compile(ur'","")
        s = s.replace("' + '\\n', '', 'single')", "")
    return s
    
ComputeCell=Cell

    
def number_of_rows(txt, ncols):
    r"""
    Returns the number of rows needed to display the string in txt if
    there are a maximum of ncols columns per row.
    
    EXAMPLES::
    
        sage: from sagenb.notebook.cell import number_of_rows
        sage: s = "asdfasdf\nasdfasdf\n"
        sage: number_of_rows(s, 8)
        2
        sage: number_of_rows(s, 5)
        4
        sage: number_of_rows(s, 4)
        4
    """
    rows = txt.splitlines()
    nrows = len(rows)
    for i in range(nrows):
        nrows += int((len(rows[i])-1)/ncols)
    return nrows
