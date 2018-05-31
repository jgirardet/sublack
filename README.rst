===============================
sublack
===============================


`Black`_ integration for SublimeText


* License : GNU General Public License v3 or later (GPLv3+) 
* Source: https://github.com/jgirardet/sublack



Usage
--------

* Run Black on current file:
	Press `Ctrl-Alt-F` to format the entire file.
	You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Format file`.


* Run Black with --diff:
	Press `Ctrl-Alt-Shift-F` will show diff in a new tab.
	You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Diff file`.



Installation
-------------

#. Install `Black`_ (if you haven't already)::
   
	   pip install black # Requires python 3.6

#. Waiting for PackageControl Entry, install manually by navigating to Sublime's `Packages` folder and cloning this repository::

      git clone https://github.com/jgirardet/sublack.git

.. #.  In PackageControlFind "sublack", and that's it !

Settings
---------

* black_command:
	Set custom location. Default = "black".

* on_save:
	Black is always run before saving file. Default = false.

* line_length:
	Set custom line length option used by `Black`_. Default = null which lets black default.

* fast:
	Black fast mode. default is false.

* debug:
	Show non error messages in console. Default = false. Error messages are always shown in console.


Issues
---------

If there is something wrong with this plugin, `add an issue <https://github.com/kgirardet/sublack/issues>`_ on GitHub and I'll try to address it.


Thanks
----------

This plugin is very inspired by the very good `PyYapf <https://github.com/jason-kane/PyYapf>`_ Plugin. Thanks to Jason Kane.

Changelog
-----------

1.4.0:
	- add black_diff command
	- add black_diff keymap
	- add fast setting
	- refactor code
	- do nothing if already formated and show "already formated" in statusbar
1.3.4:
	- Format sublack with Black (#8, thanks to `mschneiderwind <https://github.com/mschneiderwind>`_)
1.3.3:
	- Fix encoding if not given by SublimeText.
1.3.2:
	- BugFix : Click library Bug with locale under OSX
1.3.1:
	- update README
1.3.0:
	- use '-' argument to format inline document wihout saving it
	- consequently post-save became pre-save
	- line_length typo in settings
	- add log
1.2.0:
	- add error handling (thanks to `nicokist <https://github.com/nicokist>`_)
1.1.0:
	- add line_length option
1.0.0:
	- make plugin
	- add on_save option

.. _Black : https://github.com/ambv/black 