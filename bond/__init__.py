import json
import os
import pexpect
import pkg_resources
import re
import sys
import tty
from bond import protocols

try:
    from shlex import quote
except ImportError:
    from pipes import quote


# Host constants
LANG  = 'Python'           # Identity language
PROTO = ['PICKLE', 'JSON'] # Supported protocols, in order of preference


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

    def expect_noecho(self, *args, **kwargs):
        self.noecho()
        return self.expect(*args, **kwargs)

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


# The main host controller
class Bond(object):
    def __init__(self, proc, trans_except, lang='<unknown>', proto=protocols.JSON):
        '''Construct a bond using an pre-initialized interpreter.
        Use ``bond.make_bond()`` to initialize it using a language driver.

        "proc": a pexpect object, with an open communication to a bond driver
        "trans_except": local behavior for transparent exceptions
        "lang": language name
        "proto": serialization object supporting "dumps/loads"'''

        self.channels = {'STDOUT': sys.stdout, 'STDERR': sys.stderr}
        self.bindings = {}
        self.trans_except = trans_except
        self._proc = proc
        self.lang = lang
        self._proto = proto


    def loads(self, *args):
        return self._proto.loads(*args)

    def dumps(self, *args):
        try:
            return self._proto.dumps(*args)
        except Exception as e:
            raise SerializationException(self.lang, str(e), 'local')


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
                raise RemoteException(self.lang, str(args), args)
            elif cmd == "ERROR":
                raise SerializationException(self.lang, str(args), 'remote')
            elif cmd == "BYE":
                raise TerminatedException(self.lang, str(args))
            elif cmd == "CALL":
                ret = None
                state = "RETURN"
                try:
                    ret = self.bindings[args[0]](*args[1])
                except Exception as e:
                    state = "EXCEPT"
                    ret = e if self.trans_except else str(e)
                try:
                    code = self.dumps(ret)
                except SerializationException as e:
                    state = "ERROR"
                    code = self.dumps(str(e))
                self._sendstate(state, code)
                continue

            raise BondException(self.lang, 'unknown interpreter state')


    def eval(self, code):
        '''Evaluate and return the value of a single statement of code in the interpreter.'''
        self._sendstate('EVAL', self.dumps(code))
        return self._repl()

    def eval_block(self, code):
        '''Evaluate a "code" block inside the interpreter. Nothing is returned.'''
        self._sendstate('EVAL_BLOCK', self.dumps(code))
        return self._repl()

    def call(self, name, *args):
        '''Call a function "name" using *args (apply *args to a callable statement "name")'''
        self._sendstate('CALL', self.dumps([name, args]))
        return self._repl()

    def close(self):
        '''Terminate the underlying interpreter'''
        self._proc.sendeof()

    def export(self, func, name=None):
        '''Export a local function "func" to be callable in the interpreter as "name".
        If "name" is not specified, use the local function name directly.'''
        if name is None:
            name = func.__name__
        self._sendstate('EXPORT', self.dumps(name))
        self.bindings[name] = func
        return self._repl()

    def callable(self, name):
        '''Return a function calling "name"'''
        return lambda *args: self.call(name, *args)

    def proxy(self, name, other, remote=None):
        '''Export a function "name" to the "other" bond, named as "remote"'''
        other.export(self.callable(name), remote or name)

    def interact(self, **kwargs):
        '''Start an interactive session with this bond. See ``bond.interact()``
        for a full list of keyword options'''
        interact(self, **kwargs)


# Drivers
def query_driver(lang):
    '''Query an individual driver by language name and return its raw data'''
    path = os.path.join('drivers', lang, 'bond.json')
    try:
        code = pkg_resources.resource_string(__name__, path).decode('utf-8')
        data = json.loads(code)
    except IOError as e:
        raise BondException(lang, 'unable to load driver data: {error}'.format(error=str(e)))
    except ValueError as e:
        raise BondException(lang, 'malformed driver data: {error}'.format(error=str(e)))
    return data


def list_drivers():
    '''Return a list of available language driver names'''
    langs = []
    drivers_path = pkg_resources.resource_filename(__name__, 'drivers')
    for path in os.listdir(drivers_path):
        data_path = os.path.join(drivers_path, path, 'bond.json')
        if os.path.isfile(data_path):
            langs.append(path)
    return langs


def _load_stage(lang, data):
    stage = os.path.join('drivers', lang, data['file'])
    stage = pkg_resources.resource_string(__name__, stage).decode('utf-8')
    if 'sub' in data:
        sub = data['sub']
        stage = re.sub(sub[0], sub[1], stage)
    return stage.strip()

def make_bond(lang, cmd=None, args=None, cwd=None, env=os.environ, def_args=True,
              trans_except=None, timeout=60, protocol=None, logfile=None):
    '''Construct a ``Bond`` using the specified language/command.

    "lang": a valid, supported language name (see ``list_drivers()``).

    "cmd": a valid shell command used to start the interpreter. If not
    specified, the default command is taken from the driver.

    "args": a list of command line arguments which are automatically quoted
    and appended to the final command line.

    "cwd": the working directory of the interpreter (defaulting to the current
    working directory)

    "env": the environment passed to the interpreter.

    "def_args": enable (default) or suppress default, extra command-line
    arguments provided by the driver.

    "trans_except": forces/disables transparent exceptions. When transparent
    exceptions are enabled, exceptions themselves are serialized and rethrown
    across the bond. It's disabled by default on all languages except Python.

    "timeout": the default communication timeout.

    "protocol": forces a specific serialization protocol to be chosen. It's
    automatically selected when not specified, and usually matches "JSON".

    "logfile": a file handle which is used to copy all input/output with the
    interpreter for debugging purposes.'''

    data = query_driver(lang)

    # select the highest compatible protocol
    protocol_list = list(filter(PROTO.__contains__, data['proto']))
    if protocol is not None:
        if not isinstance(protocol, list): protocol = [protocol]
        protocol_list = list(filter(protocol_list.__contains__, protocol))
    if len(protocol_list) < 1:
        raise BondException(lang, 'no compatible protocol supported')
    protocol = protocol_list[0]

    # determine a good default for trans_except
    if trans_except is None:
        trans_except = (lang == LANG and protocol == PROTO[0])

    # find a suitable command
    proc = None
    cmdline = None
    if args is None: args = []
    if cmd is not None:
        xargs = data['command'][0][1:] if def_args else []
        cmdline = ' '.join([cmd] + list(map(quote, xargs + args)))
        try:
            proc = Spawn(cmdline, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        except pexpect.ExceptionPexpect:
            raise BondException(lang, 'cannot execute: ' + cmdline)
    else:
        for cmd in data['command']:
            xargs = cmd[1:] if def_args else []
            cmdline = ' '.join([cmd[0]] + list(map(quote, xargs + args)))
            try:
                proc = Spawn(cmdline, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
                break
            except pexpect.ExceptionPexpect:
                pass
        if proc is None:
            raise BondException(lang, 'no suitable interpreter found')

    try:
        # wait for a prompt if needed
        if 'wait' in data['init']:
            proc.expect_noecho(data['init']['wait'])

        # probe the interpreter
        probe = data['init']['probe']
        proc.sendline_noecho(probe)
        if proc.expect_exact_noecho(['STAGE1\n', 'STAGE1\r\n']) == 1:
            tty.setraw(proc.child_fd)
    except pexpect.ExceptionPexpect:
        raise BondException(lang, 'cannot get an interactive prompt using: ' + cmdline)

    # inject base loader
    try:
        stage1 = _load_stage(lang, data['init']['stage1'])
        proc.sendline_noecho(stage1)
        if proc.expect_exact_noecho(['STAGE2\n', 'STAGE2\r\n']) == 1:
            raise BondException(lang, 'cannot switch terminal to raw mode')
    except pexpect.ExceptionPexpect:
        errors = proc.before.decode('utf-8')
        raise BondException(lang, 'cannot initialize stage1: ' + errors)

    # load the second stage
    try:
        stage2 = _load_stage(lang, data['init']['stage2'])
        stage2 = protocols.JSON.dumps({'code': stage2, 'start': [protocol, trans_except]})
        proc.sendline(stage2)
        proc.expect_exact("READY\n")
    except pexpect.ExceptionPexpect:
        errors = proc.before.decode('utf-8')
        raise BondException(lang, 'cannot initialize stage2: ' + errors)

    # remote environment is ready
    proto = getattr(protocols, protocol)
    return Bond(proc, trans_except, lang=lang, proto=proto)



# Utilities
def interact(bond, prompt=None):
    '''Start an interactive session with "bond"

    If "prompt" is not specified, use the language name of the bond. By
    default, all input lines are executed with bond.eval_block().  If "!" is
    pre-pended, execute a single statement with bond.eval() and print it's
    return value.

    You can continue the statement on multiple lines by leaving a trailing
    "\\". Type Ctrl+C to abort a multi-line block without executing it.'''

    ps1 = "{lang}> ".format(lang=bond.lang) if prompt is None else prompt
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
