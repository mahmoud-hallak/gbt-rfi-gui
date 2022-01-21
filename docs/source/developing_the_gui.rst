.. _DevelopingRFIGUI:

How to Develop With the RFI GUI Project: Conventions for Git
=====

*You do NOT need to do any of this to test -- this is only for development changes*

Get the project
-----

Clone the project

.. code-block::

    git clone /home/gbt2/git/integration-bare/gbt_rfi_query.git

Do not develop on the master branch

There are 2 options
 1. Make a new branch
    ``git checkout -b <new branch name>_dev``
 2. Use the created development branch
    ``git checkout gui_dev``


Make your venv
----

.. code-block::

  # make and source the new venv
    ~gbosdd/pythonversions/3.9/bin/python -m venv <Name>
    source <pathToVenv/Name>/bin/activate

  # install the requirements and the package to your venv
    pip install -U pip setuptools wheel build
    pip install -r requirements.txt
  # install the gbt_rfi_query package to your venv
    pip install -e .
  # install pre-commit to help with git tracking
    pip install pre-commit; pre-commit install


Now you can run your development version of the program by calling gbt-rfi-gui in any location *after sourcing your venv*


Development Changes
-----

Do all development for a single fix then track that change

Find what files have changed

.. code-block::

    git status

Add the changes

.. code-block::

    git add <new/changed files separated by a space>

    git commit -m "<message describing the additions above>"

Pre-commit is being used in this repo, so if there is any failures in the pre-commit stage, either fix them or re-add and commit the automatic changes


Once they are all added, push the changes so others can see them

First, pull to see if others made changes on the dev branch

.. code-block::

    git pull origin gui_dev

Then, push the changes

.. code-block::

   git push origin gui_dev


Others will then be able to see the changes and be able to pull them to use themselves


With any new changes follow the pull,add,commit,push steps again. Do a pull before-hand to make sure there are no new changes before adding your new changes


Release Changes
-------------

How to release changes to production made via the development branch
~~~~~~~~

*Only do this after testing and approval of changes*

.. code-block::

  # You now want to release changes you made via your development branch
  # First you must get onto the master branch
  ## From your dev repo and dev branch
    git checkout master
  # Add your changes
    git merge gui_dev
    git push origin master

The changes are available to the release area, but they are not being used

Go to the release area and update the repo

.. code-block::

    cd /home/gbt1/gbt_rfi_gui/gbt_rfi_query
    git pull origin master

Now the changes are live in production
