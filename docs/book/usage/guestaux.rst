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

Executes a previously recorded macro. See the `Macro recording (Windows)`_  section for information on how to record macros for Cuckoo.

Action name: ``playmacro``

Data options:
- ``name`` - A name of the macro to run

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

Human behavior schedule
=======================

The human behavior module needs a schedule to know what large actions to execute, as stated in the `Large actions`_ section.

There are two types of schedules you can provide the human module with. A sequential and a schedule used to generate a queue of random actions. The latter
is meant for long analyses in which it is required to fill the total analysis with simulated behavior.

The human schedules are YAML files and should be placed in ``$CWD/human``.

When submitting a new task, a schedule can be activated by passing the option: ``human.schedule=<schedulename>``. Pass the schedule
without the file extension. An example of passing a schedule would be: ``human.schedule=default`` or ``human.schedule=sequential``

Sequential schedule
-------------------

A sequential schedule contains a list of actions that should be executed in order. Only the specified actions will executed
by the human module.

Below is an example of ``$CWD/human/sequential.yaml``

.. literalinclude:: ../../../cuckoo/data/human/sequential.yaml
    :language: typoscript
	
Random queue schedule
---------------------

A random queue schedule contains actions seperated into two categories: ``tasks`` and ``recreation`` .
The actions in both of these categories will be used to randomly generated a queue of actions that will fill the entire
time of an analysis.

For each action, a ``chance`` key should be specified. The value is used to increase/decrease the chance the action is queued.
This can contain a number between ``0.1`` and ``0.9``.

Lastly, this type of schedule should also have a ``productivity`` key. This key determines how likely it is from ``0.1`` to ``0.9`` that
a module from the ``tasks`` list is queued, instead of a module from ``recreation``. This can be used to simulate more realistic working behavior.

Below is an example of ``$CWD/human/default.yaml``
	
.. literalinclude:: ../../../cuckoo/data/human/default.yaml
    :language: typoscript

	
Macro recording (Windows)
=========================

The macro recording module assists in recording macros for Cuckoo to use. The macros recorded here can be later used by the human behavior module.

To start a macro recording, submit a recording task with the ``cuckoo submit`` tool. See :doc:`submit` for more information on this tool.
A macro recording can be submitted with: ``cuckoo submit --record-macro <macroname> --machine <machinename>``. This will create a macro recording task.

When your Cuckoo instance is started, this task will be started first. To be able to get into the machine, RDP will have to be activated. If Virtualbox is used, this can be achieved with the command ``vboxmanage controlvm <vmname> vrde on``. This will enable VRDP on port 3389.

To record macros, Cuckoo uses `Perfect automation <http://www.perfectautomation.com/>`_. This software is automatically downloaded, uploaded to, and started in the analysis machine.

When in the machine, you can almost immediately start the recording. The given macro name will already be filled in. Make sure to set the ``File`` setting to
``Executable file (silent) (*.exe)`` before starting the recording. See an example of the correct settings below.

    .. image:: ../_images/screenshots/macrosettings.png
        :align: center
		
When ready to record the macro, hit the ``Record`` button. After this, take your time to perform the actions that should be recorded.  For optinal recording results, move the mouse slightly slower than you normally would. When finished recording, hit the ``Stop`` button at the bottom right of the screen.

    .. image:: ../_images/screenshots/macrostop.png
        :align: center

After hitting stop, the macro exe will automatically be uploaded back to the Cuckoo host, where it will be made available for use as soon as the macro recording task
is finished. It is possible to record multiple macros in a single session. Just be sure to change the ``Name`` field in the recorder.
