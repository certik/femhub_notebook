# -*- coding: utf-8 -*
import copy
import crypt
import cPickle
import os

SALT = 'aa'

import user_conf

def User_from_basic(basic):
    """
    Create a user from a basic data structure.
    """
    user = User(basic['username'])
    user.__dict__ = dict([('_' + x, y) for x, y in basic.iteritems()])
    user._conf = user_conf.UserConfiguration_from_basic(user._conf)
    return user

class User(object):
    def __init__(self, username, password='', email='', account_type='admin'):
        self._username = username
        self._password = crypt.crypt(password, SALT)
        self._email = email
        self._email_confirmed = False
        if not account_type in ['admin', 'user', 'guest']:
            raise ValueError, "account type must be one of admin, user, or guest"
        self._account_type = account_type
        self._conf = user_conf.UserConfiguration()
        self._temporary_password = ''
        self._is_suspended = False

    def __getstate__(self):
        d = copy.copy(self.__dict__)

        # Some old worksheets have this attribute, which we do *not* want to save.
        if d.has_key('history'):
            try:
                self.save_history()
                del d['history']
            except Exception, msg:
                print msg
                print "Unable to dump history of user %s to disk yet."%self._username
        return d

    def basic(self):
        """
        Return a basic Python data structure from which self can be
        reconstructed.
        """
        d = dict([ (x[1:],y) for x,y in self.__dict__.iteritems()])
        d['conf'] = self._conf.basic()
        return d

    def history_list(self):
        try:
            return self.history
        except AttributeError:
            import twist   # late import
            if twist.notebook is None: return []       
            history_file = "%s/worksheets/%s/history.sobj"%(twist.notebook.directory(), self._username)
            if os.path.exists(history_file):
                try:
                    self.history = cPickle.load(open(history_file))
                except:
                    print "Error loading history for user %s"%self._username
                    self.history = []
            else:
                self.history = []
            return self.history    

    def save_history(self):
        if not hasattr(self, 'history'):
            return
        import twist   # late import
        if twist.notebook is None: return
        history_file = "%s/worksheets/%s/history.sobj"%(twist.notebook.directory(), self._username)
        try:
            #print "Dumping %s history to '%s'"%(self.__username, history_file)
            his = cPickle.dumps(self.history)
        except AttributeError:
            his = cPickle.dumps([])
        open(history_file,'w').write(his)

    def username(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: User('andrew', 'tEir&tiwk!', 'andrew@matrixstuff.com', 'user').username()
            'andrew'
            sage: User('sarah', 'Miaasc!', 'sarah@ellipticcurves.org', 'user').username()
            'sarah'
            sage: User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin').username()
            'bob'
        """
        return self._username

    def __repr__(self):
        return self._username

    def conf(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: config = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin').conf(); config
            Configuration: {}
            sage: config['max_history_length']
            1000
            sage: config['default_system']
            'sage'
            sage: config['autosave_interval']
            3600
            sage: config['default_pretty_print']
            False
        """
        return self._conf

    def __getitem__(self, *args):
        return self._conf.__getitem__(*args)

    def __setitem__(self, *args):
        self._conf.__setitem__(*args)

    def password(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.password()
            'aamxw5LCYcWY.'
        """
        return self._password

    def set_password(self, password):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: old = user.password()
            sage: user.set_password('Crrc!')
            sage: old != user.password()
            True
        """
        if password == '':
            self._password = 'x'   # won't get as a password -- i.e., this account is closed.
        else:
            self._password = crypt.crypt(password, SALT)
            self._temporary_password = ''

    def set_hashed_password(self, password):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.set_hashed_password('Crrc!')
            sage: user.password()
            'Crrc!'
        """
        self._password = password
        self._temporary_password = ''

    def get_email(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.get_email()
            'bob@sagemath.net'
        """
        return self._email

    def set_email(self, email):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.get_email()
            'bob@sagemath.net'
            sage: user.set_email('bob@gmail.gov')
            sage: user.get_email()
            'bob@gmail.gov'
        """
        self._email = email
        
    def set_email_confirmation(self, value):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.is_email_confirmed()
            False
            sage: user.set_email_confirmation(True)
            sage: user.is_email_confirmed()
            True
            sage: user.set_email_confirmation(False)
            sage: user.is_email_confirmed()
            False
        """
        value = bool(value)
        self._email_confirmed = value
        
    def is_email_confirmed(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.is_email_confirmed()
            False
        """
        try:
            return self._email_confirmed
        except AttributeError:
            self._email_confirmed = False
            return False

    def password_is(self, password):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.password_is('ecc')
            False
            sage: user.password_is('Aisfa!!')
            True
        """
        if self._username == "pub":
            return False
        return self._password == crypt.crypt(password, SALT)

    def account_type(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: User('A', account_type='admin').account_type()
            'admin'
            sage: User('B', account_type='user').account_type()
            'user'
            sage: User('C', account_type='guest').account_type()
            'guest'
        """
        if self._username == 'admin':
            return 'admin'
        return self._account_type
    
    def is_admin(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: User('A', account_type='admin').is_admin()
            True
            sage: User('B', account_type='user').is_admin()
            False
        """
        return self._account_type == 'admin'

    def is_guest(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: User('A', account_type='guest').is_guest()
            True
            sage: User('B', account_type='user').is_guest()
            False
        """
        return self._account_type == 'guest'
        
    def is_suspended(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.is_suspended()
            False
        """
        try:
            return self._is_suspended
        except AttributeError:
            return False
        
    def set_suspension(self):
        """
        EXAMPLES::

            sage: from sagenb.notebook.user import User
            sage: user = User('bob', 'Aisfa!!', 'bob@sagemath.net', 'admin')
            sage: user.is_suspended()
            False
            sage: user.set_suspension()
            sage: user.is_suspended()
            True
            sage: user.set_suspension()
            sage: user.is_suspended()
            False
        """
        try:
            self._is_suspended = False if self._is_suspended else True
        except AttributeError:
            self._is_suspended = True
