This is the first release of the standalone FEMhub Notebook.

INSTALLATION:

Make sure to pull the latest changes!

git clone git://github.com/regmi/femhub_notebook.git

QUICK: Install FEMhub, then type "./femhub -i ~/femhub_notebook.spkg" in the
current directory.

MORE DETAILS: Make sure you have Python 2.6 installed with the following packages:

      * Jinja-1.2-py2.6-macosx-10.3-i386.egg
      * Pygments-1.1.1-py2.6.egg
      * Sphinx-0.5.1-py2.6.egg
      * Twisted-8.2.0-py2.6.egg-info + TwistedWeb2
      * docutils-0.5-py2.6.egg
      * zope.interface-3.3.0-py2.6.egg-info

   Note that pexpect is not required.  Note that twisted.web2 is.  The
   only easy way to get the above is probably just to start with a
   FEMhub install.
