from __future__ import print_function
import bond
from tests import *

def test_api_v0():
    # TODO: language constructors (as supported in v0) are deprecated in favor
    #       of the make_bond function.
    import bond.PHP
    php = bond.PHP.PHP(timeout=TIMEOUT)
    assert(php.eval('1') == 1)

    import bond.Perl
    perl = bond.Perl.Perl(timeout=TIMEOUT)
    assert(perl.eval('1') == 1)

    import bond.Python
    py = bond.Python.Python(timeout=TIMEOUT)
    assert(py.eval('1') == 1)

    import bond.JavaScript
    js = bond.JavaScript.JavaScript(timeout=TIMEOUT)
    assert(js.eval('1') == 1)
