---
name: structured-log-parsing
description: Use when parsing application logs, filtering error levels, and formatting JSON outputs.
---
- Transform service names to lowercase and replace hyphens with underscores.
- Sort error entries strictly by service name ascending, then by timestamp in UTC ascending.
- Include required schema version and generator identifiers in the top-level output object.
