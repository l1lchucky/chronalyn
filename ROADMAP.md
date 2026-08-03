# Roadmap

This is a working plan, not a promise of dates or features. Priorities may move
when upstream APIs change, testing uncovers a problem, or users report a better
need.

## 0.2.0-beta.1

The beta focuses on being a well-behaved Hermes memory provider:

- one router remains the only external provider visible to Hermes;
- Hindsight-only and dual-mode policies are both supported;
- provider discovery is read-only until the user approves a plan;
- package installation never activates Mnemosyne;
- current Hindsight memories are preserved;
- configuration changes are backed up and reversible;
- router databases are tied to one Hermes profile, namespace, and environment;
- recalled content is returned plainly so Hermes adds its own context fence;
- the default Hermes tool list stays small;
- model-requested deletion is disabled unless an operator enables the two-step
  confirmation flow;
- dual setup has a lightweight terminal interface with keyboard and optional
  mouse support.

## Next beta work

- test against supported Hermes releases in CI;
- report Hindsight and Mnemosyne versions in `status`;
- add database integrity and migration commands;
- add a guided backup-and-restore check;
- expose simple metrics without requiring a monitoring stack;
- add repair tools for orphaned backend records;
- improve error messages using real staging feedback.

## Release-candidate work

- run longer staging soak tests;
- test a controlled production canary;
- publish backup and disaster-recovery results;
- freeze the configuration format for `1.0`;
- document supported dependency combinations;
- test shutdown, restart, retry, and delete races with live services.

## What must be true before 1.0

- no known data-loss bug;
- no known staging/production crossover bug;
- no known provider-conflict regression;
- safe configuration and database upgrades;
- successful live fallback, retry, deletion, restart, and restore tests;
- tested self-hosted and Hindsight Cloud installations;
- signed release artifacts with an SBOM and provenance record;
- a clear rollback and security-response process.

## Other memory backends

A new adapter needs a clear job. It must document its IDs, retry behavior,
delete behavior, privacy boundary, and failure policy. Provider count by itself
is not a project goal.
