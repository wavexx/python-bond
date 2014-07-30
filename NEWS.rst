python-bond 0.2
---------------

* Serialization errors are now intercepted by default and generate a local
  exception of type ``bond.SerializationError``.
* PHP can now "call" any callable statement.
* eval_block() no longer returns the value of the last statement. This avoids
  confusion with Perl code blocks returning unserializable references.
* Standard error is now also redirected.
