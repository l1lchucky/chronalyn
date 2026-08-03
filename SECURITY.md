# Security policy

## Supported versions

Only the latest tagged pre-release is supported before `1.0`.

## Reporting

Do not open public issues for suspected vulnerabilities or leaked secrets.
Use GitHub's private vulnerability reporting feature for this repository.

Include:

- affected version and configuration;
- reproduction steps;
- impact;
- whether real credentials or personal data were involved;
- suggested mitigation, when known.

The maintainer aims to acknowledge valid reports within seven days. No response
time is guaranteed.

## Secret exposure

Immediately revoke exposed credentials. Removing a secret from Git history does
not revoke it. Review Hindsight, Mnemosyne, router, backups, and logs.
