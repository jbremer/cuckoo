===============
Guest Auxiliary
===============

Guest auxiliary modules are modules that are uploaded to the guest
and started each time a new Cuckoo analysis starts. These modules are initialized and started before the submitted target to be analyzed is started.

Each of the auxiliary has a specific task to complete before or during a Cuckoo analysis.


Human behavior simulation (Windows)
===================================

Option key: ``human``
The human behavior simulation or human module's task is to simulate
simple human actions. It can perform a set of actions that can be categorized
as small or large actions. 

Each action has a name that can be used to either enable it or disable it during an analysis.
To disable a small action, add the option: ``human.<action name>=0``. To enable a large action, add the option
``human.actions=<action name>``

Small actions
-------------

Small actions are actions that are always executed during a Cuckoo analysis.
These actions run every few seconds. The currently existing small actions are:

- **Mouse movement**

Simulates mouse movement. The mouse is moved to a different spot on the screen.

Action name: ``move_mouse``

- **Mouse clicking**

Simulates mouse clicking. The clicking will occur if the position at which the cursor is at that moment is not a window of a type that it ignores.

Action name: ``click_mouse``

- **Window handling/button clicking**

Searches all currently opened windows for windows with titles that match rules that it has. These rules define what should be done when it encounters such a window.

Action name: ``click_buttons``

A window title can be used to trigger one of 3 types of actions:
	- Closing the window
	- Clicking a specific button
	- A custom action (pointer to a function to execute)

If no matching rule is found for a window title, the window's buttons
will be matched against a list of buttons that should be clicked. If any match is found, this button will be clicked.

To add or edit the rules of how specific windows should be handled. Edit the ``WindowHandler`` class in the `Human module <https://github.com/cuckoosandbox/cuckoo/blob/master/cuckoo/data/analyzer/windows/modules/auxiliary/human.py>`_.

	
Large actions
-------------

These actions are action that are supposed to simulate a human using the analysis machine. It can be 
useful for longer analysis in which the machine should not be idle.

Large actions only get executed if the human module is told to do so. This can be done by supplying it with either a human schedule name or a specific action to execute through the analysis options. Actions either run until they have finished, or it is possible to specific an approximite time how long they should run (in minutes).

Types of supported actions:

**Macro playing**

Executes a previously recorded macro. See (TODO ADD LINK) for information on how to record macros for Cuckoo.

Action name: ``playmacro``

**Using wordpad**

Opens Wordpad on Windows and starts writing paragraphs of text.

Action name: ``wordprocessor``
	
Supported options:
	
- ``min`` - The minimum amount of minutes it should run each time it is executed
- ``max`` - The maximum amount of minutes it should run each time it is executed

**Browsing a webpage**

Simulates reading a webpage. Opens Internet explorer for a specified page and slowly scrolls over the page.

Action name: ``browsewebsite``

Supported options:
	
- ``min`` - The minimum amount of minutes it should run each time it is executed
- ``max`` - The maximum amount of minutes it should run each time it is executed

Data options:
- ``url`` - Specific the url that should be opened

**Using a calculator**

Open the Windows calculator and uses it to calculate something.

Action name: ``usecalculator``

**Doing nothing**

Performs no action at all/be idle. This can be used to make the simulation more realistic by
adding moments where nothing it happening at all.

Action name: ``donothing``

- ``min`` - The minimum amount of minutes it should run each time it is executed
- ``max`` - The maximum amount of minutes it should run each time it is executed
