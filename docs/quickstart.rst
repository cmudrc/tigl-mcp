Quickstart
==========

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

   tigl-mcp-server --transport stdio

Inspect a non-blocking HTTP configuration example:

.. code-block:: bash

   PYTHONPATH=src python3 examples/server/http_launch_config.py

Current capability notes
------------------------

- The package currently uses deterministic CPACS/TiGL stand-ins from
  ``tigl_mcp_server.cpacs_stubs``.
- Output schemas and tool names are stable.
- Geometry numbers are intentionally simplified to keep local development and CI
  deterministic.
