===============================
sublack
===============================


`Black`_ integration for SublimeText


* License : GNU General Public License v3 or later (GPLv3+) 
* Source: https://github.com/jgirardet/sublack



Usage
--------

* Default:
	Press `Ctrl-Alt-F` to format the entire file.
	You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `sublack: Format file`.

* On Save:
	To automatically run Black on the current file before saving, use the `"on_save"` setting.

* Line Length:
	You can specify `"line_length"` used by `Black`_ in settings.

* SublimeText limitation:
	Actually Python 3.6 is not supported by SublimeText, so the Black API can't be used for now. This implies that we have to use the **black** command instead (which is good also) and then apply the changes to a  **saved file** only. So every time you run **sublack**, the file is automatically saved.




Installation
-------------

#. Install Black (if you haven't already)::
   
	   pip install black # Requires python 3.6

#. Waiting for PackageControl Entry, install manually by navigating to Sublime's `Packages` folder and cloning this repository::

      git clone https://github.com/jgirardet/sublack.git

#. Add **Black** commad to settings::
   
	
	{
	"black_command": "/my/path/to/bin/black",
	}
.. #.  In PackageControlFind "sublack", and that's it !


Issues
---------

If there is something wrong with this plugin, `add an issue <https://github.com/kgirardet/sublack/issues>`_ on GitHub and I'll try to address it.


Thanks
----------

This plugin is very inspired by the very good `PyYapf <https://github.com/jason-kane/PyYapf>`_ Plugin. Thanks to Jason Kane.

Changelog
-----------

1.1.0:
	- add line_length option
1.0.0:
	- make plugin
	- add on_save option

_`Black`: https://github.com/ambv/black 