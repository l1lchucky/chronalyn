# Contributing

Thanks for taking the time to improve the project.

By submitting a contribution, you agree to license it under the MIT License.

## Before opening a pull request

1. Open an issue first for changes to routing, storage, deletion, privacy, or
   compatibility.
2. Keep the branch focused on one problem.
3. Add tests for the normal path and the failure path.
4. Run `make check`.
5. Update the relevant documentation and changelog.
6. Explain the security, privacy, compatibility, and rollback impact in the pull
   request.

A change will not be accepted if it silently drops writes, weakens environment
isolation, stores secrets in normal configuration, or turns both providers into
equal automatic memory backends without an approved design change.
