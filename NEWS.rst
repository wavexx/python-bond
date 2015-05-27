python-bond 1.4
---------------

* Performance/documentation tweaks.


python-bond 1.3
---------------

* Added support for "Quoted expressions". ``call()`` can now be used on remote
  functions expecting one or more remote unserializable objects as their
  arguments, without the need of a support function and/or ``eval()``.


python-bond 1.2
---------------

* PHP's error level can now be controlled through the ``_BOND_error_level()``
  function (see the PHP "Limitations" section).
* An initialization race with PHP <= 5.3 (causing intermittent initialization
  issues) has been fixed.
* The license has been changed from GPLv2 to GNU GPLv2+.
* A new mailing list for announcements and development discussions has been
  created (see the README).


python-bond 1.1
---------------

* PHP output redirection was broken in 1.0; it's now fixed.
* PHP now also redirects error messages to stderr, honouring correctly
  ``error_reporting()`` and ``display_errors``.


python-bond 1.0
---------------

* The API has been streamlined: ``make_bond()`` is now the primary method of
  constructing ``Bond`` objects, independently of the interpreter language.
  The old language constructors are still supported, but are deprecated and
  will be removed in a future release.
* All functions/objects/methods are now documented with docstrings.
* Bond initialization errors, especially errors related to missing
  dependencies, are now much easier to understand.
* Serialization exceptions on the remote side have been renamed to
  ``_BOND_SerializationException`` for consistency with other languages.
* JavaScript/Node.js support was previously limited to versions >= 0.10. Any
  version of Node.js starting with 0.6.12 is now supported.
* PHP support was previously limited to versions >= 5.6. Any version of PHP
  starting with 5.3 is now supported.
* A Perl dependency on ``IO::String`` was previously missing, and has now been
  correctly documented.


python-bond 0.5
---------------

* Python 3 support has been added, with the ability to mix major Python
  versions between the host and the bond.
* All languages/interpreters can now be executed with a remote shell without
  using additional arguments.
* On the remote side, ``__PY_BOND_SerializationException`` has been renamed to
  ``_PY_BOND_SerializationException`` as it can be trapped by the user code.
* The scope of a PHP code block in an exported, recursive call has been fixed.


python-bond 0.4
---------------

* Serialization exceptions generating from exported functions now correctly
  unwind the remote stack.
* An exception with exported functions returning no values was fixed.
* The size of the serialization buffers was previously limited to 4k; it's now
  bound to the available memory.
* ``bond.interact()`` now can accept multi-line blocks by using a trailing
  backslash at the end of the line.
* Performance was optimized.


python-bond 0.3
---------------

* Local exceptions are now forwarded remotely for exported functions.
* Excluding Python, exceptions are no longer serialized, but are instead
  propagated using their originating error message. See the ``trans_except``
  keyword argument in constructors that allows to tune this behavior.
* The spawned interpreter now uses a copy of the current environment.
* PHP now triggers an exception when attempting to redefine a function.
* JavaScript is now supported through Node.js.


python-bond 0.2
---------------

* Serialization errors are now intercepted by default and generate a local
  exception of type ``bond.SerializationException``.
* PHP can now "call" any callable statement.
* ``eval_block()`` no longer returns the value of the last statement. This
  avoids confusion with Perl code blocks returning unserializable references.
* Standard error is now also redirected.
