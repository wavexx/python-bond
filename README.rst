================
 python ``bond``
================
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

``bond`` currently supports PHP, Perl and Python itself.


A simple  example
=================

.. code:: python3

  >>> # Let's bond with a PHP interpreter
  >>> from bond.PHP import PHP
  >>> php = PHP()
  >>> php.eval_block('echo "Hello world!\n";')
  Hello world!

  >>> # Make an expensive split function using PHP's explode
  >>> split = php.callable('explode')
  >>> split(' ', "Hello world splitted by PHP!")
  [u'Hello', u'world', u'splitted', u'by', u'PHP!']

  >>> # Call Python from PHP
  >>> def call_me():
  ...     print("Hi, this is Python talking!")
  >>> php.export(call_me, 'call_me')
  >>> php.eval('call_me()')
  Hi, this is Python talking!

  >>> # Use some remote resources
  >>> remote_php = PHP('ssh remote php')
  >>> remote_php.eval_block('function call_me() { echo "Hi from " . system("hostname") . "!"; }')
  >>> remote_php.eval('call_me()')
  Hi from remote!

  >>> # Bridge two worlds!
  >>> from bond.Perl import Perl
  >>> perl = Perl()
  >>> php.proxy('explode', perl)
  >>> # note: explode is now available to Perl
  >>> perl.eval('explode("=", "Mind=blown!")')
  [u'Mind', u'blown!']


Why?
====

I needed ``bond`` for refactoring a large ``PHP`` project, mostly. With
``bond`` you can rewrite your program incrementally, while still executing all
your existing code unchanged. You can start by rewriting just a single
function:

.. code:: python3

  from bond.PHP import PHP
  import sys

  php = PHP()
  php.eval_block('include("my_original_program.php");')

  def new_function(arg)
     # do something here
     pass

  php.export(new_function, 'function_to_be_replaced')
  php.call('main', sys.argv)

It turns out that the same approach can be useful to perform remote computation
as well. The wire protocol is simple enough to be extended to any language
supporting an interactive interpreter.


API
===

The ``bond`` class supports the following methods:

``eval(code)``:

  Evaluate and return the value of a *single statement* of code in the interpreter.

``eval_block(code)``:

  Execute a "code" block inside the interpreter. Any construct which is legal
  by the current interpreter is allowed, but the return value may/may not
  contain the result of the last statement.

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
  as "name". Note that "func" must be a function *reference*, not a function
  name.

``proxy(name, other, remote)``:

  Export a function "name" from the current ``bond`` to "other", named as
  "remote". If "remote" is not provided, the same value as "name" is used.

``interact()``:

  Start an interactive session with the underlying interpreter. By default, all
  input lines are executed with bond.eval_block(), which might not output the
  result of the expression. If "!" is pre-pended, execute a single statement
  with bond.eval() instead.

You can construct a ``bond`` by using the appropriate subclass:

.. code:: python

  from bond.<language> import <language>
  interpreter = <language>().


Language support
================

Python:

* Python has no restriction on data types (everything is pickled), so you can
  also transparently send/receive functions.


PHP:

* The PHP's command line and the ``readline`` module needs to be installed for
  the interactive interpreter to work properly. On Debian/Ubuntu, you'll need
  ``php5-cli`` and ``php5-readline``.


Perl:

* The ``JSON`` and ``Data::Dump`` modules are required (``libjson-perl`` and
  ``libdata-dump-perl`` in Debian/Ubuntu).

* There's no distinction between ``eval`` and ``eval_block`` in Perl. Both
  calls accept any number of statements and return the result of the last.

* By default, evaluation is forced in array context. Use the "scalar" keyword
  to coerce the result manually.

* Most, but not all built-in functions are callable directly using
  ``bond.call()`` due to the syntax semantics of Perl: you can only call
  function-like builtins.


Common limitations
==================

Only basic types (booleans, numbers, strings, lists, arrays and
maps/dictionaries) can be transferred between the interpreters. References are
implicitly broken as *objects are transferred by value*.

Calling functions across the bridge is slow due to the serialization, but the
execution speed of the functions themselves is *not affected*. This might be
perfectly reasonable if there are only occasional calls between languages,
and/or the calls themselves take a significant fraction of time.


Authors and Copyright
=====================

| "python-bond" is distributed under GPL2 (see COPYING) WITHOUT ANY WARRANTY.
| Copyright(c) 2014 by wave++ "Yuri D'Elia" <wavexx@thregr.org>.

python-bond's GIT repository is publicly accessible at::

  git://src.thregr.org/python-bond

or at `GitHub <https://github.com/wavexx/python-bond>`_.
