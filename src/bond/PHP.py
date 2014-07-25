from bond import *

import json
import pexpect
import re
import sys


# PHP constants
PHP_PROMPT    = r'php > '
PHP_WRAP_SUFF = '__PY_BOND'

# Some local constants and definitions
_PHP_FUN_DECL = re.compile(r'^\s*function\s+(\w+)')
_PHP_PRELUDE = r'''

# Define STDIN/STDOUT
define("%(PHP_WRAP_SUFF)s_STDIN", fopen("php://stdin","r"));
define("%(PHP_WRAP_SUFF)s_STDOUT", fopen("php://stdout","r"));

# Use a custom output filter to redirect normal output
function %(PHP_WRAP_SUFF)s_output($buffer, $phase)
{
  $enc_ret = json_encode($buffer);
  %(PHP_WRAP_SUFF)s_sendline("OUTPUT $enc_ret");
}

ob_start('%(PHP_WRAP_SUFF)s_output', 1);

# Define our own i/o methods
function %(PHP_WRAP_SUFF)s_getline()
{
  return stream_get_line(%(PHP_WRAP_SUFF)s_STDIN, "\r\n");
}

function %(PHP_WRAP_SUFF)s_sendline($line = '')
{
  fwrite(%(PHP_WRAP_SUFF)s_STDOUT, $line . "\n");
}

# Helpers
function %(PHP_WRAP_SUFF)s_call($name, $json)
{
  $args = ($json !== null? json_decode($json): array());
  $ret = call_user_func_array($name, $args);
  %(PHP_WRAP_SUFF)s_return($name, $ret);
}

function %(PHP_WRAP_SUFF)s_return($name, $ret)
{
  $enc_ret = json_encode(array($name, $ret));
  %(PHP_WRAP_SUFF)s_sendline("RETURN $enc_ret");
}

''' % locals()


def _strip_newlines(code):
    """Turn a PHP code block into one line, so that an interactive PHP prompt
    does not output cruft while interpreting it"""
    # TODO: this is buggy on several levels. We could pre-process code using
    #       `php -w`, but it sounds prohibitive.
    return re.sub(r'(?:#.*)?\n\s*', '', code)


class PHP(bond):
    def __init__(self, php="php -a", timeout=None):
        self.timeout = timeout
        self._proc = pexpect.spawn(php, logfile=open('log', 'w'))
        self._expect(PHP_PROMPT)
        self._eval(_PHP_PRELUDE)

    def _sendline(self, *args, **kwargs):
        self._proc.setecho(False)
        return self._proc.sendline(*args, **kwargs)

    def _expect(self, *args, **kwargs):
        self._proc.setecho(False)
        kwargs['timeout'] = self.timeout
        return self._proc.expect(*args, **kwargs)

    def close(self):
        self._proc.sendeof()


    def _eval_core(self, code):
        # Inject the code
        code = _strip_newlines(code)
        self._sendline(r'%(code)s; %(PHP_WRAP_SUFF)s_sendline();' % {
            'PHP_WRAP_SUFF': PHP_WRAP_SUFF,
            'code': code})

        # Read all output until the next prompt
        self._expect(r'(?:([^\r\n]+)\r\n)?\r\n%(prompt)s' % {'prompt': PHP_PROMPT})
        data = self._proc.match.group(1)
        if data is None:
            return

        # Parse the serial protocol
        ret = []
        for line in data.split('\r\n'):
            (k, v) = line.split(' ', 1)
            v = json.loads(v)
            ret.append((str(k), v))
        return ret


    def _eval(self, code):
        cmds = self._eval_core(code)
        if cmds is None:
            return

        ret = None
        for (k, v) in cmds:
            if k == "OUTPUT":
                # Show all the output to the user
                sys.stdout.write(v)
            elif k == "RETURN":
                ret = v

        # Preserve only the last return value
        if ret is not None:
            return ret[1]


    def eval_block(self, code):
        code = r'call_user_func(function(){ %(code)s; })' % {'code': code}
        return self._eval(code)

    def call(self, name, *args):
        code = r'%(PHP_WRAP_SUFF)s_call(%(name)s, %(args)s)' % {
            'PHP_WRAP_SUFF': PHP_WRAP_SUFF,
            'name': repr(name),
            'args': repr(json.dumps(args)) if args else 'null'}
        return self.eval_block(code)

    def eval(self, code):
        return self._eval(code)

    def export(self, func, name):
        # TODO
        pass
