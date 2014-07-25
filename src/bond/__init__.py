from abc import ABCMeta, abstractmethod
import json
import pexpect
import sys


class spawn(pexpect.spawn):
    def silent_sendline(self, *args, **kwargs):
        self.setecho(False)
        self.waitnoecho()
        return self.sendline(*args, **kwargs)

    def silent_expect(self, *args, **kwargs):
        self.setecho(False)
        self.waitnoecho()
        return self.expect(*args, **kwargs)


class bond(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, proc):
        self._proc = proc
        self._proc.silent_expect("READY\r\n")
        self.local_bindings = {}


    def _repl(self):
        while self._proc.silent_expect("(\S*)(?: ([^\r\n]+))?\r\n") == 0:
            cmd = str(self._proc.match.group(1))
            args = self._proc.match.group(2)
            if args is not None:
                args = json.loads(args)

            # interpret the serial protocol
            if cmd == "OUTPUT":
                sys.stdout.write(args)
                continue
            elif cmd == "REMOTE":
                ret = self.local_bindings[args[0]](*args[1])
                ret = json.dumps(ret) if ret else None
                self._proc.silent_sendline('RETURN {ret}'.format(ret=ret))
                continue
            elif cmd == "RETURN":
                return args

            raise IOError("unknown interpreter state")


    def eval(self, code):
        '''Evaluate "code" inside the interpreter'''
        code = json.dumps(code)
        self._proc.silent_sendline('EVAL {code}'.format(code=code))
        return self._repl()

    def call(self, name, *args):
        '''Call a function "name" using *args'''
        code = json.dumps([name, args])
        self._proc.silent_sendline('CALL {code}'.format(code=code))
        return self._repl()

    def eval_block(self, code):
        '''Evaluate "code" inside the interpreter, within an anonymous block'''
        raise Exception("method not implemented")

    def close(self):
        '''Terminate the underlying interpreter'''
        self._proc.sendeof()

    def export(self, func, name):
        '''Export a local function "func" to be callable in the interpreter as "name"'''
        self.local_bindings[name] = func

    def callable(self, name):
        '''Return a function calling "name"'''
        return lambda *args: self.call(name, *args)
