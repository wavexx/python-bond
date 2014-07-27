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
    pass

class StateException(BondException):
    pass

class RemoteException(BondException):
    pass


class Bond(object):
    LANG = '<unknown>'

    def __init__(self, proc):
        self.channels = {'STDOUT': sys.stdout}
        self.bindings = {}

        self._proc = proc
        try:
            self._proc.expect("READY\r\n")
        except pexpect.ExceptionPexpect as e:
            raise StateException('unknown "{lang}" interpreter state'.format(lang=self.LANG))


    def _repl(self):
        while self._proc.expect("(\S*)(?: ([^\r\n]+))?\r\n") == 0:
            cmd = str(self._proc.match.group(1))
            args = self._proc.match.group(2)
            if args is not None:
                args = json.loads(args)

            # interpret the serial protocol
            if cmd == "OUTPUT":
                self.channels[args[0]].write(args[1])
                continue
            elif cmd == "REMOTE":
                ret = self.bindings[args[0]](*args[1])
                ret = json.dumps(ret) if ret else None
                self._proc.sendline('RETURN {ret}'.format(ret=ret))
                continue
            elif cmd == "ERROR":
                raise RemoteException('{lang}: {error}'.format(lang=self.LANG, error=str(args)))
            elif cmd == "RETURN":
                return args

            raise StateException('unknown "{lang}" interpreter state'.format(lang=self.LANG))


    def eval(self, code):
        '''Evaluate "code" inside the interpreter within the main scope (if possible)'''
        code = json.dumps(code)
        self._proc.sendline('EVAL {code}'.format(code=code))
        return self._repl()

    def call(self, name, *args):
        '''Call a function "name" using *args'''
        code = json.dumps([name, args])
        self._proc.sendline('CALL {code}'.format(code=code))
        return self._repl()

    def eval_block(self, code):
        '''Evaluate "code" inside the interpreter, within an anonymous block'''
        code = json.dumps(code)
        self._proc.sendline('EVAL_BLOCK {code}'.format(code=code))
        return self._repl()

    def close(self):
        '''Terminate the underlying interpreter'''
        self._proc.sendeof()

    def export(self, func, name):
        '''Export a local function "func" to be callable in the interpreter as "name"'''
        self.bindings[name] = func
        self._proc.sendline('EXPORT {name}'.format(name=json.dumps(name)))
        return self._repl()

    def callable(self, name):
        '''Return a function calling "name"'''
        return lambda *args: self.call(name, *args)

    def proxy(self, name, other, remote=None):
        '''Export a function "name" to the "other" bond, named as "remote"'''
        other.export(self.callable(name), remote or name)
