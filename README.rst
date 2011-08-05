===========================================
 f5test2 - A Test Framework for F5 products
===========================================

:Version: 1.0
:Web: http://
:Download: http://
:Source: http://
:Keywords: f5 testing em bvt

--

.. _f5test2-synopsis:

Celery is an open source asynchronous task queue/job queue based on
distributed message passing.  It is focused on real-time operation,
but supports scheduling as well.

Description
===========

F5test2 is a structured framework that makes testing of F5 products easier.
It introduces the following concepts:

- Interfaces: an abstract layer of interactions with different entities
- Commands: a set of Actions focused on one Interface, version agnostic.
- Macros: a complex set of Actions or Commands spanned across one or more Interfaces

Documentation
=============

http://go/indexing

Interfaces
==========

- SSH: Run commands remotely through SSH. File transfers supported as well.
- Shell: For executing local commands on the test runner
- iControl: Access iControl API.
- EM/iControl: Access EM daemon API over icontrol.
- Testopia: Access to Testopia XML RPC interface.
- iRack: Access to iRack REST interface.

Commands
========

- SSH
    - License: Remotely license a device.
    - ScpPut/ScpGet: Fast Upload/Download using SCP. 
    - GetVersion: /VERSION file parser.
    - GetPlatform: /PLATFORM file parser.
    - ParseLicense: bigip.license parser.
    - GetPrompt
    - Reboot
    - Switchboot
    - InstallSoftware: image2disk wrapper.
    - AuditSoftware: Parser for the audit script output.
    - CollectLogs: Tail important log files.
    - FileExists
    - CoresExist
    - RemoveEm: Remove all EM certificates from a target.

- SQL
    - Query: Run SQL queries over a SSH interface.

- TMSH:
    - ListSoftware: Parser for `tmsh list sys software`
    - GetProvision: Parser for `tmsh list sys provision`

- iControl System:
	- GetVersion: returns the version (build is not included by default)
	- GetPlatform: returns the platform ID
	- SetPassword: resets the password of admin/root accounts
	- Reboot
	- HasRebooted
	- IsServiceUp
	- FileExists

- iControl Software:
	- GetSoftwareImage
	- DeleteSoftwareImage
	- InstallSoftware
	- ClearVolume
	- GetSoftwareStatus
	- GetActiveVolume
	- GetInactiveVolume

- iControl Management:
	- GetDbvar
	- IsExpired

- UI Common:
	- Login
	- Screenshot
	- Logout
	- BrowseToTab
	- BrowseTo
    
Macros
======

- install: perform image installs, with or without hotfixes, of any supported version.
- confgen: reconfigure a TMOS based device. Currently up to LTM module. Module specific configuration is not implemented.
- keyswap: swap SSH keys with a target device
- webcert: push the test certificate signed by the internal authority "F5 Test"
- irackprofile: query iRack for static information like IP, hostnames, licenses
- ha: setup HA configurations (currently only CMI is implemented)
- big3dutil: push big3d to all devices requiring it discovered on a given EM
- seleniumrc: start/stop selenium server and/or Xvfb

Nose Plugins
============

- email: send email reports at the end of a test run
- logcollect: collect logs when a test fails
- testconfig: provide access to the global config object
- testopia: sync testplans and create testruns 
 
Installation
============

  python setup.py install

Testing
=======

  python setup.py test

License
=======

F5test is distributed under the terms of the Apache
License, Version 2.0.  See docs/COPYING for more
information.

Credits
=======

F5test has been created with the help of:

- 
