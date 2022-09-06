<h1 align="center">
<!--   <br>
  <a href="http://www.amitmerchant.com/electron-markdownify"><img src="https://raw.githubusercontent.com/amitmerchant1990/electron-markdownify/master/app/img/markdownify.png" alt="Sublack4" width="200"></a>
  <br> -->
  Sublack4
  <br>
</h1>

<h2 align="center">Black integration for SublimeText4</a>.</h2>

<p align="center">
  <a href="https://github.com/munkybutt/sublack/blob/master/LICENSE.md">
    <img src="https://img.shields.io/github/license/munkybutt/sublack?style=for-the-badge"
  </a>
  <a href="https://github.com/munkybutt/sublack/releases/tag/v0.3.0">
    <!-- <img src="https://badge.fury.io/gh/munkybutt%2Fsublack.svg?style=for-the-badge"> -->
    <img src="https://img.shields.io/github/release/munkybutt/sublack?style=for-the-badge&include_prereleases">
  </a>
  <a href="https://saythanks.io/to/munkybutt">
      <img src="https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg?style=for-the-badge">
  </a>
  <a href="https://www.paypal.me/munkybuttballs">
    <img src="https://img.shields.io/badge/$-donate-ff69b4.svg?maxAge=2592000&amp;style=for-the-badge">
  </a>
</p>


* Source: https://github.com/munkybutt/sublack

---------
<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#blackd-mode">Blackd Mode</a> •
  <a href="#pre-commit-integration">Pre-Commit Integration</a> •
  <a href="#settings">Settings</a> •
  <a href="#code-folding">Code Folding</a> •
  <a href="#sublime-linter-integration">Sublime Linter Integration</a> •
  <a href="#changelog">Changelog</a> •
  <a href="#how-to-contribute">How to Contribute</a> •
  <a href="#authors">Authors</a> •
  <a href="#thanks">Thanks</a> •
  <a href="#personal-info">Personal Info</a>
</p>

---------


Installation
------------

Use Package Control to search for: ``sublack4`` and install.

or

Without PackageControl install manually by navigating to Sublime's `Packages` folder and cloning this repository:

``git clone https://github.com/munkybutt/sublack.git``


(Optional) `sublack4` includes black and black[d] but if you wish to install your own version:

- `Black`_ min (19.3b0)
- pip install black # Requires python 3.6
- or pip install black[d] # for blackd support

Usage
-----

* Run Black on the current file:
    Press `Ctrl-Alt-B` to format the entire file.
    You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Format file`.


* Run Black with --diff:
    Press `Ctrl-Alt-Shift-B` will show diff in a new tab.
    You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Diff file`.

* Toggle Black on save for current view :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Toggle black on save for current view`.

* run Black Format All :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Format All`. Run black against each root folder in a standard way (without taking care of sublack options and configuration). Same thing as running `black .` being in the folder.

* Start Blackd Server :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Start BlackdServer`.

* Stop Blackd Server :
    Press `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select `Sublack: Stop BlackdServer`.


Blackd Mode
-----------

Sublack supports blackd. If option `black_use_blackd` is to true, Sublack will use blackd (and not black) according to the 'host' and 'port' configuration.

You can run blackd from SublimeText manually via `Start Blackd Server` command or automatically at SublimeText start via setting `black_blackd_autostart` to true.

Blackd server started via SublimeText can be stopped manually via the `Stop Blackd Server` command or automatically at sublime's exit.

Unlike "standalone" blackd, using sublack with blackd will continue to take care of the pyproject file.

Using standard mode ou blackd mode in sublack should always have the same result...or it's a bug :-)

Blackd is faster than Black.

Diff is always run with black.


Pre-commit Integration
----------------------

You can choose to run Black via pre-commit by setting `black_use_precommit` to `true`. Sublack settings will be ignored.


Settings
--------

Sublack will always look for settings in the following order:
 - First in a pyproject.toml file
 - Second in the project file: first with sublack prefix then in a subsetting (see Project settings).
 - Then in Users global settings
 - Finally in Sublack's default settings


Global settings
***************
Preferences -> Package Settings -> sublack -> settings :


Black specifics options
+++++++++++++++++++++++

* black_line_length:
    Set custom line length option used by `Black`_. Default = null which lets black default.

* black_fast:
    Black fast mode. default is false.

* black_skip_string_normalization:
    Don't normalize string quotes or prefixes. Default = false.

* black_py36[Deprecated]:
    Force use of python 3.6 only syntax. The default is Black-s default.

* black_target_version:
    Python versions that should be supported by Black's output. You should enter it as a list ex : ["py37"]


Sublack specifics options
+++++++++++++++++++++++++

* black_command:
    Set custom location. Default = "black".

* black_on_save:
    Black is always run before saving the file. Default = false.

* black_log:
    Show non error messages in console. Default = info.

* black_default_encoding:
    Should not be changed. Only needed on some OSX platforms.

* black_use_blackd:
    Use blackd instead of black. Default = false.

* black_blackd_server_host:
    default = "localhost",

* black_blackd_port:
    default = "45484"

* black_blackd_autostart:
    Automatically run blackd in the background wen sublime starts. default is false.

* black_use_precommit:
    run black via pre-commit hook.

* black_confirm_formatall:
    Popup confirmation dialog before format_all command. default = true.


Project settings
****************

Just add sublack as prefix (recommended):

.. code-block:: json

    {
        "settings": {
            "sublack.black_on_save": true
        }
    }

A sublack subsettings is still possible:

.. code-block:: json

    {
        "settings": {
            "sublack": {
                "black_on_save": true
            }
        }
    }


pyproject.toml settings
***********************

Sublack supports the use of black configuration in pyproject.toml. Be aware that global/project settings will BE OVERRIDDEN by pyproject.toml's settings.
Sublack will look for this file in your `project directory` then in your root folder(s).
See `black about pyproject.toml <https://github.com/ambv/black/#pyprojecttoml>`_ .


Code folding
------------

Sublack attempt to keep code folding intact, but this functionality is unpredictable.


Sublime Linter integration
--------------------------

You can install `SublimeLinter-addon-black-for-flake <https://github.com/kaste/SublimeLinter-addon-black-for-flake>`_. The plugin will auto-configure flake8 and mute all warnings black can actually fix.


Changelog
---------

see `install.txt <messages/install.txt>`_


How to Contribute
------------

* Remove sublack via Package Control.
* Fork sublack
* Clone your sublack fork to your Packages folder (Preferences -->  Browse Packages...).
* Preferences --> Package Control: Satisfy Dependencies (install requests)
* Install UnitTesting in Package Control
* Adding a test for new features or bugfix is really nice if you can.
* Add your name to Authors in the readme.


Authors
-------
Original Author: Jimmy Girardet

New Author: Shea Richardson

Contributions by:

* `nicokist <https://github.com/nicokist>`_
* `mschneiderwind <https://github.com/mschneiderwind>`_
* `catch22 <https://github.com/catch22>`_
* `Thom1729  <https://github.com/Thom1729>`_
* `Jacobi Petrucciani  <https://github.com/jpetrucciani>`_
* `Herr Kaste <https://github.com/kaste>`_
* `Martinj Peters <https://github.com/mjpieters>`_
* `Cyrus Yip <https://github.com/realcyguy>`_
* `Georgios Samaras <https://github.com/gsamaras>`_

Thanks
------

This plugin is very inspired by the very good `PyYapf <https://github.com/jason-kane/PyYapf>`_ Plugin. Thanks to Jason Kane.


## Personal Info
> Webbie [techanimdad.com](https://techanimdad.com) &nbsp;&middot;&nbsp;
> GitHub [@munkybutt](https://github.com/munkybutt)

