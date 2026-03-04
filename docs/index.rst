tigl-mcp
========

`tigl-mcp` exposes deterministic, JSON-friendly CPACS/TiGL tools through an MCP
server surface. The current implementation uses lightweight stubs so the
development and test workflows stay stable without external geometry runtimes.

Get Started Fast
----------------

If you are new to the project, this is the fastest path:

1. Create a virtual environment and install the local toolchain.
2. Run the test suite once.
3. Start the MCP server over stdio.

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   make dev
   make test
   tigl-mcp-server --transport stdio

For the fuller setup flow, go straight to :doc:`quickstart`.

.. toctree::
   :maxdepth: 1

   Quickstart <quickstart>
   Python API <api>
   Runtime Guides <reference/index>
   Examples <examples/index>
