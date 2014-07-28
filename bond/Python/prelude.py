# python-bond Python interface setup
import base64
import cPickle
import cStringIO
import os
import sys


# Redirect normal output
__PY_BOND_BUFFER = cStringIO.StringIO()
__PY_BOND_STDIN = sys.stdin
__PY_BOND_STDOUT = sys.stdout


# Define our own i/o methods
def __PY_BOND_getline():
    return __PY_BOND_STDIN.readline().rstrip()

def __PY_BOND_sendline(line=""):
    __PY_BOND_STDOUT.write(line + "\n")
    __PY_BOND_STDOUT.flush()


# Serialization methods
__PY_BOND_PROTOCOL = -1

def __PY_BOND_dumps(*args):
    return base64.b64encode(cPickle.dumps(args, __PY_BOND_PROTOCOL))

def __PY_BOND_loads(string):
    return cPickle.loads(base64.b64decode(string))[0]


# Recursive repl
def __PY_BOND_remote(name, args):
    code = __PY_BOND_dumps([name, args])
    __PY_BOND_sendline("REMOTE {code}".format(code=code))
    return __PY_BOND_repl()

def __PY_BOND_export(name):
    globals()[name] = lambda *args: __PY_BOND_remote(name, args)

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
                err = str(e)

        elif cmd == "EXPORT":
            __PY_BOND_export(args)

        elif cmd == "CALL":
            try:
                func = eval(compile(args[0], '<string>', 'eval'), globals())
                ret = func(*args[1])
            except Exception as e:
                err = str(e)

        elif cmd == "RETURN":
            return args

        else:
            exit(1)

        # redirected output
        if __PY_BOND_BUFFER.tell():
            output = __PY_BOND_BUFFER.getvalue()
            code = __PY_BOND_dumps(['STDOUT', output])
            __PY_BOND_sendline("OUTPUT {code}".format(code=code))
            __PY_BOND_BUFFER.truncate(0)

        # error state
        state = None
        if err is None:
            state = "RETURN"
        else:
            state = "ERROR"
            ret = err

        code = __PY_BOND_dumps(ret)
        __PY_BOND_sendline("{state} {code}".format(state=state, code=code))

    # stream ended
    exit(0)


def __PY_BOND_start(protocol=-1):
    sys.stdout = __PY_BOND_BUFFER
    sys.stdin = open(os.devnull)
    __PY_BOND_PROTOCOL = protocol
    __PY_BOND_sendline("READY")
    exit(__PY_BOND_repl())
