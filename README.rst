.. image:: https://travis-ci.org/jgirardet/sublack.svg?branch=master
    :target: https://travis-ci.org/jgirardet/sublack


===============================
sublack
===============================


`Black`_ integration for SublimeText


* License : GNU General Public License v3 or later (GPLv3+) 
* Source: https://github.com/jgirardet/sublack



Usage
--------

* Run Black on current file:
	Press `Ctrl-Alt-B` to format the entire file.
	You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Format file`.


* Run Black with --diff:
	Press `Ctrl-Alt-Shift-B` will show diff in a new tab.
	You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Diff file`.




Installation
-------------

#. Install `Black`_ (if you haven't already)::
   
	   pip install black # Requires python 3.6

#. In PackageControl just find ``sublack``, and that's it !

or

Without PackageControl  install manually by navigating to Sublime's `Packages` folder and cloning this repository::

      git clone https://github.com/jgirardet/sublack.git

Settings
---------

* black_command:
	Set custom location. Default = "black".

* black_on_save:
	Black is always run before saving file. Default = false.

* black_line_length:
	Set custom line length option used by `Black`_. Default = null which lets black default.

* black_fast:
	Black fast mode. default is false.

* black_debug_on:
	Show non error messages in console. Default = false. Error messages are always shown in console.

* black_default_encoding:
	Should not be changed. Only needed on some OSX platforms.


Issues
---------

If there is something wrong with this plugin, `add an issue <https://github.com/jgirardet/sublack/issues>`_ on GitHub and I'll try to address it.


Thanks
----------

This plugin is very inspired by the very good `PyYapf <https://github.com/jason-kane/PyYapf>`_ Plugin. Thanks to Jason Kane.

Changelog
-----------

see messages/install.txt

.. _Black : https://github.com/ambv/black 
