import json
import pexpect
import sys
import tty


# pexpect helper
class Spawn(pexpect.spawn):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('env', {})['TERM'] = 'dumb'
        super(Spawn, self).__init__(*args, **kwargs)
        tty.setraw(self.child_fd)

    def noecho(self):
        self.setecho(False)
        self.waitnoecho()

    def sendline_noecho(self, *args, **kwargs):
        self.noecho()
        return self.sendline(*args, **kwargs)

    def expect_exact_noecho(self, *args, **kwargs):
        self.noecho()
        return self.expect_exact(*args, **kwargs)


# Our exceptions
class BondException(RuntimeError):
    def __init__(self, lang, error):
        self.lang = lang
        self.error = error
        super(BondException, self).__init__(error)

    def __str__(self):
        return "BondException[{lang}]: {msg}".format(lang=self.lang, msg=self.error)

class TerminatedException(BondException):
    def __init__(self, lang, error):
        super(TerminatedException, self).__init__(lang, error)

    def __str__(self):
        return "TerminatedException[{lang}]: {msg}".format(lang=self.lang, msg=self.error)

class SerializationException(BondException, TypeError):
    def __init__(self, lang, error, side):
        self.side = side
        super(SerializationException, self).__init__(lang, error)

    def __str__(self):
        return "SerializationException[{lang}, {side}]: {msg}".format(
            lang=self.lang, side=self.side, msg=self.error)

class RemoteException(BondException):
    def __init__(self, lang, error, data):
        self.data = data
        super(RemoteException, self).__init__(lang, error)

    def __str__(self):
        return "RemoteException[{lang}]: {msg}".format(lang=self.lang, msg=self.error)


# The main base class
class Bond(object):
    LANG = '<unknown>'

    def __init__(self, proc, trans_except):
        self.channels = {'STDOUT': sys.stdout, 'STDERR': sys.stderr}
        self.bindings = {}
        self.trans_except = trans_except
        self._proc = proc


    def _init_2stage(self, proc, probe, stage1, stage2, trans_except):
        # probe the interpreter
        try:
            proc.sendline_noecho(probe)
            if proc.expect_exact_noecho(['STAGE1\n', 'STAGE1\r\n']) == 1:
                tty.setraw(proc.child_fd)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG,
                                'cannot get an interactive prompt using: '
                                + str(proc.args))

        # inject base loader
        try:
            proc.sendline(stage1)
            if proc.expect_exact_noecho(['STAGE2\n', 'STAGE2\r\n']) == 1:
                raise BondException(self.LANG, 'cannot switch terminal to raw mode')
        except pexpect.ExceptionPexpect:
            errors = proc.before.decode('utf-8')
            raise BondException(self.LANG, 'cannot initialize stage1: ' + errors)

        # load the second stage
        try:
            proc.sendline(stage2)
            proc.expect_exact("READY\n")
        except pexpect.ExceptionPexpect:
            errors = proc.before.decode('utf-8')
            raise BondException(self.LANG, 'cannot initialize stage2: ' + errors)

        # remote environment is ready
        Bond.__init__(self, proc, trans_except)


    def loads(self, buf):
        return json.loads(buf.decode('utf-8'))

    def dumps(self, *args):
        return json.dumps(*args, skipkeys=False).encode('utf-8')


    def _dumps(self, *args):
        try:
            return self.dumps(*args)
        except Exception as e:
            raise SerializationException(self.LANG, str(e), 'local')

    def _sendstate(self, cmd, code):
        ret = bytes(cmd.encode('ascii')) + b' ' + code
        self._proc.sendline(ret)


    def _repl(self):
        while self._proc.expect_exact(b'\n') == 0:
            line = self._proc.before.split(b' ', 1)
            cmd = line[0].decode('ascii')
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
                self._sendstate(state, code)
                continue

            raise BondException(self.LANG, 'unknown interpreter state')


    def eval(self, code):
        '''Evaluate and return the value of a single statement of code in the interpreter.'''
        self._sendstate('EVAL', self._dumps(code))
        return self._repl()

    def eval_block(self, code):
        '''Evaluate a "code" block inside the interpreter. Nothing is returned.'''
        self._sendstate('EVAL_BLOCK', self._dumps(code))
        return self._repl()

    def call(self, name, *args):
        '''Call a function "name" using *args (apply *args to a callable statement "name")'''
        self._sendstate('CALL', self._dumps([name, args]))
        return self._repl()

    def close(self):
        '''Terminate the underlying interpreter'''
        self._proc.sendeof()

    def export(self, func, name=None):
        '''Export a local function "func" to be callable in the interpreter as "name".
        If "name" is not specified, use the local function name directly.'''
        if name is None:
            name = func.__name__
        self._sendstate('EXPORT', self._dumps(name))
        self.bindings[name] = func
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



# Utilities
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
