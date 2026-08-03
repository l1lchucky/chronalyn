# Contributing

By contributing, you agree that your contribution is licensed under MIT.

1. Open an issue for material architectural changes.
2. Fork and create a focused branch.
3. Add tests for success and failure paths.
4. Run `make check`.
5. Update documentation and changelog.
6. Open a pull request with security and compatibility impact.

No contribution may weaken environment isolation, silently drop failed writes,
store secrets in configuration, or enable equal automatic dual-provider routing
without an accepted design proposal.
