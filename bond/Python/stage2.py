# python-bond Python interface setup
import base64
import io
import os
import sys

try:
    import cPickle as pickle
except ImportError:
    import pickle


# Redirect normal output
__PY_BOND_BUFFERS = {
    "STDOUT": io.BytesIO(),
    "STDERR": io.BytesIO()
}

__PY_BOND_CHANNELS = {
    "STDIN": sys.stdin,
    "STDOUT": sys.stdout,
    "STDERR": sys.stderr
}


# Define our own i/o methods
def __PY_BOND_getline():
    return __PY_BOND_CHANNELS['STDIN'].readline().rstrip()

def __PY_BOND_sendline(line=b''):
    stdout = __PY_BOND_CHANNELS['STDOUT']
    stdout.write(line + b'\n')
    stdout.flush()

def __PY_BOND_sendstate(state, code=None):
    line = bytes(state.encode('ascii'))
    if code is not None:
        line = line + b' ' + code
    __PY_BOND_sendline(line)


# Serialization methods
class _PY_BOND_SerializationException(TypeError):
    pass

__PY_BOND_PROTOCOL = None

def __PY_BOND_dumps(*args):
    try:
        ret = base64.b64encode(pickle.dumps(args, __PY_BOND_PROTOCOL))
    except (TypeError, pickle.PicklingError):
        raise _PY_BOND_SerializationException("cannot encode {data}".format(data=str(args)))
    return ret

def __PY_BOND_loads(buf):
    return pickle.loads(base64.b64decode(buf))[0]


# Recursive repl
__PY_BOND_TRANS_EXCEPT = None

def __PY_BOND_call(name, args):
    __PY_BOND_sendstate("CALL", __PY_BOND_dumps([name, args]))
    return __PY_BOND_repl()

def __PY_BOND_export(name):
    globals()[name] = lambda *args: __PY_BOND_call(name, args)

def __PY_BOND_repl():
    SENTINEL = 1
    while True:
        line = __PY_BOND_getline()
        if len(line) == 0:
            break

        line = line.split(b' ', 1)
        cmd = line[0].decode('ascii')
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
                func = eval(args[0], globals())
                ret = func(*args[1])
            except Exception as e:
                err = e

        elif cmd == "RETURN":
            return args

        elif cmd == "EXCEPT":
            raise args if isinstance(args, Exception) else Exception(args)

        elif cmd == "ERROR":
            raise _PY_BOND_SerializationException(args)

        else:
            exit(1)

        # redirected channels
        for chan, buf in __PY_BOND_BUFFERS.items():
            if buf.tell():
                output = buf.getvalue() if not isinstance(buf, io.TextIOWrapper) \
                  else buf.buffer.getvalue().decode(buf.encoding)
                code = __PY_BOND_dumps([chan, output])
                __PY_BOND_sendstate("OUTPUT", code)
                buf.truncate(0)

        # error state
        state = "RETURN"
        if err is not None:
            if isinstance(err, _PY_BOND_SerializationException):
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
        __PY_BOND_sendstate(state, code)

    # stream ended
    return 0


def __PY_BOND_start(trans_except, protocol):
    global __PY_BOND_TRANS_EXCEPT, __PY_BOND_PROTOCOL
    global __PY_BOND_BUFFERS, __PY_BOND_CHANNELS

    if isinstance(sys.stdout, io.TextIOWrapper):
        for buf in __PY_BOND_BUFFERS:
            __PY_BOND_BUFFERS[buf] = io.TextIOWrapper(__PY_BOND_BUFFERS[buf])
        for chan in __PY_BOND_CHANNELS:
            __PY_BOND_CHANNELS[chan] = __PY_BOND_CHANNELS[chan].detach()

    sys.stdout = __PY_BOND_BUFFERS['STDOUT']
    sys.stderr = __PY_BOND_BUFFERS['STDERR']
    sys.stdin = open(os.devnull)

    __PY_BOND_TRANS_EXCEPT = trans_except
    __PY_BOND_PROTOCOL = protocol
    __PY_BOND_sendstate("READY")
    ret = __PY_BOND_repl()
    __PY_BOND_sendstate("BYE")
    exit(ret)
