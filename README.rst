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

Table Of content
-----------------

`Installation`_ | `Usage`_ | `Blackd mode`_ | `Pre-commit integration`_ | `Settings`_ | `Code folding`_ | `Sublime Linter integration`_ | `Issues`_ | `Thanks`_ | `Changelog`_ | `Contributing`_ | `Authors`_


Installation
-------------

#. Install `Black`_ min (19.3b0) (if you haven't already)::
   
	   pip install black # Requires python 3.6
       or pip install black[d] # for blackd support

#. In PackageControl just find ``sublack``, and that's it !

or

Without PackageControl  install manually by navigating to Sublime's `Packages` folder and cloning this repository::

      git clone https://github.com/jgirardet/sublack.git

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

* run Black Format All :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Format All`. Run black against each root folder  in a standard way (without taking care of sublack options and configuration). Same thing as running `black .` being in the folder.

* Start Blackd Server :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Start BlackdServer`.

* Stop Blackd Server :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Stop BlackdServer`.


Blackd Mode
------------

Sublack supports blackd. If option `black_use_blackd` is to true, Sublack will use blackd (and not black) according the 'host' and 'port' configuration.

You can run blackd from SublimeText manually via `Start Blackd Server` command or automatically at sublimetext start via setting `black_blackd_autostart` to true.

Blackd server started via SublimeText can be stopped manually via the `Stop Blackd Server` command or automatically at sublime's exit.

Unlike "standalone" blackd, using sublack with blackd will continue to take care of the pyproject file.

Using standard mode ou blackd mode in sublack should always have the same result...or it's a bug :-)

Blackd is faster than Black.

Diff is always run with black.

Pre-commit integration
------------------------

You can choose tu run Black via pre-commit by setting `black_use_precommit` to `true`. Sublack settings will be ignored.

Settings
---------

Sublack will always look for settings in the following order:
 - First in a pyproject.toml file
 - Second in project file : first with sublack prefix then in a subsetting (see Project settings).
 - Then in Users global settings
 - finally in sublack's default settings

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

* black_py36[Deprecated]:
    Force use of python 3.6 only syntax. Default is Black-s default.

* black_target_version:
    Python versions that should be supported by Black's output.

Sublack specifics options
++++++++++++++++++++++++++

* black_command:
    Set custom location. Default = "black".

* black_on_save:
    Black is always run before saving file. Default = false.

* black_log:
    Show non error messages in console. Default = info.

* black_default_encoding:
    Should not be changed. Only needed on some OSX platforms.

* black_use_blackd:
    Use blackd instead of black. Default is false.

* black_blackd_server_host:
    default = "localhost",

* black_blackd_server_port:
    default = "45484"

* black_blackd_autostart:
    Automaticaly run blackd in the background wen sublime starts. default is false.

* black_use_precommit:
    run black via pre-commit hook.

* black_confirm_formatall:
    Popup confirmation dialog before format_all command. default = true.


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

Sublack support use of black configuration in pyproject.toml. Be aware that global/project settings will BE OVERRIDEN by pyproject.toml's settings.
Sublack will look for this file in your `project directory` then in your root folder(s).
See `black about pyproject.toml <https://github.com/ambv/black/#pyprojecttoml>`_ .

Code folding
---------------

Sublack tries to keep code folding as before reformatting. SublimeText only support python3.3 syntax. For newer syntax (ex await/async), you have to set
the `python_interpreter` setting.

.. code-block:: json

    {
    "settings"{
        "python_interpreter: /path/to/my/python/virtualenv/bin/python"
    }
    }


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
* `Martinj Peters <https://github.com/mjpieters>`_


Todo
---------

- cors
- refactor popen



.. _Black : https://github.com/ambv/black 
