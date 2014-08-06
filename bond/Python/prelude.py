# python-bond Python interface setup
import base64
import cPickle
import cStringIO
import os
import sys


# Redirect normal output
__PY_BOND_BUFFERS = {
    "STDOUT": cStringIO.StringIO(),
    "STDERR": cStringIO.StringIO()
}

__PY_BOND_CHANNELS = {
    "STDIN": sys.stdin,
    "STDOUT": sys.stdout,
    "STDERR": sys.stderr
}


# Define our own i/o methods
def __PY_BOND_getline():
    return __PY_BOND_CHANNELS['STDIN'].readline().rstrip()

def __PY_BOND_sendline(line=""):
    stdout = __PY_BOND_CHANNELS['STDOUT']
    stdout.write(line + "\n")
    stdout.flush()


# Serialization methods
class __PY_BOND_SerializationException(cPickle.PicklingError):
    pass

__PY_BOND_PROTOCOL = None

def __PY_BOND_dumps(*args):
    try:
        ret = base64.b64encode(cPickle.dumps(args, __PY_BOND_PROTOCOL))
    except cPickle.PicklingError:
        raise __PY_BOND_SerializationException("cannot encode {data}".format(data=str(args)))
    return ret

def __PY_BOND_loads(string):
    return cPickle.loads(base64.b64decode(string))[0]


# Recursive repl
__PY_BOND_TRANS_EXCEPT = None

def __PY_BOND_call(name, args):
    code = __PY_BOND_dumps([name, args])
    __PY_BOND_sendline("CALL {code}".format(code=code))
    return __PY_BOND_repl()

def __PY_BOND_export(name):
    globals()[name] = lambda *args: __PY_BOND_call(name, args)

def __PY_BOND_repl():
    while True:
        line = __PY_BOND_getline()
        if len(line) == 0:
            break

        line = line.split(' ', 1)
        cmd = str(line[0])
        args = __PY_BOND_loads(line[1]) if len(line) > 1 else []

        ret = None
        err = None
        if cmd == "EVAL" or cmd == "EVAL_BLOCK":
            try:
                mode = 'eval' if cmd == "EVAL" else 'exec'
                ret = eval(compile(args, '<string>', mode), globals())
            except Exception as e:
                err = e

        elif cmd == "EXPORT":
            __PY_BOND_export(args)

        elif cmd == "CALL":
            try:
                func = eval(compile(args[0], '<string>', 'eval'), globals())
                ret = func(*args[1])
            except Exception as e:
                err = e

        elif cmd == "RETURN":
            return args

        elif cmd == "EXCEPT":
            raise args

        elif cmd == "ERROR":
            raise __PY_BOND_SerializationException(args)

        else:
            exit(1)

        # redirected channels
        for chan, buf in __PY_BOND_BUFFERS.iteritems():
            if buf.tell():
                output = buf.getvalue()
                code = __PY_BOND_dumps([chan, output])
                __PY_BOND_sendline("OUTPUT {code}".format(code=code))
                buf.truncate(0)

        # error state
        state = "RETURN"
        if err is not None:
            if isinstance(err, __PY_BOND_SerializationException):
                state = "ERROR"
                ret = str(err)
            else:
                state = "EXCEPT"
                ret = err if __PY_BOND_TRANS_EXCEPT else str(err)
        try:
            code = __PY_BOND_dumps(ret)
        except Exception as e:
            state = "ERROR"
            code = __PY_BOND_dumps(str(e))
        __PY_BOND_sendline("{state} {code}".format(state=state, code=code))

    # stream ended
    return 0


def __PY_BOND_start(trans_except, protocol):
    global __PY_BOND_TRANS_EXCEPT, __PY_BOND_PROTOCOL

    sys.stdout = __PY_BOND_BUFFERS['STDOUT']
    sys.stderr = __PY_BOND_BUFFERS['STDERR']
    sys.stdin = open(os.devnull)

    __PY_BOND_TRANS_EXCEPT = trans_except
    __PY_BOND_PROTOCOL = protocol
    __PY_BOND_sendline("READY")
    ret = __PY_BOND_repl()
    __PY_BOND_sendline("BYE")
    exit(ret)
