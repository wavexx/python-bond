import exceptions
import json
import pexpect
import sys
import tty


class Spawn(pexpect.spawn):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('env', {})['TERM'] = 'dumb'
        super(Spawn, self).__init__(*args, **kwargs)

    def sendline_noecho(self, *args, **kwargs):
        self.setecho(False)
        self.waitnoecho()
        return super(Spawn, self).sendline(*args, **kwargs)


class BondException(exceptions.IOError):
    def __init__(self, lang, error):
        self.lang = lang
        super(BondException, self).__init__(error)

    def __str__(self):
        return "BondException[{lang}]: {msg}".format(lang=self.lang, msg=self.message)

class TerminatedException(BondException):
    def __init__(self, lang, error):
        super(TerminatedException, self).__init__(lang, error)

    def __str__(self):
        return "TerminatedException[{lang}]: {msg}".format(lang=self.lang, msg=self.message)

class SerializationException(BondException):
    def __init__(self, lang, error, side):
        self.side = side
        super(SerializationException, self).__init__(lang, error)

    def __str__(self):
        return "SerializationException[{lang}, {side}]: {msg}".format(
            lang=self.lang, side=self.side, msg=self.message)

class RemoteException(BondException):
    def __init__(self, lang, error, data):
        self.data = data
        super(RemoteException, self).__init__(lang, error)

    def __str__(self):
        return "RemoteException[{lang}]: {msg}".format(lang=self.lang, msg=self.message)


class Bond(object):
    LANG = '<unknown>'

    def __init__(self, proc, trans_except):
        self.channels = {'STDOUT': sys.stdout, 'STDERR': sys.stderr}
        self.bindings = {}

        self.trans_except = trans_except
        self._proc = proc
        try:
            self._proc.expect_exact("READY\r\n")
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'unknown interpreter state')
        tty.setraw(self._proc.child_fd)


    def loads(self, string):
        return json.loads(string)

    def dumps(self, *args):
        return json.dumps(*args, skipkeys=False)


    def _dumps(self, *args):
        try:
            return self.dumps(*args)
        except Exception as e:
            raise SerializationException(self.LANG, str(e), 'local')


    def _repl(self):
        while self._proc.expect_exact('\n') == 0:
            line = self._proc.before.split(' ', 1)
            cmd = str(line[0])
            args = self.loads(line[1]) if len(line) > 1 else []

            # interpret the serial protocol
            if cmd == "RETURN":
                return args
            elif cmd == "OUTPUT":
                self.channels[args[0]].write(args[1])
                continue
            elif cmd == "EXCEPT":
                raise RemoteException(self.LANG, str(args), args)
            elif cmd == "ERROR":
                raise SerializationException(self.LANG, str(args), 'remote')
            elif cmd == "BYE":
                raise TerminatedException(self.LANG, str(args))
            elif cmd == "CALL":
                ret = None
                state = "RETURN"
                try:
                    ret = self.bindings[args[0]](*args[1])
                except Exception as e:
                    state = "EXCEPT"
                    ret = e if self.trans_except else str(e)
                try:
                    code = self._dumps(ret)
                except SerializationException as e:
                    state = "ERROR"
                    code = self._dumps(str(e))
                self._proc.sendline('{state} {code}'.format(state=state, code=code))
                continue

            raise BondException(self.LANG, 'unknown interpreter state')


    def eval(self, code):
        '''Evaluate and return the value of a single statement of code in the interpreter.'''
        code = self._dumps(code)
        self._proc.sendline('EVAL {code}'.format(code=code))
        return self._repl()

    def eval_block(self, code):
        '''Evaluate a "code" block inside the interpreter. Nothing is returned.'''
        code = self._dumps(code)
        self._proc.sendline('EVAL_BLOCK {code}'.format(code=code))
        return self._repl()

    def call(self, name, *args):
        '''Call a function "name" using *args (apply *args to a callable statement "name")'''
        code = self._dumps([name, args])
        self._proc.sendline('CALL {code}'.format(code=code))
        return self._repl()

    def close(self):
        '''Terminate the underlying interpreter'''
        self._proc.sendeof()

    def export(self, func, name=None):
        '''Export a local function "func" to be callable in the interpreter as "name".
        If "name" is not specified, use the local function name directly.'''
        if name is None:
            name = func.__name__
        self.bindings[name] = func
        self._proc.sendline('EXPORT {name}'.format(name=self._dumps(name)))
        return self._repl()

    def callable(self, name):
        '''Return a function calling "name"'''
        return lambda *args: self.call(name, *args)

    def proxy(self, name, other, remote=None):
        '''Export a function "name" to the "other" bond, named as "remote"'''
        other.export(self.callable(name), remote or name)

    def interact(self, **kwargs):
        '''Start an interactive session with this bond. See bond.interact() for
        a full list of keyword options'''
        interact(self, **kwargs)



def interact(bond, prompt=None):
    '''Start an interactive session with "bond"

    If "prompt" is not specified, use the language name of the bond. By
    default, all input lines are executed with bond.eval_block().  If "!" is
    pre-pended, execute a single statement with bond.eval() and print it's
    return value.

    You can continue the statement on multiple lines by leaving a trailing "\".
    Type Ctrl+C to abort a multi-line block without executing it.'''

    ps1 = "{lang}> ".format(lang=bond.LANG) if prompt is None else prompt
    ps1_len = len(ps1.rstrip())
    ps2 = '.' * ps1_len + ' ' * (len(ps1) - ps1_len)

    # start a simple repl
    buf = ""
    while True:
        try:
            ps = ps1 if not buf else ps2
            line = raw_input(ps)
        except EOFError:
            print("")
            break
        except KeyboardInterrupt:
            print("")
            buf = ""
            continue

        # handle multi-line blocks
        buf = (buf + "\n" + line).strip()
        if not buf:
            continue
        if buf[-1] == '\\':
            buf = buf[0:-1]
            continue

        # execute the statement/block
        ret = None
        try:
            if buf[0] == '!':
                ret = bond.eval(buf[1:])
            else:
                bond.eval_block(buf)
        except (RemoteException, SerializationException) as e:
            ret = e
        buf = ""

        # answer
        if ret is not None:
            print(ret)
