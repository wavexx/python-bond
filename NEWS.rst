python-bond 0.3
---------------

* Local exceptions are now forwarded remotely for exported functions.
* Except for Python, exceptions are no longer serialized, but are instead
  propagated using their originating error message. See the ``trans_except``
  keyword argument in constructors allows to tune this behavior.
* The spawned interpreter now uses a copy of the current environment.
* PHP now triggers an exception when attempting to redefine a function.
* JavaScript is now supported through Node.js.


python-bond 0.2
---------------

* Serialization errors are now intercepted by default and generate a local
  exception of type ``bond.SerializationException``.
* PHP can now "call" any callable statement.
* eval_block() no longer returns the value of the last statement. This avoids
  confusion with Perl code blocks returning unserializable references.
* Standard error is now also redirected.
