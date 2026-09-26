# One shared OTX meta-settings store for all modules

A technical proposition, draft 2 (26 Sep 2026), for discussion between the
module authors. It incorporates Sam Banks' eight comments on draft 1. It
distinguishes the agreed design rule from on-card and UI choices that still
need tests. Nothing here is implemented. Module authors can
start with the companion [guidelines](OTX_MODULE_GUIDELINES.md).
This technical proposal defines the format and takes precedence if the
author-facing guidelines differ from it.

Confidence markers: ✅ measured, 🟡 inferred with
a falsifier stated, ❌ retracted.

## Read this first

**Terminology.** The *OTX shared settings store* (short: *OTX store*) is
the one logical container that all modules share: `otx.work` / `otx.strd` in
a project, and optionally one UNIT file on the card. It is a shared file, not
a file system.

**One shared container holds the meta-settings of every module.** The
proposal is one logical OTX store in each project folder, represented by
`otx.work` and `otx.strd`. Both contain all modules, never one file per module.
Each module has a stable id and a record in that shared state. A firmware
without a module skips its record when
loading and copies that block back **byte for byte** when saving. A newer
version's unknown keys receive the same protection. Missing modules must
never prevent a project from opening.

When a setting genuinely applies across projects, the same format can be used
in one shared UNIT file at the **root of the inserted CF card**. Its proposed
name is `unit.otx`; unlike a project store it has no `.strd` fallback. This is
card-wide persistence, not internal memory that follows the physical
Octatrack to another card. The exact UNIT filename and recovery policy still
require agreement. **OTX names the shared format and its `OTX1` magic.** The
project files use the agreed stock-style names `otx.work` / `otx.strd`; `.otx`
is not their filename extension.

**Only meta-settings belong in `.OTX`:** how a module behaves or looks,
including menu options and generator setups. A groove, Kit, preset or other
piece of personal material that a musician may copy between projects stays
in a separate file owned and formatted by its module. The shared settings
core neither parses nor rewrites those files. This separation is the user's
design rule, not an open choice between one shared file and one file per
module.

The shared settings menu (name still open) shows only modules included in the
firmware, plus the core's GENERAL module. An
alternative firmware can exchange settings only if it adopts this format and
the same module ids. Stock project-copy commands may not carry the OTX pair;
that behavior is a required test (§5). Nothing here is implemented yet.
The UNIT filename and project-copy behavior still require agreement.

```text
SET / PROJECT / otx.work + otx.strd    working and saved shared state
                    ├─ org.octalab.core: page options, generator setup
                    ├─ org.example.fm: FM page options
                    └─ unknown module: retained unchanged

Octalab groove files              separate, Octalab-owned format
FM patches                        separate, FM-module-owned format
```

If an image without the FM module edits an Octalab setting, its next save
must leave the FM record byte-identical in the shared OTX state. It need not
understand, display or open the FM patch files.

---

> ## The rule this proposal rests on
>
> **The standard stores META-settings only: how a module behaves and looks,
> never the musician's material.**
>
> - **Meta, in the standard file:** how the GROOVE page is displayed, whether
>   the screen colours are inverted, USB AUDIO LIGHT or FULL, a checkbox that
>   changes how a page reacts. Small values that configure the tool.
> - **Personal material, in the module's OWN files:** anything a musician
>   would want to carry from one project to another, or keep as their own
>   (grooves, Kits, presets, curves). **Each module that
>   has such material keeps its own file system for it**: its own files, its
>   own format, its own place on the card. The standard never holds it,
>   never copies it and never decides its layout.
>
> The test for any value: *would someone want to copy it into another
> project on its own, without the rest of the configuration?* If yes, it is
> material and it stays out of the standard. Mixing the two would mean that
> copying a groove also copies a USB profile, and that resetting a page's
> display could erase someone's work.

## 1. The wish

A module with meta-settings stores them in **one shared container** and edits
them in **one shared menu category**, and it never loses another module's
settings. Concretely:

- An image built without a module shows none of that module's menu rows and
  never applies its block. It preserves the block unchanged on save, until an
  image with the module opens the project again.
- No module invents its own **meta-settings** file or save hooks
  or its own menu category any more. Octalab would move its meta-settings to
  this format and drop its OCTALAB root category, like everyone else.
- A module's personal material (Octalab's grooves, Octakit's
  Kits) stays in that module's own files, as the rule above says (§3.5).
- USB AUDIO's profile (OFF / LIGHT / FULL) is the first new setting. It is
  an optional module, so its row exists only in images that carry it.

---

## 2. What exists today

### 2.1 Where settings live now

- **In the Part** — every FX module's twelve parameters. ✅ Octabam's [`MODULES.md`](https://github.com/sambanks/octabam/blob/main/docs/remixer/MODULES.md) names the trap: "a stored value does the same, and the schema cannot see
  it". A Part saved under an older layout gives the new layout its old bytes,
  and a value outside the new count stalls the sequencer. Part parameters
  stay where they are. This proposal is for everything that is *not* a Part
  parameter.
- **Private files** — Octalab (this repository) writes
  `<set>/<project>/octalab_grooves.map` ("OTGM" v1, up to 40,228 B) and
  `octalab_generators.map`. ✅ MKI 15 Sep 2026: survives a power cycle, a
  SYNC and a project change. Each file has its own magic, its own checksum,
  its own save trigger and its own loader. Octakit keeps its Kits in files of
  its own. As far as we know (26 Sep 2026), no other module keeps state on
  the card.
- **Nowhere** — Octalab's menu checkboxes (`SC PITCH [ ]`…) ship in the image
  and reset at every boot.

### 2.2 What the firmware already gives us

- **A stock job queue that can run our jobs.** ✅ MKI (Octalab v41). A Detour at
  `0x4008485e` gives a job type of our own (`0x40`) to the stock engine job
  queue: the priority-1 "engine" task (dispatcher `0x4008445c`), the same
  queue that runs LOAD, SAVE and SYNC, not the priority-5 FAT/ATA task.
  The job is posted from a UI timer, and before the stock jobs 7 (SYNC TO
  CARD), 0xb/0xc/0xd (project change), 0x11 (SAVE PROJECT) and 0x12 (SAVE
  BANK). Writes go through the stock buffered calls
  `0x40016864` open / `0x400166b8` write / `0x4001677c` close.
  Octalab removes the file and writes it again, as the stock does for its
  own files (job `0x16`: remove, then write). A power cut during a write can
  leave the file missing or short; draft 2 accepts that same risk and relies
  on the saved `otx.strd` copy (§3.3).
- **The project folder** is `"%s/%s"` of the set path `0x100f8480` and the
  project name `0x100f8378` ✅. `FUN_400255ec() != 0` means a project is
  open.
- **A fifth MAIN MENU root category** made only of data (✅ MKI 7 Sep 2026;
  Octabam's [`MAINMENU.md`](https://github.com/sambanks/octabam/blob/main/docs/firmware/MAINMENU.md) §5): a heading row has a null action and the cursor skips
  it; the rows carry their value in the label. A shared toggle routine finds
  the row from the descriptor's absolute selection at `+0x0c` (✅ MKI 8 Sep
  2026). There is **no free page id** for a stock-style settings page, so a
  list whose labels change is the widget.
- **The limit this removes.** ✅ [`MAINMENU.md`](https://github.com/sambanks/octabam/blob/main/docs/firmware/MAINMENU.md) §5: "Two modules that both
  grow one submenu cannot coexist (the build refuses the second)". Each
  module that wants a row currently has to own a menu.

### 2.3 Prior art: how monome norns does it

norns has a mature answer to this problem, used by hundreds of scripts and
mods. It is read from monome's documentation (`monome.org/docs/norns/
reference/params`, `.../norns/mods`) and from its source (`lua/core/
paramset.lua`, `state.lua`, `pmap.lua`, `monome/norns` main, 26 Sep 2026):

- **One declarative registry.** A script declares its parameters in one
  table, `params`, which has typed entries: `number`, `option`, `control`,
  `taper`, `binary`, `trigger`, `text`, `file`. Every entry has a stable
  **id** (used by code and by the file) and a free **name** (shown in the
  menu). `add_separator` and `add_group` give the menu its structure, and
  `hide` / `show` change what is visible. The system draws the PARAMETERS
  menu; the script draws nothing.
- **A forgiving file.** A PSET is text, one `"id": value` line per saved
  parameter (`paramset.lua` `write`). On `read`, **an id the script no longer
  has is ignored, and a parameter missing from the file keeps its default.**
  Scripts can therefore add and remove parameters without breaking old
  presets.
- **Not everything is saved.** `trigger` parameters (actions) and
  separators are never written, and `set_save(id, false)` excludes
  runtime-only values.
- **Apply after load.** Reading a PSET calls every parameter's action
  (unless `silent`), and `params:bang()` does the same on demand. After a
  load, the script's state is whatever the values say, with no separate
  "apply" code to forget.
- **Extra data rides along.** `params.action_write` / `action_read` /
  `action_delete` are called with the PSET's file name and number. The docs
  recommend them for data that is not a parameter (sequences, tables),
  stored beside the PSET in the script's data folder.
- **System state is separate from script state.** Levels, clock, device
  assignments and the last script live in one system file
  (`dust/data/system.state`), and each script's presets in
  `dust/data/<script>/<script>-NN.pset`. MIDI mappings of parameters are a
  third file (`<script>.pmap`), keyed by the same parameter ids.
- **Mods are optional system extensions.** They are enabled in `SYSTEM >
  MODS` and load at startup. A mod registers its own menu page
  (`mod.menu.register`, under its own name) and lifecycle callbacks
  (`mod.hook.register` on `system_post_startup`, `script_pre_init`,
  `script_post_init`, `script_post_cleanup`, `system_pre_shutdown`). It can
  add parameters to any script's menu from `script_pre_init`. Hooks run in
  alphabetical order, and errors in them are caught so that a mod cannot
  break the system.

**What we take:**
- the declarative registry, with types, a stable id separate from the
  shown name, and menu structure generated by the system;
- the forgiving read;
- the `save=False` flag and never-saved triggers;
- the "apply after load" rule;
- callbacks for extra data (for settings that are not single values; not for
  personal material, which stays in the module's own files);
- system and project state kept apart;
- lifecycle events for optional modules.

**Where we must differ:**
- **ids live in a namespace.** norns ids share one flat namespace and a
  collision is only a runtime warning. Here an id is (module, key), and the
  build refuses a duplicate module id.
- **unknown keys are kept, not dropped.** A norns `write` saves only the
  parameters the current script has, so an id that an older or newer
  version wrote disappears at the next save. Here unknown keys are written
  back.
- **binary, not text.** The reader is ColdFire assembly. The computer tool
  (`otx.py dump`) gives the norns-style text view instead.
- **no user preset bank in this format.** On the OT the project (with its
  Parts/Kits) is already the snapshot. The WORK / STORED files below are
  recovery and save states, not presets the user selects.
- **no runtime enabling.** A module is in the image or it is not. The build
  does what `SYSTEM > MODS` does on norns.

---

## 3. The proposal

Four parts: declarations in module manifests, one shared core, one logical
OTX store per scope, and one generated shared settings menu. The core owns
meta-settings only. A module owns the format of its separate creative files.

### 3.1 Modules declare settings; the core owns the shared file

Illustrative manifest syntax (an API proposal, not implemented):

```python
store=Store(id="org.octalab.usbaudio", scope=Scope.UNIT),
settings=(
    Setting(key=1, name="USB AUDIO", group="audio", values=("OFF", "LIGHT", "FULL"),
            default=0, apply=Apply.NEXT_CONNECT),
),
```

- `id` identifies the feature across firmware builds. It is namespaced and
  stable; the build rejects duplicate ids. LIGHT and FULL variants of one
  feature use the same id. Menu labels may change without changing ids.
- `key` is a numeric setting id that is never reused for another meaning.
  An `Option` stores an index (append values only, never reorder them);
  `Binary` stores 0/1; `Number` stores a signed 16-bit value with declared
  bounds, step and unit; `Trigger` runs an action and is never saved.
  `save=False` marks a runtime-only value. A declarative `visible=` condition
  may hide rows without changing their stored values.
- These declarations also define the ordinary UI control: `Binary` draws a
  checkbox; `Option` draws a choice among its declared labels; `Number` draws
  a signed 16-bit integer control constrained by `min`, `max` and `step`, with an optional
  displayed unit. Each declares a default. The common core validates edits
  before calling the module. A `Blob` needs an explicitly provided editor or
  remains outside the generic scalar menu; it is never displayed as raw bytes.
- A module may declare stable parameter-group ids, short display labels and
  ordering (for example Octalab's `generators` group). A setting names one
  group id; this is menu metadata, never part of its stored OTX key. Renaming
  a group or changing the UI layout does not migrate settings.
- `scope=PROJECT` puts the module's block in that project's shared
  `otx.work` / `otx.strd` state. `scope=UNIT` puts it in the shared UNIT
  file at the card root. One module
  may declare settings at both scopes; that creates one block for the module
  in each container, never `<module>.otx` files.
- `apply=LIVE` means the module reads the current RAM value;
  `CALLBACK` calls its idempotent routine after load or edit;
  `NEXT_CONNECT` and `NEXT_BOOT` keep requested and effective values separate
  until that event. A fixed LIGHT image cannot become a 20-channel FULL
  device merely by changing this setting. Descriptor switching and USB
  re-enumeration need separate implementation and tests.

The core loads typed values into a RAM table, validates their ranges and
exports them to the linked module. A module can declare a bounded blob for a
small meta-setting that is not a scalar (for example, a generator setup);
it supplies pack/unpack callbacks. A blob in `.OTX` remains **configuration**.
Grooves, Kits, presets, samples and any other transferable creative content
never become blobs in this container (§3.5).

### 3.2 Shared core, absent modules and lifecycle

An OTX-enabled build includes one shared DRAM core and its GENERAL module,
even if no optional module declares settings. The core owns the settings menu,
shared PROJECT and UNIT state, the storage job, dirty
tracking, validation and safe writes. Modules never edit `.OTX` directly.
The build orders callbacks deterministically by module id and reports the
order. Proposed events: `unit_loaded`, `project_loaded`, `project_saving`,
`project_closing`, `setting_changed`.

**Preservation contract, required of every firmware that adopts OTX:**

1. Load a known module record with the supported schema major, including a
   **newer minor**: apply known keys and preserve unknown typed TLVs exactly.
   An unsupported major or an absent module is opaque and gets no callback;
   neither can block the project from opening.
2. Keep every opaque module record as its **exact bytes**: header, full id,
   payload, flags and padding. Write those bytes back unchanged on every
   save. Do not silently drop a record to make room.
3. Within a known record, preserve unknown setting TLVs byte for byte when
   editing known keys. A missing or invalid known value takes its declared
   default. A known key with a different type is invalid, never coerced.
4. Duplicate module ids are not applied; **every duplicate copy** is retained
   unchanged. A failed payload or callback runs that module on defaults,
   shows `LOAD ERR`, and leaves other modules available. Neither error is
   repaired merely by opening the menu or editing another module.
5. A dedicated `REPLACE SETTINGS` action with confirmation is proposed for
   deliberately replacing one damaged module record. Its exact UI remains
   open. A save must preflight all declared limits and fail visibly before
   opening `"w"` if it cannot retain all opaque records. An interrupted write
   may still corrupt `otx.work`; the saved-copy recovery below is separate.

The core loads outside the audio ISR. After every project or UNIT load, it
validates known values, supplies defaults for missing or invalid values, and
invokes each applicable callback once with the resulting value. It invokes
callbacks again after edits. A callback must be safe to receive the same
value on repeated loads. The `unit_loaded` event must occur before a
setting can affect USB descriptors; that boot ordering has not yet been
measured (§5).

Automatic OTX writes run as jobs in the stock engine job queue (§2.2), never
in the UI task. The UI
must not acquire or wait on `FS_MUTEX` for OTX. Edits are coalesced into one
bounded job after roughly two seconds idle (initial target to tune on MKI),
including when playback is running. Automatic OTX writes are deferred while
any stock recorder, CAPTURE or tape capture is writing; the dirty state stays
pending until storage can safely resume. Writes are serialized with stock
project and other CF writes. Explicit SAVE and project-switch behavior with
pending edits still needs a rule and hardware test.

MKI evidence from OLT01/OLT02, Octalab's tape-recorder diagnostic builds
(26 Sep 2026): individual CF writes reached
about 1.2 s under STATIC playback; with CAPTURE active, UI stalls reached
1.215 s and followed a 1.206 s write. UI-side waiting on `FS_MUTEX` is a
strong hypothesis, not a proven trace. OLT01 measured 1.4–2.1 MB/s while
STATIC tracks read. These are storage-system measurements, not OTX write
latencies. They rule out UI-task file access as an acceptable OTX design and
make a playback/CAPTURE timing gate mandatory.

### 3.3 Shared PROJECT state as `.work` / `.strd`

- `<set>/<project>/otx.work`: the working meta-settings of **all** modules,
  including modules absent from the running firmware. Rewritten after edits
  are coalesced and storage is available.
- `<set>/<project>/otx.strd`: the saved state of **the same shared store**.
  SAVE PROJECT writes it; RELOAD PROJECT loads it. These are not two module
  stores and not a four-slot preallocated file.
- One optional shared UNIT file at the inserted CF card root (working name
  `unit.otx`): card-wide settings for all modules, with no `.strd` copy. The
  persistence and recovery policy for a missing/unreadable card is open.

Sam's stock-style write proposal is `open("w")`, write, close. The stock
rewrites its own project files the same way after removing the old file (job
`0x16`); an open for writing does not itself shorten a file, and the length
is set at close. This is not an atomic write: a power cut can leave
`otx.work` missing or short, the same risk stock `project.work` accepts. Only
`"r"` and `"w"` are identified as open modes (adjacent strings at
`0x400b3289`); the image contains no `"r+"` string. In-place rewriting is
possible (the stock buffered seek `0x4001660c` rewrote WAV headers in place
on the MKI in OLT01/OLT02, and Octakit rewrites a preallocated file in
place), but draft 2 keeps the simpler stock-style rewrite and drops the
former fixed A/B slots, sector alignment, generation counters and
`slot_bytes`.
**Fresh, normal, recovered or damaged: decided by what is on the card**
(Sam Banks' rule of 27 Sep 2026, completed with the cases it did not list).
"Invalid" means the whole file fails its header, length or CRC checks; one
bad module inside a valid file is that module's `LOAD ERR` only (§3.2).

| `otx.work` | `otx.strd` | Meaning | Action |
|---|---|---|---|
| absent | absent | Fresh: new project, stock SAVE TO NEW, hand copy | Declared defaults; normal first write |
| valid | absent | Normal: edited, never saved | Use `otx.work`; SAVE PROJECT creates `otx.strd` |
| valid | valid | Normal | Use `otx.work` |
| valid | invalid | Saved copy damaged | Use `otx.work` and show a warning; an explicit SAVE PROJECT may rewrite `otx.strd` |
| absent | valid | Interrupted rewrite | Recovery: load `otx.strd`, report it |
| invalid | valid | Damaged working copy | Recovery: load `otx.strd`, report it |
| invalid | absent | Damaged, no fallback | Error; no OTX write until REPLACE SETTINGS |
| absent or invalid | invalid | Damaged, no fallback | Error; no OTX write until REPLACE SETTINGS |

Why the rows Sam's three cases did not cover matter:
- **absent `otx.work` + valid `otx.strd` must be recovery, not fresh.** The
  stock rewrite removes the old file before writing it (job `0x16`), so a
  power cut during an OTX write most likely leaves `otx.work` *missing*, not
  merely invalid. Treated as fresh, the next write and SAVE PROJECT would
  replace the good saved copy with defaults.
- **valid `otx.work` + absent `otx.strd`** is the ordinary state of a
  project edited but never saved; it must not raise an error.
- **valid `otx.work` + invalid `otx.strd`** loses nothing: the working copy
  is sound, and the user's explicit SAVE PROJECT is the moment to rewrite the
  damaged saved copy (the only case where an unreadable OTX file may be
  overwritten, and only by an explicit save; to confirm with the authors).
- A fresh project and a project whose OTX pair was lost by a copy that
  omits it look identical on the card. That is why the SAVE TO NEW / COLLECT
  / EXPORT copy test (§5) is mandatory.

Recovery from `otx.strd` reverts OTX edits made since the last SAVE PROJECT
and is always reported. No automatic path writes defaults over an unreadable
OTX file.

The common record and TLV format remains binary, big-endian. The following
is a **draft byte layout** for a neutral reference tool and test corpus:

```text
File header (24 bytes)
  0   char[4]  "OTX1"
  4   u16      header size = 24
  6   u8       container major = 1     7 u8 container minor = 0
  8   u8       kind (0 WORK, 1 STORED, 2 UNIT)
  9   u8       flags (zero when new)   10 u16 reserved = 0
  12  u32      total file bytes, including the trailing CRC
  16  u32      record count           20 u32 reserved = 0
Records, exactly `record count` times
  0   u8       full id length (1..63)  1 u8 flags
  2   u16      schema major           4 u16 schema minor
  6   u16      reserved = 0
  8   u32      payload length        12 u32 payload CRC-32
  16  u32      record size
  20  byte[]   full namespaced ASCII id, payload, padding to 4 bytes
Then u32      file CRC-32 (IEEE) over all preceding bytes
```

A reader advances by **record size**, not by payload length alone. It must
also require `record size == align4(20 + id length + payload length)` and
bounds-check all three lengths before reading or allocating. A disagreement
invalidates that record for application but preserves its raw bytes if its
record-size boundary is safe. If that boundary cannot be trusted, or if the
file CRC fails, the entire file is invalid and the reader tries the saved
copy.
The full id is stored, never a truncated prefix. Duplicate ids retain every
copy unchanged, but none is applied. A newer file/container major is not
rewritten by an older reader.

A known module's payload is a sequence of typed TLVs:

```text
  0   u16      stable key             2 u8  type
  3   u8       reserved = 0           4 u16 flags
  6   u16      reserved = 0           8 u32 value length
  12  byte[]   value, padding to 4 bytes
```

The reader advances by `align4(12 + value length)`. Proposed type table:
`1 Binary` (one byte, 0/1), `2 Option` (one-byte index), `3 Number`
(signed 16-bit big-endian), `4 Blob` (declared maximum in bytes). A module
manifest gives each Blob and each complete record a finite byte maximum;
the build checks the declared maxima. The global file ceiling and these
numbers need agreement before any on-card writer ships. A key cannot change
type: adding a new interpretation means a new key or a new schema major.

Record flags are `u8`; TLV flags are `u16`. New packets write zero. Within
major 1 the flags carry no semantics and are ignored when applying known
values, but their existing bytes are retained on rewrite. A future meaning
must use a new major, type or key rather than silently repurposing these
ignored bits. Unknown packets, unknown keys and their padding are retained
**byte for byte**. A type mismatch on a known key takes its default while
preserving the original packet for diagnosis.

A reference tool must verify both CRC levels, length arithmetic, unknown
record/TLV round-trips, torn `otx.work` fallback, missing `otx.strd`, duplicate
ids, newer minor and unsupported major. A valid saved copy is recovery, not
a promise of atomic `"w"` writes. The stock-like write path and copying of
both OTX project files still need emulator and MKI tests.

### 3.4 One generated settings menu with GENERAL

The build emits one root category beside PROJECT / SYSTEM / CONTROL / MIDI
when OTX is enabled. **MODULES** is only a working label; the name needs
agreement. This category always contains a
default **GENERAL** module supplied by the core at the same level as other
modules, and shows only optional modules
present in the image; absent modules' bytes remain in OTX with no menu row.
Authors can propose a setting for GENERAL when it truly concerns the whole
firmware. Shared GENERAL keys, type, meaning and defaults are maintained in
one core registry and reviewed together; a module cannot independently claim
or redefine them. Module-specific settings retain their module namespace.
The stable identifier for GENERAL itself needs agreement before files ship.

Each present module contributes settings under its own stable namespaced id
and may declare parameter groups. For example,
`org.octalab.core > GENERATORS > ...` could be displayed with the shorter
label `OCTALAB`. The namespace owns the group and prevents collisions; a
module without groups shows its settings directly. No module gets its own
meta-settings root category.

As an **example** of a cross-module setting, GENERAL could hold a UNIT
`Option` choosing a scrolling list with module separators or an index of
module submenus. This is not yet a decision to implement both layouts or a
fixed `GROUPING` key. If adopted, the choice must remain reachable from every
view, have a safe default when UNIT cannot be read, and leave module ids,
keys and values unchanged. All settings, including GENERAL, must be reachable
with arrows alone. The exact row structure, editing gestures, page-id limits,
scrolling and back-navigation need emulator and MKI checks.

In the existing stock menu widget, a row inside a pane cannot descend into
another submenu, and no free page id is known
([MAINMENU.md](https://github.com/sambanks/octabam/blob/main/docs/firmware/MAINMENU.md) §5). A different UI mechanism would
need proof. A flat 26-row OCTALAB
category was used on the MKI in OLT02 with arrow navigation.

### 3.5 Creative files remain entirely module-owned

The practical test is: **would a musician want to copy it to another project
on its own?** A groove, Kit or preset answers yes. It is personal material,
not a meta-setting. The module chooses its file name, location, format,
versioning and migration, and can change them independently of `.OTX`. The
shared core does not parse, copy, delete or impose a header on those files.
A meta-setting may hold a reference to one of them (for example a selected
groove file) but never embeds or rewrites its contents. Octalab's grooves
therefore stay in its own files; generator setups, by the user's decision,
are small PROJECT settings in Octalab's record.

---

## 4. First users

| module | shared scope and proposed id | meta-settings in `.OTX` | separate creative files |
|---|---|---|---|
| USB AUDIO (FULL or LIGHT image) | UNIT / `org.octalab.usbaudio` | PROFILE OFF/LIGHT/FULL, default OFF; later A/B and C/D input choices if USB input is built | none |
| Octalab | PROJECT / `org.octalab.core` | checkboxes, page display choices, generator setups | grooves in Octalab's own format |
| Octakit | its author's choice | only settings it chooses to declare | Kits in Octakit's own format |

The ids above are examples to discuss with their authors before any file is
written. Octalab's checkboxes currently reset at boot, so they start from
defaults. GENERATOR setups can be imported from `octalab_generators.map` only
after a tested migration: write Octalab's block, read it back, then retain the
old file for older builds. `octalab_grooves.map` remains module-owned and is
not imported into `.OTX`.

Default USB OFF is motivated by the MKI CAPSTRESS6 comparison: the image
without USB AUDIO was substantially smoother than the 20-channel image.
The size and cause of the difference are not yet measured. A stored FULL
request on a LIGHT-only image stays stored; that image applies only a
capability it actually implements and shows requested versus effective.

---

## 5. What must be agreed and measured

The **shared store and module-owned creative files are the design rule**. The
following details are open before implementation:

1. Use the agreed `otx.work` / `otx.strd` project names and OTX format name.
   Ratify the UNIT filename, recovery policy, and maximum file, record and
   Blob sizes; publish a neutral byte corpus.
2. Implement `tools/hw/otx.py` on the computer: create, read, validate, dump
   and round-trip. Cover absent modules, newer minor, unsupported major,
   unknown type/key/flags, duplicate ids, bad lengths, CRC failures, torn
   `otx.work`, absent `otx.strd`, and byte-identical opaque preservation after
   a known setting edit.
3. Trace stock `"w"` / close and project SAVE/RELOAD timing in the emulator,
   then test the OTX pair on a disposable MKI project, including playback and
   CAPTURE while edits save. A valid `otx.strd` fallback must be visible; no
   valid fallback must never become a silent overwrite of damaged data.
4. Implement one shared core with GENERAL and module-owned groups. Test
   arrow-only navigation, namespaces, per-module parameter groups, scrolling,
   row count, back-navigation, LOAD ERR and the deliberate `REPLACE SETTINGS`
   action on MKI. If a menu-presentation setting is adopted, test each offered
   view and switching between them before shipping it.
5. Test stock SAVE TO NEW, COLLECT SAMPLES, EXPORT TO SET, PURGE and project
   copy. If they omit OTX, the shared core must copy both project files,
   retaining unknown module records byte-identically.
6. Decide UNIT recovery and card-swap behavior. Prove UNIT load and any USB
   profile application finish before the host reads descriptors. Until then
   `NEXT_CONNECT` is only a requested behavior.
7. Keep all OTX I/O out of audio ISRs and measure latency with several module
   records and CAPTURE under extreme CF load.
8. Choose the user-facing name of the special settings menu. **MODULES** is
   only a working label. Decide the menu structure with authors and MKI tests;
   a presentation-choice setting is an example, not an agreed requirement.
   The existing stock pane cannot descend to a module submenu; prototype a
   different mechanism before promising one.

---

## 6. What a module author does

- Declare a stable namespaced id, keys, defaults, scope and apply policy for
  **meta-settings**. Do not create a private OTX settings file, menu root or save
  hook for those settings.
- Keep grooves, Kits, presets and other transferable personal content in
  files whose format the module alone chooses and maintains. The shared
  settings core never dictates that format.
- Make callbacks idempotent and validate bounded blobs. A module only sees
  its own recognized record; it never parses another module's block.
- Add a neutral compatibility test: when this module is removed from an
  image, editing another module's setting and saving must preserve this
  module's complete record byte for byte.

## 7. Later, not in draft 2

Stable (module, key) addresses make a settings map possible, like norns'
`.pmap` for MIDI mappings: a MIDI CC or one of our USB vendor requests could
read or set any declared setting by address, with no code in the module.
For example, the computer could select the USB profile. Nothing here depends
on it.
