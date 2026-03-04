Quickstart
==========

Fast path
---------

If you want to get moving immediately, use this minimal setup:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   make dev
   tigl-mcp --transport stdio

Then come back to the sections below for validation, examples, and workflow
details.

Setup
-----

Create a local virtual environment and install the development dependencies:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   make dev

Run the default quality gates:

.. code-block:: bash

   make test
   make ci

Start the server
----------------

Run the CLI over stdio:

.. code-block:: bash

   tigl-mcp --transport stdio

Inspect a non-blocking HTTP configuration example:

.. code-block:: bash

   PYTHONPATH=src python3 examples/server/http_launch_config.py

Current capability notes
------------------------

- The package currently uses deterministic CPACS/TiGL stand-ins from
  ``tigl_mcp.cpacs_stubs``.
- Output schemas and tool names are stable.
- Geometry numbers are intentionally simplified to keep local development and CI
  deterministic.
