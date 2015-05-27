===============
python ``bond``
===============
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


Overview
========

.. code:: python3

  >>> # Let's bond with a PHP interpreter
  >>> from bond import make_bond
  >>> php = make_bond('PHP')
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
  >>> remote_php = make_bond('PHP', 'ssh remote php')
  >>> remote_php.eval_block('function call_me() { echo "Hi from " . system("hostname") . "!"; }')
  >>> remote_php.eval('call_me()')
  Hi from remote!

  >>> # Bridge two worlds!
  >>> perl = make_bond('Perl')
  >>> php.proxy('explode', perl)
  >>> # note: explode is now available to Perl, but still executes in PHP
  >>> perl.eval('explode("=", "Mind=blown!")')
  [u'Mind', u'blown!']


A concrete example
==================

I needed ``bond`` for migrating a large PHP project to Python. With ``bond``
you can rewrite a program incrementally, while still executing all the existing
code unchanged. You can start by rewriting just a single function in an empty
shell that wraps your existing code, as follows:

.. code:: python3

  from bond import make_bond
  import sys

  php = make_bond('PHP')
  php.eval_block('include("my_original_program.php");')

  def new_function(arg)
      # do something here
      pass

  php.export(new_function, 'function_to_be_replaced')
  php.call('main', sys.argv)

You can also use ``bond`` to mix Python 2/3 code. Python <=> Python bonds
automatically use pickling as a protocol, which makes serialization almost
invisible.

Thanks to that, you can easily use ``bond`` to perform remote/parallel
computation. Nobody stops you from having multiple interpreters at the same
time: you can create bonds to setup a poor-man's distributed system with
minimal effort:

.. code:: python3

  # setup the workers
  from bond import make_bond
  hosts = ['host1', 'host2', 'host3']
  nodes = [make_bond('Python', 'ssh {} python'.format(host)) for host in hosts]

  # load our libraries first
  for node in nodes:
      node.eval_block('from library import *')

  # execute "do_something" remotely on each worker
  from threading import Thread
  threads = [Thread(target=lambda: node.call('do_something')) for node in nodes]
  for thread in threads: thread.start()

  # collect the results
  results = [thread.join() for thread in threads]

Distributed producer/consumer schemes also come for free by proxying calls:

.. code:: python3

  host1.eval_block(r'''def consumer(data):
     # do something with data
     pass
  ''')

  host2.eval_block(r'''def producer():
      while True:
	 data = function()
	 consumer(data)
  ''')

  host1.proxy('consumer', host2)
  host2.call('producer')

It's even more interesting if you realize that the producers/consumers don't
even have to be written in the same language, and don't know that the call is
actually being forwarded.

``bond`` doesn't even need to be installed remotely: the required setup is
injected directly into a live interpreter. The wire protocol is simple enough
that any language supporting an interactive REPL can be called. In fact, `the
drivers themselves <https://github.com/wavexx/bond-drivers>`_ are designed to
be used from any other language.


API
===

Initialization
--------------

A ``bond.Bond`` object is not normally constructed directly, but by using the
``bond.make_bond()`` function:

.. code:: python3

  import bond
  interpreter = bond.make_bond('language')

The first argument should be the desired language name ("JavaScript", "PHP",
"Perl", "Python"). The list of supported languages can be fetched dynamically
using ``bond.list_drivers()``.

You can override the default interpreter command using the second argument,
which allows to specify any shell command to be executed:

.. code:: python3

  import bond
  py = bond.make_bond('Python', 'ssh remote python3')

An additional *list* of arguments to the interpreter can be provided using the
third argument, ``args``:

.. code:: python3

  import bond
  py = bond.make_bond('Python', 'ssh remote python3', ['-E', '-OO'])

The *arguments*, contrarily to the command, are automatically quoted.

Some command line arguments may be supplied automatically by the driver to
force an interactive shell; for example "-i" is supplied if Python is
requested. You can disable default arguments by using ``def_args=False``.

The following keyword arguments are supported:

``cwd``:

  Working directory for the interpreter (defaults to current working
  directory).

``env``:

  Environment for the interpreter (defaults to ``os.environ``).

``def_args``:

  Enable (default) or suppress default, extra command-line arguments to the
  interpreter.

``timeout``:

  Defines the timeout for the underlying communication protocol. Note that
  ``bond`` cannot distinguish between a slow call or noise generated while the
  interpreter is set up. Defaults to 60 seconds.

``logfile``:

  Accepts a file handle which is used to log the entire communication with the
  underlying interpreter for debugging purposes.

``trans_except``:

  Enables/disables "transparent exceptions". Exceptions are always first class,
  but when ``trans_except`` is enabled, the exception objects themselves will
  be forwarded across the bond. If ``trans_except`` is disabled (the default
  for all languages except Python), then local exceptions will always contain a
  string representation of the remote exception instead, which avoids
  serialization errors.


``bond.Bond`` Methods
---------------------

The resulting ``bond.Bond`` class has the following methods:

``eval(code)``:

  Evaluate and return the value of a *single statement* of code in the
  interpreter.

``eval_block(code)``:

  Execute a "code" block inside the top-level of the interpreter. Any construct
  which is legal by the current interpreter is allowed. Nothing is returned.

``ref(code)``:

  Return a reference to an *single, unevaluated statement* of code, which can
  be later used in eval(), eval_block() or as an *immediate* argument to call().
  See `Quoted expressions`_.

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


Exceptions
----------

All exceptions thrown by the ``bond`` module are of base type ``RuntimeError``
<= ``BondException``.

``BondException``:
  Thrown during initialization or unrecoverable errors.

``TerminatedException``:
  Thrown when the bond exits unexpectedly.

``SerializationException``:
  Thrown when an object/exception which is sent *or* received cannot be
  serialized by the current protocol. The ``side`` attribute can be either
  "local" (when attempting to *send*) or "remote" (when *receiving*). A
  ``SerializationException`` is not fatal.

``RemoteException``:
  Thrown for uncaught remote exceptions. The "data" attribute contains either
  the error message (with ``trans_except=False``) or the remote exception
  itself (``trans_except=True``).

Beware that both ``SerializationException`` (with ``side="remote"``) and
``RemoteException`` may actually be originating from uncaught *local*
exceptions when an exported function is called. Pay attention to the error
text/data in these cases, as it will contain several nested exceptions.


Quoted expressions
------------------

``bond`` has minimal support for quoted expressions, through the use of
``Bond.ref()``. ``ref()`` returns a reference to a unevaluated statement that
can be fed back to ``eval()``, ``eval_block()``, or as an *immediate* (i.e.:
not nested) argument to ``call()``. References are bound to the interpreter
that created them.

``ref()`` allows to "call" methods that take remote un-serializable arguments,
such as file descriptors, without the use of a support function and/or eval:

.. code:: python3

  pl = make_bond('Perl')
  pl.eval_block('open($fd, ">file.txt");')
  fd = pl.ref('$fd')
  pl.call('syswrite', fd, "Hello world!")
  pl.call('close', fd)

Since ``ref()`` objects cannot be nested, there are still cases where it might
be necessary to use a support function. To demonstrate, we rewrite the above
example without quoted expressions, while still allowing an argument ("Hello
world!") to be local:

.. code:: python3

  pl = make_bond('Perl')
  pl.eval_block('open($fd, ">file.txt");')
  pl.eval_block('sub syswrite_fd { syswrite($fd, shift()); };')
  pl.call('syswrite_fd', "Hello world!")
  pl.eval('close($fd)')

Or more succinctly:

.. code:: python3

  pl.call('sub { syswrite($fd, shift()); }', "Hello world!")


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
  ``TypeError`` <= ``_BOND_SerializationException``.


Python 2 / Python 3:

You can freely mix Python versions between hosts/interpreters (that is: you can
run Python 3 code from a Python 2 host and vice-versa). You'll need to disable
transparent exceptions though, as the exception hierarchy is different between
major versions:

.. code:: python3

  # assuming a python2.7 environment
  from bond import make_bond
  py = make_bond('Python', 'python3', trans_except=False)


PHP
---

Requirements:

* The PHP's >= 5.3 command line interpreter needs to be installed. On
  Debian/Ubuntu, the required package is ``php5-cli``.

Serialization:

* Performed remotely using ``JSON``. Implement the `JsonSerializable
  <http://php.net/manual/en/jsonserializable.jsonserialize.php>`_ interface to
  tweak which/how objects are encoded.

* Serialization exceptions on the remote side are of base type
  ``_BOND_SerializationException``. The detailed results of the error can
  also be retrieved using `json_last_error
  <http://php.net/manual/en/function.json-last-error.php>`_.

Limitations:

* PHP <= 5.3 doesn't support the ``JsonSerializable`` interface, and thus lacks
  the ability of serializing arbitrary objects.

* You cannot use ``call`` on a built-in function such as "echo". You have to
  use a real function instead, like "print". You can still call "echo" by using
  ``eval`` or ``eval_block``.

* Unfortunately, you cannot catch "fatal errors" in PHP. If the evaluated code
  triggers a fatal error it will terminate the bond without appeal. A common
  example of such error can be attempting to use an undefined variable or
  function (which could happen while prototyping).

* Due to the inability to override built-in functions, ``error_reporting()`` is
  not completely transparent and always returns 0. It shouldn't be used to
  control the display error level. Use ``_BOND_error_reporting()`` instead,
  which has the same usage/signature as the built-in function.


Perl
----

Perl is a quirky language, due to its syntax. We assume here you're an
experienced Perl developer.

Requirements:

* Perl >= 5.14 is required, with the following modules:

  - ``JSON``
  - ``Data::Dump``
  - ``IO::String``

  On Debian/Ubuntu, the required packages are ``libjson-perl``
  ``libdata-dump-perl`` and ``libio-string-perl``.

Serialization:

* Performed remotely using ``JSON``. Implement the `TO_JSON
  <http://search.cpan.org/dist/JSON/lib/JSON.pm#allow_blessed>`_ method on
  blessed references to tweak which/how objects are encoded.

* Serialization exceptions on the remote side are generated by dying with a
  ``_BOND_SerializationException`` @ISA.

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

* Node.js v0.6.12 and v0.10.29 have been tested. On Debian/Ubuntu, the required
  package is ``nodejs``.

Serialization:

* Performed remotely using ``JSON``. Implement the `toJSON
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify>`_
  property to tweak which/how objects are encoded.

* Serialization exceptions on the remote side are of base type
  ``TypeError`` <= ``_BOND_SerializationException``.

Limitations:

* Currently the code expects an unix-like environment with ``/dev/stdin`` to
  perform synchronous I/O.

* Since there's no distinction between "plain" objects (dictionaries) and any
  other object, almost everything will be silently serialized. Define a custom
  "toJSON" property on your "real" objects to control this behavior.

* When executing a remote JavaScript bond with Node.js <= 0.6, you need to
  manually invoke the REPL, as follows:

  .. code:: python3

    js = make_bond('JavaScript',
		   "ssh remote node -e 'require\(\\\"repl\\\"\).start\(\)'",
		   def_args=False)

  When executing "node" locally, or when using Node.js >= 0.10, this is not
  required (the "-i" flag is automatically provided).


Common limitations
------------------

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


General/support mailing list
============================

If you are interested in announcements and development discussions about
``bond``, you can subscribe to the `bond-devel` mailing list by sending an
empty email to <bond-devel+subscribe@thregr.org>.

You can contact the main author directly at <wavexx@thregr.org>, though using
the general list is encouraged.


Authors and Copyright
=====================

`python-bond` can be found at
http://www.thregr.org/~wavexx/software/python-bond/

| "python-bond" is distributed under the GNU GPLv2+ license (see COPYING).
| Copyright(c) 2014-2015 by wave++ "Yuri D'Elia" <wavexx@thregr.org>.

python-bond's GIT repository is publicly accessible at::

  git://src.thregr.org/python-bond

or at https://github.com/wavexx/python-bond
