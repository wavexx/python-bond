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


A simple  example
=================

.. code:: python3

  >>> # Let's bond with a PHP interpreter
  >>> from bond.PHP import PHP
  >>> php = PHP()
  >>> php.eval('echo "Hello world!\n";')
  Hello world!

  >>> # Make an expensive split function using PHP's explode
  >>> split = php.callable('explode')
  >>> split(' ', "Hello world splitted by PHP!")
  [u'Hello', u'world', u'splitted', u'by', u'PHP!']

  >>> # Call Python from PHP
  >>> def call_me():
  ...     print("Hi, this is Python talking!")
  >>> php.export(call_me, 'call_me')
  >>> php.eval('call_me();')
  Hi, this is Python talking!

  >>> # Use some remote resources
  >>> remote_php = PHP('ssh remote php -a')
  >>> remote_php.eval('function call_me() { echo "Hi from " . system("hostname") . "!"; }')
  >>> remote_php.eval('call_me();')
  Hi from remote!

  >>> # Bridge two worlds!
  >>> from bond.Perl import Perl
  >>> perl = Perl()
  >>> php.proxy('explode', perl)
  >>> # note: explode is now available to Perl
  >>> perl.eval('explode("=", "Mind=blown!");')
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
  php.eval('include("my_original_program.php");')

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

  Execute "code" (which is a normal string) inside the interpreter within the
  main scope (if possible). Any construct which is legal by the current
  interpreter is allowed.

``eval_block(code)``:

  Execute "code" (which is a normal string) inside the interpreter, but within
  an anonymous block. Local variables will be not visible to the main code,
  unless they are explicitly declared as global.

``close()``:

  Terminate the communication with the interpreter.

``call(name, *args)``:

  Call a function "name" in the interpreter using the supplied list of
  arguments \*args. The arguments are automatically converted to their other
  language's counterpart. The return value is captured and converted back to
  Python as well.

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

You can construct a ``bond`` by using the appropriate subclass:

.. code:: python

  from bond.<language> import <language>
  interpreter = <language>().


Language support
================

PHP:

* The PHP's command line and the ``readline`` module needs to be installed for
  the interactive interpreter to work properly. On Debian/Ubuntu, you'll need
  ``php5-cli`` and ``php5-readline``.

* A syntax error will not currently return a proper exception.


Perl:

* The ``perlsh`` interpreter is used, which is installed by the
  `Term::ReadLine::Gnu package
  <https://metacpan.org/release/Term-ReadLine-Gnu>`_ (also available in
  Debian/Ubuntu as ``libterm-readline-gnu-perl``).

* There's no distinction between ``eval`` and ``eval_block`` in Perl. Both
  calls execute the evaluated code in an anonymous scope. If you need to
  *create* global variables, you need to use a qualified prefix.

* Not all built-in functions are callable directly using ``bond.call`` due to
  the syntax semantics of Perl: you can only call function-like builtins.


Common limitations
==================

Only basic types (booleans, numbers, strings, lists, arrays and
maps/dictionaries) can be transferred between the interpreters. References are
implicitly broken as *objects are transferred by value*.

Calling functions across the bridge is slow, but the execution speed of
function itself is *not affected*. This might be perfectly reasonable if there
are only occasional calls between languages, and the calls themselves take a
significant fraction of time. Calling functions recursively between
interpreters though might be prohibitive.


Authors and Copyright
=====================

| "python-bond" is distributed under GPL2 (see COPYING) WITHOUT ANY WARRANTY.
| Copyright(c) 2014 by wave++ "Yuri D'Elia" <wavexx@thregr.org>.

python-bond's GIT repository is publicly accessible at::

  git://src.thregr.org/python-bond

or at `GitHub <https://github.com/wavexx/python-bond>`_.
