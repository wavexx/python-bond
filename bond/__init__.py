import exceptions
import json
import pexpect
import sys


class Spawn(pexpect.spawn):
    def __init__(self, *args, **kwargs):
        kwargs['env'] = {'TERM': 'dumb'}
        super(Spawn, self).__init__(*args, **kwargs)

    def sendline(self, *args, **kwargs):
        self.setecho(False)
        self.waitnoecho()
        return super(Spawn, self).sendline(*args, **kwargs)

    def expect(self, *args, **kwargs):
        self.setecho(False)
        self.waitnoecho()
        return super(Spawn, self).expect(*args, **kwargs)


class BondException(exceptions.IOError):
    def __init__(self, lang, error):
        self.lang = lang
        super(BondException, self).__init__(error)

    def __str__(self):
        return "BondException[{lang}]: {msg}".format(lang=self.lang, msg=self.message)

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

    def __init__(self, proc):
        self.channels = {'STDOUT': sys.stdout, 'STDERR': sys.stderr}
        self.bindings = {}

        self._proc = proc
        try:
            self._proc.expect("READY\r\n")
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'unknown interpreter state')


    def loads(self, string):
        return json.loads(string)

    def dumps(self, *args):
        return json.dumps(*args)


    def _dumps(self, *args):
        try:
            return self.dumps(*args)
        except Exception as e:
            raise SerializationException(self.LANG, str(e), 'local')
        return ret


    def _repl(self):
        while self._proc.expect("(\S*)(?: ([^\r\n]+))?\r\n") == 0:
            cmd = str(self._proc.match.group(1))
            args = self._proc.match.group(2)
            if args is not None:
                args = self.loads(args)

            # interpret the serial protocol
            if cmd == "OUTPUT":
                self.channels[args[0]].write(args[1])
                continue
            elif cmd == "REMOTE":
                ret = self.bindings[args[0]](*args[1])
                ret = self._dumps(ret) if ret else None
                self._proc.sendline('RETURN {ret}'.format(ret=ret))
                continue
            elif cmd == "EXCEPT":
                raise RemoteException(self.LANG, str(args), args)
            elif cmd == "ERROR":
                raise SerializationException(self.LANG, str(args), 'remote')
            elif cmd == "RETURN":
                return args

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
    return value'''

    if prompt is None:
        prompt = "{lang}> ".format(lang=bond.LANG)

    # start a simple repl
    while True:
        try:
            line = raw_input(prompt)
        except EOFError:
            print('<EOF>')
            break
        if not line:
            continue

        ret = None
        try:
            if line[0] == '!':
                ret = bond.eval(line[1:])
            else:
                ret = bond.eval_block(line)
        except (RemoteException, SerializationException) as e:
            ret = e
        if ret is not None:
            print(ret)
