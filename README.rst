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

Global settings
*****************
Preferences -> Package Settings -> sublack -> settings : 

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


Project settings
*******************

Just add sublack as prefix (recommended):

.. code-block:: json

    {
    "settings":{
    	"sublack.black_on_save": true
    	}
    }

A sublack subsettings is still possible:

.. code-block:: json

    {
    "settings":{
    	"sublack":{
    		"black_on_save": true
    		}
    	}
    }

Issues
---------

If there is something wrong with this plugin, `add an issue <https://github.com/jgirardet/sublack/issues>`_ on GitHub and I'll try to address it.


Thanks
----------

This plugin is very inspired by the very good `PyYapf <https://github.com/jason-kane/PyYapf>`_ Plugin. Thanks to Jason Kane.

Changelog
-----------

see `install.txt <messages/install.txt>`_ 

Contributing
--------------

* remove sublack via Package Control.
* fork sublack
* clone your sublack fork  to your Packages folder (Preferences -->  Browse Packages...).
* install UnitTesting in Package Control
* adding a test for new features or bugfix is really nice	 if you can.
* add your name to Authors in readme.

Authors
---------

Laboriously coded by Jimmy Girardet

contributions by:

* `nicokist <https://github.com/nicokist>`_
* `mschneiderwind <https://github.com/mschneiderwind>`_
* `catch22 <https://github.com/catch22>`_
* `Thom1729  <https://github.com/Thom1729>`_
* `Jacobi Petrucciani  <https://github.com/jpetrucciani>`_
* `Herr Kaste <https://github.com/kaste>`_ 




.. _Black : https://github.com/ambv/black 