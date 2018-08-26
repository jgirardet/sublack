.. image:: https://travis-ci.org/jgirardet/sublack.svg?branch=master
    :target: https://travis-ci.org/jgirardet/sublack

.. image:: https://ci.appveyor.com/api/projects/status/ffd44ndqx713yuhd/branch/master?svg=true
    :target: https://ci.appveyor.com/project/jgirardet/sublack

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

* Toggle Black on save for current view :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Toggle black on save for current view`.

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

Black specifics options
++++++++++++++++++++++++


* black_line_length:
    Set custom line length option used by `Black`_. Default = null which lets black default.

* black_fast:
    Black fast mode. default is false.

* black_skip_string_normalization:
    Don't normalize string quotes or prefixes. Default = false.

* black_exclude:
    Regex matching excluded path. Default is Black's default.

* black_include:
    Regex matching included path. Default is Black's default.

* black_py36:
    Force use of python 3.6 only syntax. Default is Black-s default.

Sublack specifics options
++++++++++++++++++++++++++

* black_command:
    Set custom location. Default = "black".

* black_on_save:
    Black is always run before saving file. Default = false.

* black_debug_on:
    Show non error messages in console. Default = false. Error messages are always shown in console.

* black_default_encoding:
    Should not be changed. Only needed on some OSX platforms.

* black_use_blackd:
    Use blackd instead of black. Default is false.

* blackd server host:
    default = "localhost",

* blackd server port:
    default = "45484"

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

pyproject.toml settings
***************************

sublack support use of black configuration in pyproject.toml. Be aware that global/project settings will override pyproject.toml's settings.
See `black about pyproject.toml <https://github.com/ambv/black/#pyprojecttoml>`_ .

Sublime Linter integration
----------------------------

You can install `SublimeLinter-addon-black-for-flake <https://github.com/kaste/SublimeLinter-addon-black-for-flake>`_. The plugin will auto configure flake8 and mute all warnings black can actually fix.


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
* Package Control: Satisfy Dependencies (install requests)
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
