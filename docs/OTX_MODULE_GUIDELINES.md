# Octabam Module Settings — Format and Menu Guidelines

Discussion draft 2 for a future Octabam PR. Each module owns its own
meta-settings. OTX gives those settings a common file format, registry and
menu conventions so projects remain usable across different module builds.
Only the settings in **GENERAL** are common to the whole firmware. This page
covers parameter declarations, controls, groups and menu placement; it is
not a guide to creating modules. The API is still a proposal, not
implemented. The companion format proposal is
[OTX_PROJECT_PROPOSAL.md](OTX_PROJECT_PROPOSAL.md), which defines the technical format
and takes precedence if these guidelines differ from it.

## What belongs in OTX and the common menu

**Terminology.** The *OTX shared settings store* (short: *OTX store*) is
the one container all modules share (`otx.work` / `otx.strd` per project,
optionally one UNIT file). It is a shared file, not a file system.

**OTX names the common file format for module meta-settings in a project.** Its
agreed project filenames are `otx.work` and `otx.strd`, beside the stock project
files. These are the working and saved copies of the **same shared store**,
never one pair per module. An optional card-wide UNIT store uses the same
record format; its filename and lifetime still need agreement.

Put *meta-settings* here: values that change how a module behaves or presents
itself. Keep transportable musical material, such as grooves, Kits, patches
and presets, in separate files whose names, location, format and migration
belong to the module. OTX must not parse or rewrite those creative files.
Existing stock Part parameters remain in Parts.
Ask whether someone would want to copy a value into another project on its
own: if so, it is content for a module-owned file, not an OTX setting.

## Declare settings through the shared registry

- Choose a stable, namespaced module id. The build must reject duplicate ids.
  A renamed menu label does not rename the id. Variants of one feature share
  its id if they share the settings schema.
- Declare optional parameter groups with stable ids, short display labels and
  a predictable order (for example `org.octalab.core > GENERATORS`). Assign
  each setting to at most one group. Groups are menu metadata: moving a row
  between groups never changes its persistent key or value.
- Declare each persistent key, type, default, scope (`PROJECT` or `UNIT`),
  validation bounds and apply policy. Never reuse a key for a new meaning or
  change its type in place. Add a new key and a migration instead. A newer
  minor schema may add optional keys; a breaking interpretation needs a new
  major schema.
- Declare the control that the common menu should draw. `Binary` (0/1) is a
  checkbox; `Option` is a choice from an ordered list of labels; `Number` is
  a **signed 16-bit integer** with a declared minimum, maximum, step, optional
  unit and default. The core validates these values and builds their ordinary
  menu controls. `Trigger` is an action rather than a saved setting. A small
  bounded `Blob` needs an explicit module editor or stays off the generic
  scalar menu; raw bytes are never shown as a number.
- An `Option` stores its numeric index. Append new choices at the end of its
  list; never reorder, remove or reuse an existing index, because old project
  files would silently acquire a different meaning.
- Declare an explicit maximum payload size **in bytes** for each record and
  each Blob setting. The shared core must check the assembled file size before
  writing. A Blob is for small configuration, not a way to put musical
  material in OTX. The global budget is still to be agreed with authors.
- Keep callbacks idempotent and bounded. After **every** project or UNIT
  load, the core passes each applicable callback the resulting validated
  value or declared default, even if it is unchanged from the previous load.
  It calls them again after an edit. They do not parse another module's
  record, edit the OTX files, or perform card I/O from an audio interrupt.
- Declare nonpersistent actions as triggers. A hidden menu row or a module
  absent from the image does not delete its stored value.

For example, these declarations give the menu enough information to draw and
validate a control without bespoke UI code:

| Declared type | Menu control | Author supplies |
| --- | --- | --- |
| `Binary` | Checkbox | Label and default on/off value |
| `Option` | Labelled choice | Append-only ordered labels and default index |
| `Number` | Signed 16-bit integer value | Minimum, maximum, step, default, optional unit |

For example, a possible common setting for menu presentation could be an
`Option` with `LIST` and `BY MODULE`. A module's own checkbox or ranged
integer uses the same declarations under its own namespace. The exact
manifest API is still illustrative in the companion proposal.

The shared core owns the menu, file I/O, integrity checks, write scheduling,
error display and project/UNIT lifecycle. A module may keep its own creative
files, but it must not create a private settings sidecar for OTX values.

## Keeping projects usable across firmware builds

- A firmware without your module must open the project and write your whole
  record back **byte for byte**, including its id, flags, payload and padding.
  Your module must do the same for unknown keys inside a record it understands.
- A newer **minor** schema still loads: known keys are validated and applied;
  unknown typed TLVs survive untouched. An unsupported **major** is opaque and
  survives untouched. A type mismatch on a known key is not silently coerced.
- Duplicate module ids are invalid for application; **every copy** survives
  unchanged until an explicit repair. One bad module does not prevent the
  other modules or the project from loading.
- If your record fails validation, your module runs on declared defaults and
  the common UI shows `LOAD ERR`. Merely entering the menu or editing another
  module does not erase the bad record. A dedicated `REPLACE SETTINGS` action,
  with confirmation and a clear scope, is proposed for deliberate replacement
  of that module's damaged record. The exact label and interaction need UI
  agreement.
- New packets write zero reserved/flag fields. Readers preserve bytes they do
  not understand. The spec must settle how a known packet with nonzero future
  flags is handled before anyone claims compatibility.

## Working, saved and recovery behavior

The proposed `otx.work` uses stock-style open `"w"`, write, close, after edits
have been coalesced; `otx.strd` is written on SAVE PROJECT. RELOAD
PROJECT loads `otx.strd`. A valid `otx.strd` can recover an invalid `otx.work`,
and the UI must report that recovery. Neither file is an archive of every edit.

A missing or invalid `otx.strd` leaves **no proven recovery source**. The core
must show an error and must not silently overwrite an unreadable OTX file or
claim to have preserved unknown records. Fresh projects may start with module
defaults, but their creation path must be distinguished from corruption. UNIT
has no proposed `.strd` fallback, so its failure policy must be specified
before a UNIT setting is relied on at boot.

Automatic OTX writes must run as jobs in the stock engine job queue (where
Octalab's storage jobs already run), never in the UI task; the
UI must not acquire or wait on the FS mutex for OTX. Coalesce edits and queue
one write after roughly two seconds without further edits; this is an initial
debounce target, not a measured optimum. Defer automatic OTX writes while any
stock recorder, CAPTURE or tape capture is writing, and keep the dirty state
until storage can safely resume. Serialize OTX with stock saves and other CF
writes. The behavior of an explicit SAVE or project switch with pending OTX
changes still needs an implementation rule and MKI test.

**MKI evidence, 26 Sep 2026:** OLT02, an Octalab tape-recorder diagnostic
build, observed individual CF writes of about
1.2 s under STATIC playback. With CAPTURE active, UI stalls reached 1.215 s
and tracked those writes; UI-side waiting on `FS_MUTEX` is a strong
hypothesis, not a proven call trace. OLT01 measured roughly 1.4–2.1 MB/s
while STATIC tracks read. These are storage-system measurements, not OTX
write timings. The OTX scheduler still needs a playback/CAPTURE stress test.

Rewriting `otx.work` the stock way (the stock removes the old file, then
writes it with `"w"`) can leave it missing or short after a power cut, as
stock's `project.work` can. A CRC detects an incomplete file and a valid
`otx.strd` can recover it, but edits since the last saved copy can be lost.

## Common settings

The special settings menu starts with **GENERAL**, a default module supplied
by the OTX core at the same level as other modules. GENERAL is visible even
when no optional module declares settings. Put a setting here when its meaning
is shared across the firmware and remains useful independently of any one
module: for example, a preference that changes how the common menu presents
settings. A feature's own enable switch or generator option belongs to that
feature's module.

Module authors can propose common settings, but GENERAL has one shared
definition of each key, type, default and behavior. The core maintains that
definition so two modules cannot give a common key different meanings. A
common setting still declares its `PROJECT` or `UNIT` scope as appropriate;
GENERAL does not mean that every value is card-wide. Its stable module id
must be chosen before files are written.

One **possible example** is an `Option` in GENERAL that chooses between a
scrolling list and module submenus. This illustrates where a cross-module UI
preference would live; neither presentation nor a switch between them is
agreed for implementation.

## Parameter groups

Each present module uses its stable namespace and may group related settings.
These declarations organize the menu; they do not change the OTX keys or
values stored in the module's record.

| Level | Author declares | Example on screen | Stored identity |
| --- | --- | --- | --- |
| Module | Stable namespace and short label | `OCTALAB` | Namespace identifies the OTX record |
| Named parameter group | Group id, short label and order | `GENERATORS` above its settings | UI metadata only; setting keys stay the same |
| Ungrouped settings | No group id | Settings directly under `OCTALAB` | Their ordinary setting keys |

For example, a flat menu could show `OCTALAB`, then a separator line labelled
`GENERATORS`, then the generator settings. A module with no groups shows its
settings directly after its heading. A different screen arrangement may be
chosen after testing; the namespace and group ids keep the declarations
stable. Every row must remain reachable with the arrow keys, preserving the
familiar navigation gesture. Exact row structure and editing gestures need
MKI tests.

## Open questions for the menu

- What should the special settings menu be called? **MODULES** has been a
  working label, not an agreed name.
- Should it use a flat list with separator lines, module submenus, or offer
  a common setting to choose? In the current stock menu widget, a row within
  a pane cannot open another submenu and no free page id is known
  ([MAINMENU.md](https://github.com/sambanks/octabam/blob/main/docs/firmware/MAINMENU.md) §5); a different UI mechanism would
  need proof.
  The flat 26-row OCTALAB category was used on the MKI with arrow navigation
  (OLT02). Test row count, scrolling and navigation before deciding.
- Should OTX have a spelled-out name? **Octatrack Typed eXchange** is one
  suggestion, reflecting the typed values exchanged between firmware builds.
  OTX remains the format name unless the authors agree on an expansion.

## Checks before an Octabam implementation ships

1. A computer reference reader/writer plus shared test files for old/new
   minor and major schemas, unknown keys and flags, duplicate ids, bad lengths,
   bad CRCs, torn `otx.work`, missing `otx.strd`, and byte-identical opaque
   record preservation after another module is edited.
2. Emulator and MKI checks for new project, project switch, SAVE PROJECT,
   RELOAD PROJECT, SAVE TO NEW, COLLECT, EXPORT and PURGE, including modules
   absent from the running image.
3. A measured heavy playback/CAPTURE test for `"w"` writes and a boot-order
   test before any UNIT preference can affect USB enumeration.

The UNIT filename and recovery rule, on-card byte layout, future flag
semantics, size limits and precise editing gesture require joint review before
these guidelines are ready to implement. The OTX format name, project
filenames and GENERAL section are agreed design choices, pending
implementation. A menu-presentation setting remains an example for discussion.
