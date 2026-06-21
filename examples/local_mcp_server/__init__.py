"""A small local MCP server for end-to-end smoke testing of the platform.

See README.md. The pure request-parsing logic lives in ``tags.py`` (no MCP
imports, fully unit-testable); ``server.py`` wires it into a low-level MCP
server served over Streamable HTTP.
"""
