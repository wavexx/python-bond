================
 python ``bond``
================
Ambivalent bonds between Python and other languages
---------------------------------------------------

.. contents::

The Python module ``bond`` supports transparent remote/recursive evaluation
between Python and another interpreter through automatic call serialization.


A ``PHP`` example
=================

.. code:: python3

  >>> # Let's bond with a PHP interpreter
  >>> from bond.PHP import PHP
  >>> php = PHP()
  >>> php.eval('echo "Hello world!\n";')
  Hello world!

  >>> # Make an expensive split function using PHP's explode
  >>> split = php.callable('explode')
  >>> split('=', "Mind=blown!")
  [u'Mind', u'blown!']

  >>> # Call Python from PHP
  >>> def call_me():
  ...     print("Hi, this is Python talking!")
  >>> php.export(call_me, 'call_me')
  >>> php.eval('call_me();')
  Hi, this is Python talking!

  >>> # Bridge two worlds!
  >>> remote_php = PHP('ssh remote php -a')
  >>> php.eval('function local_php() { echo "Hi from " . system("hostname") . "!"; }')
  >>> php.proxy('local_php', remote_php)
  >>> remote_php.eval('local_php();')
  Hi from localhost!


Limitations
===========

Only basic types (booleans, numbers, strings, lists, arrays and
maps/dictionaries) can be transferred between the interpreters. References are
implicitly broken as objects are transferred by *value*.

The PHP's ``readline`` module needs to be installed for the interactive
interpreter to work properly.

Calling functions across the bridge is slow, but the execution speed of
function itself is *not affected*. This might be perfectly reasonable if there
are only occasional calls between languages, and the calls themselves take a
significant fraction of time. Calling functions recursively between
interpreters though might be prohibitive.


Why?
====

I needed ``bond`` for refactoring, mostly. It lets you rewrite your program
incrementally, while still executing all your existing code unchanged:

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


Authors and Copyright
=====================

| "python-bond" is distributed under GPL2 (see COPYING) WITHOUT ANY WARRANTY.
| Copyright(c) 2014 by wave++ "Yuri D'Elia" <wavexx@thregr.org>.

python-bond's GIT repository is publicly accessible at::

  git://src.thregr.org/python-bond

or at `GitHub <https://github.com/wavexx/python-bond>`_.
