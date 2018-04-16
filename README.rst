===============================
sublack
===============================


`Black`_ integration for SublimeText


* License : GNU General Public License v3 or later (GPLv3+) 
* Source: https://github.com/jgirardet/sublack



Usage
--------

By default, press `Ctrl-Alt-F` to format the entire document.
You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `sublack: Format file`.

To automatically run Black on the current document before saving, use the `on_save` setting.

.. note:: Be aware that the current file is automatically saved after reformatting




Installation
-------------

#. Install Black (if you haven't already)::
   
	   pip install black # Requires python 3.6

.. #.  Install Sublime Package Control by following the instructions [here](https://packagecontrol.io/installation) (if you haven't already).

.. # `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and choose "Package Control: Install Package".

.. #.  Find "PyYapf Python Formatter" in the list (type in a few characters and you should see it).

#. Waiting for PackageControl Entry, install manually by navigating to Sublime's `Packages` folder and cloning this repository::

      git clone https://github.com/jgirardet/sublack.git

Issues
---------

If there is something wrong with this plugin, `add an issue <https://github.com/kgirardet/sublack/issues>`_ on GitHub and I'll try to address it.


Thanks
----------

This plugin is very inspired by the very good `PyYapf <https://github.com/jason-kane/PyYapf>`_ Plugin. Thanks to Jason Kane.

Changelog
-----------
1.0.0:
	- first try

_`Black`: https://github.com/ambv/black 