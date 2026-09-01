"""Analytics engine (STAGE D/E).

The engine is a pure, deterministic library plus a database-backed runner. It has no
dependency on the React frontend: the same functions are exercised by the HTTP API,
the CLI and the automated test-suite.
"""