# Dual Memory Router Setup

The setup interface is a small terminal application built for one job: explain
and install the Hindsight-primary, Mnemosyne-checkpoint policy without hiding
what changes on the machine.

It uses Python's standard `curses` module. There is no web server, JavaScript
runtime, TUI framework, or long-running setup process.

## Controls

```text
ARROWS    move
1-9       choose a numbered option
SPACE     select or toggle
ENTER     continue
MOUSE     click an option where supported
B         back
Q / ESC   cancel
```

Keyboard controls always work. Mouse support depends on the terminal emulator
and can be disabled with `--no-mouse`.

## Design

The interface is monochrome so it remains readable over SSH, serial terminals,
low-color consoles, and dark or light themes. Selection uses reverse video and
bold text instead of color.

The Pac-Man line appears only while a task is waiting:

```text
C  * * * *  Testing Hindsight
<  * * *    Testing Hindsight
C    * *    Testing Hindsight
```

It is animation, not a second process or network feature.

## Setup steps

### 1. Welcome

Explains the four routing rules before anything is installed.

### 2. Hermes

Reuses an existing Hermes runtime when found. If Hermes is missing, the setup
offers to download the official installer, displays its source and SHA-256, and
waits for approval.

### 3. Project identity

Collects a namespace and environment. These values form the default Hindsight
and Mnemosyne bank names and bind the router database.

### 4. Hindsight

Offers three choices:

1. reuse the profile's existing Hindsight connection;
2. connect to a self-hosted Hindsight API;
3. connect to Hindsight Cloud.

Remote endpoints are shown clearly and require a privacy acknowledgement.
Secrets are masked and written to an owner-readable environment file.

### 5. Policy acknowledgement

The user toggles each routing statement:

```text
Hindsight owns automatic memory.
Mnemosyne receives checkpoints only.
Existing memories will not be migrated.
The selected endpoint and data location are understood.
```

All statements must be selected before setup can continue.

### 6. Review

Shows paths, banks, endpoint, actions, backups, and the final routing policy.
Pressing Back returns to editing. Enter starts installation.

### 7. Apply and verify

The setup:

- installs the router and Mnemosyne dependency into Hermes' Python;
- installs one Hermes memory-provider entry;
- backs up current configuration;
- writes the profile-scoped router and Hindsight files;
- checks Hindsight and Mnemosyne;
- activates the router only after successful checks;
- shows the backup path and rollback command.

## Small terminals and accessibility

The UI asks for at least 72 columns and 22 rows. If the terminal is smaller, it
shows the required size and waits for a resize.

Secret fields are masked. Every mouse action has a keyboard equivalent. The UI
can be bypassed for automation by using the documented `adopt` and `provider`
commands.
