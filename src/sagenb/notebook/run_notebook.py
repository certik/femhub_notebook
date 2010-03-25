# -*- coding: utf-8 -*
"""nodoctest
Server the Sage Notebook.
"""

#############################################################################
#       Copyright (C) 2009 William Stein <wstein@gmail.com>
#  Distributed under the terms of the GNU General Public License (GPL)
#  The full text of the GPL is available at:
#                  http://www.gnu.org/licenses/
#############################################################################

try:
    # If Sage is installed, then we have gnutls, etc., and GPL'd code,
    # so we prefer GNUtls.
    import sage.misc.misc
    protocol = 'tls'
except ImportError:
    # We are not in the presence of Sage, so we probably have SSL,
    # which is better anyways.
    protocol = 'ssl'

# System libraries
import getpass, os, shutil, socket, sys
from exceptions import SystemExit

from twisted.python.runtime import platformType

from sagenb.misc.misc import (DOT_SAGENB, print_open_msg, find_next_available_port)

import notebook

conf_path       = os.path.join(DOT_SAGENB, 'notebook')

private_pem   = os.path.join(conf_path, 'private.pem')
public_pem    = os.path.join(conf_path, 'public.pem')
template_file = os.path.join(conf_path, 'cert.cfg')

def cmd_exists(cmd):
    """
    Return True if the given cmd exists.
    """
    return os.system('which %s 2>/dev/null >/dev/null'%cmd) == 0

def notebook_setup(self=None):
    if not os.path.exists(conf_path):
        os.makedirs(conf_path)

    if not cmd_exists('certtool'):
        raise RuntimeError, "You must install certtool to use the secure notebook server."

    dn = raw_input("Domain name [localhost]: ").strip()
    if dn == '':
        print "Using default localhost"
        dn = 'localhost'

    import random
    template_dict = {'organization': 'SAGE (at %s)' % (dn),
                'unit': '389',
                'locality': None,
                'state': 'Washington',
                'country': 'US',
                'cn': dn,
                'uid': 'sage_user',
                'dn_oid': None,
                'serial': str(random.randint(1,2**31)),
                'dns_name': None,
                'crl_dist_points': None,
                'ip_address': None,
                'expiration_days': 10000,
                'email': 'sage@sagemath.org',
                'ca': None,
                'tls_www_client': None,
                'tls_www_server': True,
                'signing_key': True,
                'encryption_key': True,
                }
                
    s = ""
    for key, val in template_dict.iteritems():
        if val is None:
            continue
        if val == True:
            w = ''
        elif isinstance(val, list):
            w = ' '.join(['"%s"' % x for x in val])
        else:
            w = '"%s"' % val
        s += '%s = %s \n' % (key, w) 
    
    f = open(template_file, 'w')
    f.write(s)
    f.close()

    import subprocess
    
    if os.uname()[0] != 'Darwin' and cmd_exists('openssl'):
        # We use openssl by default if it exists, since it is open
        # *vastly* faster on Linux, for some weird reason.
        cmd = ['openssl genrsa > %s' % private_pem]
        print "Using openssl to generate key"
        print cmd[0]
        subprocess.call(cmd, shell=True)
    else:
        # We checked above that certtool is available. 
        cmd = ['certtool --generate-privkey --outfile %s' % private_pem]
        print "Using certtool to generate key"
        print cmd[0]
        subprocess.call(cmd, shell=True)
        
    cmd = ['certtool --generate-self-signed --template %s --load-privkey %s \
           --outfile %s' % (template_file, private_pem, public_pem)]
    print cmd[0]
    subprocess.call(cmd, shell=True)
    
    # Set permissions on private cert
    os.chmod(private_pem, 0600)

    print "Successfully configured notebook."

def notebook_twisted(self,
             directory   = None,
             port        = 8000,
             interface   = 'localhost',        
             address     = None,
             port_tries  = 50,
             secure      = False,
             reset       = False,
             accounts    = False,
             require_login = True, 
                     
             server_pool = None,
             ulimit      = '',

             timeout     = 0,

             open_viewer = True,

             sagetex_path = "",
             start_path = "",
             fork = False,
             quiet = False,

             subnets = None):
    cwd = os.getcwd()
    # For backwards compatible, we still allow the address to be set
    # instead of the interface argument
    if address is not None:
        from warnings import warn
        message = "Use 'interface' instead of 'address' when calling notebook(...)."
        warn(message, DeprecationWarning, stacklevel=3)
        interface = address
             
    if directory is None:
        directory = '%s/sage_notebook'%DOT_SAGENB
    else:
        if isinstance(directory, basestring) and len(directory) > 0 and directory[-1] == "/":
            directory = directory[:-1]
            
    # First change to the directory that contains the notebook directory
    wd = os.path.split(directory)
    if wd[0]: os.chdir(wd[0])
    directory = wd[1]

    port = int(port)

    if not secure and interface != 'localhost':
        print '*'*70
        print "WARNING: Running the notebook insecurely not on localhost is dangerous"
        print "because its possible for people to sniff passwords and gain access to"
        print "your account. Make sure you know what you are doing."
        print '*'*70

    nb = notebook.load_notebook(directory)
    
    directory = nb._dir
    conf = os.path.join(directory, 'twistedconf.tac')
    
    if not quiet:
        print "The notebook files are stored in:", nb._dir

    nb.conf()['idle_timeout'] = int(timeout)
    
    if nb.user_exists('root') and not nb.user_exists('admin'):
        # This is here only for backward compatibility with one
        # version of the notebook. 
        s = nb.create_user_with_same_password('admin', 'root')
        # It would be a security risk to leave an escalated account around. 

    if not nb.user_exists('admin'):
        reset = True
        
    if reset:  
        passwd = get_admin_passwd()                
        if reset:
            nb.user('admin').set_password(passwd)
            print "Password changed for user 'admin'."
        else:
            nb.create_default_users(passwd)
            print "User admin created with the password you specified."
            print "\n\n"
            print "*"*70
            print "\n"
            if secure:
                print "Login to the Sage notebook as admin with the password you specified above."
        #nb.del_user('root')  
            
    nb.set_server_pool(server_pool)
    nb.set_ulimit(ulimit)
    nb.set_accounts(accounts)
    
    if os.path.exists('%s/nb-older-backup.sobj'%directory):
        nb._migrate_worksheets()
        os.unlink('%s/nb-older-backup.sobj'%directory)
        print "Updating to new format complete."

    nb.save()
    del nb

    def run(port, subnets):
        ## Create the config file
        if secure:
            if not os.path.exists(private_pem) or not os.path.exists(public_pem):
                print "In order to use an SECURE encrypted notebook, you must first run notebook.setup()."
                print "Now running notebook.setup()"
                notebook_setup()
            if not os.path.exists(private_pem) or not os.path.exists(public_pem):
                print "Failed to setup notebook.  Please try notebook.setup() again manually."
            strport = '%s:%s:interface=%s:privateKey=%s:certKey=%s'%(protocol, port, interface, private_pem, public_pem)
        else:
            strport = 'tcp:%s:interface=%s'%(port, interface)

        notebook_opts = '"%s",interface="%s",port=%s,secure=%s' % (os.path.abspath(directory),
                interface, port, secure)

        if open_viewer:
            if require_login:
                start_path = "'/?startup_token=%s' % startup_token"
            else:
                start_path = "'/'"
            if interface:
                hostname = interface
            else:
                hostname = 'localhost'
            open_page = "from sagenb.misc.misc import open_page; open_page('%s', %s, %s, %s)"%(hostname, port, secure, start_path)
        else:
            open_page = ''
        
        config = open(conf, 'w')

        if subnets is None:
            factory = "factory = channel.HTTPFactory(site)"
        else:
            if not isinstance(subnets, (list, tuple)):
                subnets = [subnets]
            factory = """
# See http://stackoverflow.com/questions/1273297/python-twisted-restricting-access-by-ip-address
from sagenb.misc.ipaddr import IPNetwork
subnets = eval(r"%s")
if not any(s.startswith('127') for s in subnets):
    subnets.insert(0, '127.0.0.0/8')
subnets = [IPNetwork(x) for x in subnets]
class RestrictedIPFactory(channel.HTTPFactory):
    def buildProtocol(self, addr):
        a = str(addr.host)
        for X in subnets:
            if a in X:
                return channel.HTTPFactory.buildProtocol(self, addr)
        print 'Ignoring all requests from IP address '+str(addr.host)
        
factory = RestrictedIPFactory(site)
"""%tuple([subnets])

        config.write("""
####################################################################        
# WARNING -- Do not edit this file!   It is autogenerated each time
# the notebook(...) command is executed.
####################################################################
from twisted.internet import reactor

# Now set things up and start the notebook
import sagenb.notebook.notebook
sagenb.notebook.notebook.JSMATH=True
import sagenb.notebook.notebook as notebook
import sagenb.notebook.twist as twist
twist.notebook = notebook.load_notebook(%s)
twist.SAGETEX_PATH = %r
twist.OPEN_MODE = %s
twist.SID_COOKIE = str(hash(%r))
twist.DIR = %r
twist.init_updates()
import sagenb.notebook.worksheet as worksheet

import signal, sys, random
def save_notebook():
    from twisted.internet.error import ReactorNotRunning
    print "Quitting all running worksheets..."
    twist.notebook.quit()
    print "Saving notebook..."
    twist.notebook.save()
    print "Notebook cleanly saved."
    
def my_sigint(x, n):
    try:
        reactor.stop()
    except ReactorNotRunning:
        pass
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    
signal.signal(signal.SIGINT, my_sigint)

## Disable client-side certificate request for gnutls
try:
    import gnutls.connection
    gnutls.connection.CERT_REQUEST = 0
except (OSError, ImportError):
    print "Note: GNUTLS not available."


## Authentication framework (ported from Knooboo)
from twisted.web2 import log, server, channel
from twisted.cred import portal, checkers, credentials
import sagenb.notebook.guard as guard
import sagenb.notebook.avatars as avatars

from twisted.cred import portal

realm = avatars.LoginSystem()
p = portal.Portal(realm)
startup_token = '%%x' %% random.randint(0, 2**128)
startup_checker = avatars.OneTimeTokenChecker()
startup_checker.token = startup_token
p.registerChecker(startup_checker)
password_checker = avatars.PasswordChecker()
p.registerChecker(password_checker)
p.registerChecker(checkers.AllowAnonymousAccess())
rsrc = guard.MySessionWrapper(p)
log.DefaultCommonAccessLoggingObserver().start()
site = server.Site(rsrc)
%s
from twisted.web2 import channel
from twisted.application import service, strports
application = service.Application("SAGE Notebook")
s = strports.service(%r, factory)
%s
s.setServiceParent(application)

reactor.addSystemEventTrigger('before', 'shutdown', save_notebook)

"""%(notebook_opts, sagetex_path, not require_login,
     os.path.abspath(directory), cwd, factory,
     strport, open_page))


        config.close()                     

        pidfile = os.path.join(directory, 'twistd.pid')
        cmd = 'twistd --pidfile="%s" -ny "%s"' % (pidfile, os.path.join(directory, 'twistedconf.tac'))

        # Check if a Twistd PID exists in the given directory
        if platformType != 'win32':
            from twisted.scripts._twistd_unix import checkPID
            try:
                checkPID(pidfile)
            except SystemExit as e:
                pid = int(open(pidfile).read())
                if str(e).startswith('Another twistd server is running,'):
                    sys.exit("""\
Another Sage Notebook server is running, PID %d.

Please either stop the old server or run the new server in a different directory.
""" % pid)
        ## Start up twisted
        if not quiet:
            print_open_msg('localhost' if not interface else interface, port, secure=secure)
        if secure and not quiet:
            print "There is an admin account.  If you do not remember the password,"
            print "quit the notebook and type notebook(reset=True)."

        if fork:
            import pexpect
            return pexpect.spawn(cmd)
        else:
            e = os.system(cmd)

        os.chdir(cwd)
        if e == 256:
            raise socket.error

        return True
        # end of inner function run
                     
    if interface != 'localhost' and not secure:
            print "*"*70
            print "WARNING: Insecure notebook server listening on external interface."
            print "Unless you are running this via ssh port forwarding, you are"
            print "**crazy**!  You should run the notebook with the option secure=True."
            print "*"*70

    port = find_next_available_port(port, port_tries)
    if open_viewer:
        "Open viewer automatically isn't fully implemented.  You have to manually open your web browser to the above URL."
    return run(port, subnets)






#######


def get_admin_passwd():
    print "\n"*2
    print "Please choose a new password for the Sage Notebook 'admin' user."
    print "Do _not_ choose a stupid password, since anybody who could guess your password"
    print "and connect to your machine could access or delete your files."
    print "NOTE: Only the md5 hash of the password you type is stored by Sage."
    print "You can change your password by typing notebook(reset=True)."
    print "\n"*2
    while True:
        passwd = getpass.getpass("Enter new password: ")
        from sagenb.misc.misc import min_password_length
        if len(passwd) < min_password_length:
            print "That password is way too short. Enter a password with at least 6 characters."
            continue
        passwd2 = getpass.getpass("Retype new password: ")
        if passwd != passwd2:
            print "Sorry, passwords do not match."
        else:
            break

    print "Please login to the notebook with the username 'admin' and the above password."
    return passwd
