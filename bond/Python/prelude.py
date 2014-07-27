# python-bond Python interface setup
import cStringIO
#import cPickle
import json
import os
import sys


# Redirect normal output
__PY_BOND_BUFFER = cStringIO.StringIO()
__PY_BOND_STDIN = sys.stdin
__PY_BOND_STDOUT = sys.stdout


# Define our own i/o methods
__PY_BOND_PICKLE = json

def __PY_BOND_getline():
    return __PY_BOND_STDIN.readline().rstrip()

def __PY_BOND_sendline(line=""):
    __PY_BOND_STDOUT.write(line + "\n")
    __PY_BOND_STDOUT.flush()


# Recursive repl
def __PY_BOND_remote(name, args):
    pass
#sub __PY_BOND_remote($$)
#{
#  my ($name, $args) = @_
#  my $json = $__PY_BOND_JSON->encode([$name, $args])
#  __PY_BOND_sendline("REMOTE $json")
#  return __PY_BOND_repl()
#}

def __PY_BOND_repl():
    while True:
        line = __PY_BOND_getline()
        if len(line) == 0:
            break

        line = line.split(' ', 1)
        cmd = str(line[0])
        args = __PY_BOND_PICKLE.loads(line[1]) if len(line) > 1 else []

        ret = None
        err = None
        if cmd == "EVAL" or cmd == "EVAL_BLOCK":
            try:
                mode = 'exec' if cmd == "EVAL" else 'eval'
                ret = eval(compile(args, '<string>', mode))
            except Exception as e:
                err = str(e)
        elif cmd == "EXPORT":
#    elsif($cmd eq "EXPORT")
#    {
#      my $code = "sub $args { __PY_BOND_remote('$args', \\\@_); }"
#      $ret = eval($code)
#    }
            pass
        elif cmd == "CALL":
#    elsif($cmd eq "CALL")
#    {
#      no strict 'refs'
#      my $name = $args->[0]
#
#      # NOTE: note that we use "dump" to evaluate the command as a pure string.
#      #       This allows us to execute *some* perl special forms consistenly.
#      # TODO: special-case builtins to allow transparent invocation and higher
#      #       performance with regular functions.
#      my @args = @{$args->[1]}
#      my $args_ = dump(@args)
#      $args_ = "($args_)" if(@args == 1)
#      $ret = eval($name . $args_)
#      $err = $@
#    }
            pass
        elif cmd == "RETURN":
            return args
        else:
            exit(1)

        # redirected output
        if __PY_BOND_BUFFER.tell():
            output = __PY_BOND_BUFFER.getvalue()
            code = __PY_BOND_PICKLE.dumps(['STDOUT', output])
            __PY_BOND_sendline("OUTPUT {code}".format(code=code))
            __PY_BOND_BUFFER.truncate(0)

        # error state
        state = None
        if err is None:
            state = "RETURN"
        else:
            state = "ERROR"
            ret = err

        code = __PY_BOND_PICKLE.dumps(ret)
        __PY_BOND_sendline("{state} {code}".format(state=state, code=code))

    # stream ended
    exit(0)


def __PY_BOND_start():
    sys.stdout = __PY_BOND_BUFFER
    sys.stdin = open(os.devnull)
    __PY_BOND_sendline("READY")
    exit(__PY_BOND_repl())
