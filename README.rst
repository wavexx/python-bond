================
 python ``bond``
================
---------------------------------------------------
Ambivalent bonds between Python and other languages
---------------------------------------------------

.. contents::

The Python module ``bond`` supports transparent remote/recursive evaluation
between Python and another interpreter through automatic call serialization.

In poorer words, a ``bond`` lets you call functions in other languages as they
were normal Python functions. It *also* allows other languages to *call Python
functions* as if they were native.

Remote output is also transparently redirected locally, and since the
evaluation is performed through a persistent co-process, you can actually spawn
interpreters on different hosts through "ssh" efficiently.

``bond`` currently supports PHP, Perl, JavaScript (Node.js) and Python itself.


A simple  example
=================

.. code:: python3

  >>> # Let's bond with a PHP interpreter
  >>> from bond import bond
  >>> php = bond('PHP')
  >>> php.eval_block('echo "Hello world!\n";')
  Hello world!

  >>> # Make an expensive split function using PHP's explode
  >>> split = php.callable('explode')
  >>> split(' ', "Hello world splitted by PHP!")
  [u'Hello', u'world', u'splitted', u'by', u'PHP!']

  >>> # Call Python from PHP
  >>> def call_me():
  ...     print("Hi, this is Python talking!")
  >>> php.export(call_me)
  >>> php.eval('call_me()')
  Hi, this is Python talking!

  >>> # Use some remote resources
  >>> remote_php = bond('PHP', 'ssh remote php')
  >>> remote_php.eval_block('function call_me() { echo "Hi from " . system("hostname") . "!"; }')
  >>> remote_php.eval('call_me()')
  Hi from remote!

  >>> # Bridge two worlds!
  >>> perl = bond('Perl')
  >>> php.proxy('explode', perl)
  >>> # note: explode is now available to Perl, but still executes in PHP
  >>> perl.eval('explode("=", "Mind=blown!")')
  [u'Mind', u'blown!']


Why?
====

I needed ``bond`` for refactoring a large ``PHP`` project, *mostly*. With
``bond`` you can rewrite your program incrementally, while still executing all
your existing code unchanged. You can start by rewriting just a single
function:

.. code:: python3

  from bond import bond
  import sys

  php = bond('PHP')
  php.eval_block('include("my_original_program.php");')

  def new_function(arg)
      # do something here
      pass

  php.export(new_function, 'function_to_be_replaced')
  php.call('main', sys.argv)

It turns out that with the same approach you can easily perform remote/parallel
computation as well. Nobody stops you from having multiple interpreters at the
same time: you can use ``bond`` to setup a poor-man's distributed system with
minimal effort:

.. code:: python3

  # setup the workers
  from bond import bond
  hosts = ['host1', 'host2', 'host3']
  nodes = [bond('Python', 'ssh {} python'.format(host)) for host in hosts]

  # load our libraries first
  for node in nodes:
      node.eval_block('from library import *')

  # execute "do_something" remotely on each worker
  from threading import Thread
  threads = [Thread(target=lambda: node.call('do_something')) for node in nodes]
  for thread in threads: thread.start()

  # collect the results
  results = [thread.join() for thread in threads]

``bond`` aims to be completely invisible on the remote side (you don't need
``bond`` installed remotely at all). The wire protocol is simple enough to be
extended to any language supporting an interactive interpreter.


API
===

Construction
------------

You can construct a ``bond`` by using the ``bond.bond()`` function:

.. code:: python3

  import bond
  interpreter = bond.bond('language')

The first argument should be the desired language name ("JavaScript", "PHP",
"Perl", "Python"). The list of supported languages can be fetched dynamically
using ``bond.list_drivers()``.

You can override the default interpreter command using the second argument,
which allows to specify any shell command to be executed:

.. code:: python3

  import bond
  interpreter = bond.bond('Python', 'ssh remote python3')

Several command line arguments are supplied automatically by the driver to
force an interactive shell: for example, "-i" if Python is requested. You can
override these using the ``args`` keyword argument. An additional *list* of
arguments can be provided using ``xargs``. All the provided arguments are
automatically quoted.

Furthermore, the following keyword arguments are supported:

``cwd``:

  Working directory for the interpreter (defaults to current working
  directory).

``env``:

  Environment for the interpreter (defaults to ``os.environ``).

``timeout``:

  Defines the timeout for the underlying communication protocol. Note that
  ``bond`` cannot distinguish between a slow call or noise generated while the
  interpreter is set up. Defaults to 60 seconds.

``logfile``:

  Accepts a file handle which is used to log the entire communication with the
  underlying interpreter for debugging purposes.

``trans_except``:

  Enables/disables "transparent exceptions". If ``trans_except`` is enabled,
  exceptions will be forwarded across the bond using the original data-type. If
  ``trans_except`` is disabled (the default for all languages except Python),
  then local exceptions will always contain a string representation of the
  remote exception instead, which avoids serialization errors.


``bond.Bond`` Methods
---------------------

The resulting ``bond.Bond`` class has the following methods:

``eval(code)``:

  Evaluate and return the value of a *single statement* of code in the
  interpreter.

``eval_block(code)``:

  Execute a "code" block inside the interpreter. Any construct which is legal
  by the current interpreter is allowed. Nothing is returned.

``close()``:

  Terminate the communication with the interpreter.

``call(name, *args)``:

  Call a function "name" in the interpreter using the supplied list of
  arguments \*args (apply \*args to a callable statement defined by "name").
  The arguments are automatically converted to their other language's
  counterpart. The return value is captured and converted back to Python as
  well.

``callable(name)``:

  Return a function that calls "name":

  .. code:: python

    explode = php.callable('explode')
    # Now you can call explode as a normal, local function
    explode(' ', 'Hello world')

``export(func, name)``:

  Export a local function "func" so that can be called on the remote language
  as "name". If "name" is not specified, use the local function name directly.
  Note that "func" must be a function *reference*, not a function name.

``proxy(name, other, remote)``:

  Export a function "name" from the current ``bond`` to "other", named as
  "remote". If "remote" is not provided, the same value as "name" is used.

``interact()``:

  Start an interactive session with the underlying interpreter. By default, all
  input lines are executed with bond.eval_block(). If "!" is pre-pended,
  execute a single statement with bond.eval() and print it's return value. You
  can continue the statement on multiple lines by leaving a trailing "\\". Type
  Ctrl+C to abort a multi-line block without executing it.


Language support
================

Python
------

Python, as the identity language, has no restriction on data types. Everything
is pickled on both sides, including exceptions.


Serialization:

* Performed locally and remotely using ``cPickle`` in Python 2 or `pickle
  <https://docs.python.org/2/library/pickle.html>`_ in Python 3.

* Serialization exceptions on the remote side are of base type
  ``TypeError`` <= ``_PY_BOND_SerializationException``.


Python 2 / Python 3:

You can freely mix Python versions between hosts/interpreters (that is: you can
run Python 3 code from a Python 2 host and vice-versa). You'll need to disable
transparent exceptions though, as the as the exception hierarchy is different
between major versions:

.. code:: python3

  # assuming a python2.7 environment
  from bond import bond
  py = bond('Python', 'python3', trans_except=False)


PHP
---

Requirements:

* The PHP's command line interpreter needs to be installed. On Debian/Ubuntu,
  the required package is ``php5-cli``.

Serialization:

* Performed remotely using ``JSON``. Implement the `JsonSerializable
  <http://php.net/manual/en/jsonserializable.jsonserialize.php>`_ interface to
  tweak which/how objects are encoded.

* Serialization exceptions on the remote side are of base type
  ``_PY_BOND_SerializationException``. The detailed results of the error can
  also be retrieved using `json_last_error
  <http://php.net/manual/en/function.json-last-error.php>`_.

Limitations:

* You cannot use "call" on a built-in function such as "echo" (use "eval" in
  that case). You have to use a real function instead, like "print".

* Unfortunately, you cannot catch "fatal errors" in PHP. If the evaluated code
  triggers a "fatal error" it will terminate the bond without appeal. A common
  example of "fatal error" in PHP is attempting to use an undefined variable or
  function (which could happen while prototyping).


Perl
----

Perl is a quirky language, due to its syntax. We assume here you're an
experienced Perl developer.

Requirements:

* The ``JSON`` and ``Data::Dump`` modules are required (``libjson-perl`` and
  ``libdata-dump-perl`` in Debian/Ubuntu).

Serialization:

* Performed remotely using ``JSON``. Implement the `TO_JSON
  <http://search.cpan.org/dist/JSON/lib/JSON.pm#allow_blessed>`_ method on
  blessed references to tweak which/how objects are encoded.

* Serialization exceptions on the remote side are generated by dying with a
  ``_PY_BOND_SerializationException`` @ISA.

Gotchas:

* By default, evaluation is forced in array context, as otherwise most of the
  built-ins working with arrays would return an useless scalar. Use the
  "scalar" keyword for the rare cases when you really need it to.

* You can "call" any function-like statement, as long as the last argument is
  expected to be an argument list. This allows you to call builtins directly:

  .. code:: python3

    perl.call('map { $_ + 1 }', [1, 2, 3])

* You can of course "call" a statement that returns any ``CODE``. Meaning that
  you can call references to functions as long as you dereference them first:

  .. code:: python3

    perl.call('&$fun_ref', ...)
    perl.call('&{ $any->{expression} }', ...)

  Likewise you can "call" objects methods directly:

  .. code:: python3

    perl.call('$object->method', ...)

* ``eval_block`` introduces a new block. Variables declared as "my" will not be
  visible into a subsequent ``eval_block``. Use a fully qualified name or "our"
  to define variables that should persist across blocks:

  .. code:: python3

    perl.eval_block('our $variable = 1;')
    perl.eval_block('do_something_with($variable);')


JavaScript
----------

JavaScript is supported through `Node.js <http://nodejs.org/>`_.

Requirements:

* Only Node.js v0.10.29 has been tested. On Debian/Ubuntu, the required package
  is ``nodejs``.

Serialization:

* Performed remotely using ``JSON``. Implement the `toJSON
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify>`_
  property to tweak which/how objects are encoded.

* Serialization exceptions on the remote side are of base type
  ``TypeError`` <= ``_PY_BOND_SerializationException``.

Limitations:

* Currently the code expects an unix-like environment with ``/dev/stdin`` to
  perform synchronous I/O.

* Since there's no distinction between "plain" objects (dictionaries) and any
  other object, almost everything will be silently serialized. Define a custom
  "toJSON" property on your "real" objects to control this behavior.


Common traits/limitations
-------------------------

* Except for Python, only basic types (booleans, numbers, strings, lists/arrays
  and maps/dictionaries) can be transferred between the interpreters.

* Serialization is performed locally using ``JSON``. Implement a custom
  `JSONEncoder <https://docs.python.org/2/library/json.html#json.JSONEncoder>`_
  to tweak which/how objects are encoded.

* If an object that cannot be serialized reaches a "call", "eval", or even a
  non-local return such as an *error or exception*, it will generate a
  ``SerializationException`` on the local (Python) side.

* Strings are *always* UTF-8 encoded.

* References are implicitly broken as *objects are transferred by value*. This
  is obvious, as you're talking with a separate process, but it can easily be
  forgotten due to the blurring of the boundary.

* Calling functions across the bridge is slow, also in Python, due to the
  serialization. But the execution speed of the functions themselves is *not
  affected*. This might be perfectly reasonable if there are only occasional
  calls between languages, and/or the calls themselves take a significant
  fraction of time.


Authors and Copyright
=====================

| "python-bond" is distributed under GPL2 (see COPYING) WITHOUT ANY WARRANTY.
| Copyright(c) 2014 by wave++ "Yuri D'Elia" <wavexx@thregr.org>.

python-bond's GIT repository is publicly accessible at::

  git://src.thregr.org/python-bond

or at `GitHub <https://github.com/wavexx/python-bond>`_.
