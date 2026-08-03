# Security policy

## Supported releases

Before `1.0`, only the newest tagged beta is supported. Older pre-releases may
contain known issues and should not remain in production.

## Reporting a vulnerability

Please do not open a public issue for a security problem or an exposed secret.
Use GitHub's private vulnerability reporting feature for this repository.

A useful report includes:

- the affected router version;
- the relevant configuration, with secrets removed;
- steps that reproduce the problem;
- the likely impact;
- whether real credentials or personal data were involved;
- any mitigation you have already tested.

The maintainer will try to acknowledge a valid report within seven days. This is
a community project and does not offer a response-time guarantee.

## When a secret is exposed

Revoke it first. Deleting a value from a file or Git history does not make the
credential safe again.

After rotation, check:

- Hindsight;
- Mnemosyne;
- the router database;
- setup and service logs;
- backups and exported archives.
