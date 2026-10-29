# Documentation review remediation

The October 28, 2026 review was read in full before editing. Its recommendations
were checked against the local implementations across core, Equipment, Shared,
Messaging, Host, and GUI. Changes update documentation, API docstrings, example
configuration paths, and documentation generation. Public APIs and runtime
behavior are preserved.

## Changes by review area

| Review area | Applied changes |
| --- | --- |
| Core first use and navigation | Working Shared-based quickstart with PASS and FAIL outcomes, comment-only config, actual summary fields, standalone file instructions, task directory, and separate learning/reference/development navigation. |
| Script authoring and parameters | Moved parameter details into a dedicated guide with selection precedence and resolved-value examples. Moved import caching into a suite import guide. Explained keys before their use. |
| Evidence and failure behavior | Split the test-author contract from evidence implementation details. Documented measurement identity, collisions across instrument IDs, latest-key Shared lookup, continuation, optional failures, BLOCKED checks, and summary/SQLite examples. |
| Configuration | Led with single/multiple rows and IDs, moved schema/store internals into developer guidance, added CLI-pinning/reload scenarios, and distinguished standard TOML booleans and plugin/core validation. |
| Execution and suites | Added task-to-mode choices and offline replay. Moved setup/teardown result semantics near the first suite example. Explained slot/process state, connection closure, timing overrun, and local cleanup versus teardown. |
| Results | Added purpose-to-file navigation and SQL against the actual measurement and verification schemas. Measurements deliberately have no optional column. |
| Equipment | Guides precede module-level API navigation. Added transport/selection guidance and a representative model/capability matrix linked to the detailed inventory. Completed live PSU/DMM configuration, cleanup, and inspection instructions; retained existing scope, load, RF, VNA, and synchronization recipes. |
| Shared | Added task/verification selection and small independently runnable numeric, log, and new-file recipes. Kept the comprehensive demonstration. Moved historical release prose to a linked development page. |
| Messaging | Split HTTP, pub/sub, SSH, and transfer workflows. Added bounded MQTT/ZMQ readiness-probe sequences using public listener hooks. Moved private MessagePump material to development guidance. Explained host-key policy and protocol/background failure categories. |
| Host | Clarified that APIs inspect the machine running Colosseum. Added config.host.example.toml while retaining the historical filename. Split existing-process and self-contained sampling. Highlighted byte-rate units in guides and relevant API entries. |
| GUI | Distinguished the desktop runner from application automation. Added driver/platform selection, locator examples, waiting/focus/scaling guidance, and diagnostics. Corrected smoke-example paths and explained pinned config. Moved bridge implementation details to development guidance. |
| Reference consistency | Filled parameter-description gaps in public API source docstrings and generated SCPI/verifier documentation. Included previously omitted camera and analyzer reference modules. Rendered framework controls consistently without changing signatures. Builds now reject undocumented parameters on decorated APIs. |
| Editorial and maintenance | Removed promotional wording, shortened repeated artifact inventories, separated release history, fixed broken developer links, and recorded writing/example standards in docs/README.md. Plugin patch versions follow their local AGENTS.md rules. |

## Implementation details that changed the suggested wording

The review's snippets were proposals, not verified contracts. Shared's numeric
quickstart signatures were confirmed by execution. Optional measurement errors
store null ERROR values but have no optional database column. A dependent
required Shared field check records FAIL in the demonstrated case.

SSH `auth="auto"` accepts unknown host keys even when a `known_hosts` file is
configured. A populated file checks known identities but does not reject every
unknown identity. The plugin currently has no strict-key mode combined with
ordinary key/password authentication; `auth="none"` also changes authentication
requirements. The guide describes that limitation instead of implying that
setting a file alone enables strict enrollment.

The extracted keyword-only separator wording is an accessibility tooltip on
the signature's `*`, not an extra public parameter. Rendered pages show the star
normally. Type hints remain in signatures, and decorator-owned parameter
descriptions are supplied by the documentation renderer.

## Validation

- All six HTML sites built with Sphinx 8.2.3 and warnings treated as errors.
- Plugin suites: Equipment 505, Shared 151, Messaging 106, Host 68, GUI 25 passed.
- Core's documented numeric/text procedure and replay integration test passed.
- Standalone quickstart PASS/FAIL, parameter FAIL/PASS, prior-evidence replay,
  Shared recipes, plugin introductions, simulated Equipment/RF/Messaging/GUI
  procedures, Host prerequisites, and optional-failure demonstrations executed.
- SQL queries were exercised against generated evidence. Optional-failure
  summaries and verification flags were checked against the documented results.
- Across 140 HTML pages, 7,134 local and cross-package links, anchors, and
  image/script assets were checked with no broken targets.
- Desktop and mobile quickstart, Equipment navigation, and PSU reference pages
  were rendered in headless Edge. The mobile quickstart fits a 390-pixel viewport;
  long code examples remain horizontally scrollable.
- Executable ASTs of the 23 changed runtime modules match their pre-edit versions
  after excluding docstrings and documentation-only assignments.

Live hardware qualification, real SSH/broker readiness, real GUI application
behavior, and Linux telemetry were not exercised on this Windows validation
host. They are labeled as live prerequisites/limitations in the guides. External
sites beyond the six locally built documentation sites were not link-checked.
The PDF table of contents includes the reorganized pages, but a PDF was not
compiled. Implementation and validation preceded the per-repository pull requests
into develop. Documentation publication and package releases are separate steps.
