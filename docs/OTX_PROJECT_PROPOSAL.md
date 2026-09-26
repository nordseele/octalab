# One shared `.OTX` meta-settings file for all modules

Draft 1 (26 Sep 2026), for discussion among authors of alternative Octatrack
firmware. It separates the agreed design rule from encoding and integration
choices that still need measurements. No `.OTX` parser or firmware support is
implemented.

Evidence markers: ✅ observed on the unit or in the named code; 🟡 inferred
with a stated way to disprove it; ❌ retracted.

## Read this first

**One shared container holds the meta-settings of every module.** The
proposal is `project.otx` in each project folder. Each module has a stable id
and a block inside that file. A firmware without a module skips its block when
loading and copies that block back **byte for byte** when saving. A newer
version's unknown keys receive the same protection. Missing modules must
never prevent a project from opening.

When a setting genuinely applies across projects, the same format can be used
in one shared `unit.otx` at the **root of the inserted CF card**. This is
card-wide persistence, not internal memory that follows the physical
Octatrack to another card. The name and location of that optional UNIT file
still require agreement; the project file is the main proposal.

**Only meta-settings belong in `.OTX`:** how a module behaves or looks,
including menu options and generator setups. A groove, Kit, preset or other
piece of personal material that a musician may copy between projects stays
in a separate file owned and formatted by its module. The shared settings
core neither parses nor rewrites those files. This separation is the user's
design rule, not an open choice between one shared file and one file per
module.

The shared MODULES menu shows only modules included in the firmware. An
alternative firmware can exchange settings only if it adopts this format and
the same module ids. Stock project-copy commands may not carry `.otx` files;
that behavior is a required test (§5). Nothing here is implemented yet.
Examples use lowercase `.otx`; the file type is `.OTX` on a case-insensitive
FAT card.

```text
SET / PROJECT / project.otx       shared meta-settings for every module
                    ├─ org.octalab.core: page options, generator setup
                    ├─ org.example.fm: FM page options
                    └─ unknown module: retained unchanged

Octalab groove files              separate, Octalab-owned format
FM patches                        separate, FM-module-owned format
```

If an image without the FM module edits an Octalab setting, its next save
must leave the FM record in `project.otx` byte-identical. It need not
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

- **In the Part** — every FX module's twelve parameters. Existing module research names the trap: a stored Part value has no
  schema tag that tells a changed effect how to interpret it. A Part saved under an older layout gives the new layout its old bytes,
  and a value outside the new count stalls the sequencer. Part parameters
  stay where they are. This proposal is for everything that is *not* a Part
  parameter.
- **Private files** — Octalab currently writes
  `<set>/<project>/octalab_grooves.map` ("OTGM" v1, up to 40,228 B) and
  `octalab_generators.map`. ✅ MKI 15 Sep 2026: survives a power cycle, a
  SYNC and a project change. Each file has its own magic, its own checksum,
  its own save trigger and its own loader. Octakit keeps its Kits in files of
  its own. As far as we know (26 Sep 2026), no other module keeps state on
  the card.
- **Nowhere** — Octalab's menu checkboxes (`SC PITCH [ ]`…) ship in the image
  and reset at every boot.

### 2.2 What the firmware already gives us

- **A storage task that can run our jobs.** ✅ MKI (Octalab v41). A Detour at
  `0x4008485e` gives the stock storage task a job type of our own (`0x40`).
  The job is posted from a UI timer, and before the stock jobs 7 (SYNC TO
  CARD), 0xb/0xc/0xd (project change), 0x11 (SAVE PROJECT) and 0x12 (SAVE
  BANK). Writes go through the stock buffered calls
  `0x40016864` open / `0x400166b8` write / `0x4001677c` close.
  Octalab removes the file and writes it again. **That is not safe against
  a power cut in the middle of a write**, which is one reason to replace it.
- **The project folder** is `"%s/%s"` of the set path `0x100f8480` and the
  project name `0x100f8378` ✅. `FUN_400255ec() != 0` means a project is
  open.
- **A fifth MAIN MENU root category** made only of data (✅ MKI 7 Sep 2026;
  the MAIN MENU analysis): a heading row has a null action and the cursor skips
  it; the rows carry their value in the label. A shared toggle routine finds
  the row from the descriptor's absolute selection at `+0x0c` (✅ MKI 8 Sep
  2026). There is **no free page id** for a stock-style settings page, so a
  list whose labels change is the widget.
- **The limit this removes.** ✅ the MAIN MENU analysis: "Two modules that both
  grow one submenu cannot coexist (the build refuses the second)". Each
  module that wants a row currently has to own a menu.

### 2.3 Prior art: how monome norns does it

norns offers useful prior art. This comparison draws on
[monome's parameter reference](https://monome.org/docs/norns/reference/params),
[mod documentation](https://monome.org/docs/norns/mods/) and the `paramset.lua`,
`state.lua` and `pmap.lua` files in [monome/norns](https://github.com/monome/norns)
(as read on 26 Sep 2026):

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
  Parts/Kits) is already the snapshot. The WORK / STORED slots below are
  recovery and save states, not presets the user selects.
- **no runtime enabling.** A module is in the image or it is not. The build
  does what `SYSTEM > MODS` does on norns.

---

## 3. The proposal

Four parts: declarations in module manifests, one shared core, one `.OTX`
container per scope, and one generated MODULES menu. The container owns
meta-settings only. A module owns the format of its separate creative files.

### 3.1 Modules declare settings; the core owns the shared file

Illustrative manifest syntax (an API proposal, not implemented):

```python
store=Store(id="org.octalab.usbaudio", scope=Scope.UNIT),
settings=(
    Setting(key=1, name="USB AUDIO", values=("OFF", "LIGHT", "FULL"),
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
- `scope=PROJECT` puts the module's block in that project's `project.otx`.
  `scope=UNIT` puts it in the shared `unit.otx` at the card root. One module
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

The build adds one DRAM core if any selected module declares settings. The
core owns the MODULES menu, both shared containers, the storage job, dirty
tracking, validation and safe writes. Modules never edit `.OTX` directly.
The build orders callbacks deterministically by module id and reports the
order. Proposed events: `unit_loaded`, `project_loaded`, `project_saving`,
`project_closing`, `setting_changed`.

**Preservation contract, required of every firmware that adopts `.OTX`:**

1. Load only a record whose module id and schema version the image knows.
   An absent module gets no callback and cannot block project load.
2. Keep every unknown module record as its **exact bytes**: header, full id,
   payload, flags and padding. Write those bytes back unchanged on every
   save. The same rule applies to a record from a newer, unsupported schema
   major. Do not silently drop an unknown record to make room.
3. Within a known module record, keep unknown setting TLVs as exact bytes
   when the module edits known keys. Missing settings take declared defaults;
   invalid known values take defaults without corrupting other modules.
4. If one module's payload or callback fails validation, run that module on
   defaults, show `LOAD ERR` on its heading, and continue loading the other
   valid modules. Preserve the failing record for diagnosis unless the user
   explicitly replaces it.
5. If a new snapshot cannot fit while preserving all opaque data, **fail the
   save visibly and keep the previous valid snapshot**. Never truncate an
   unknown record or treat its absence from the running image as deletion.

The core loads outside the audio ISR. A callback must be safe to call twice
with the same value. The `unit_loaded` event must occur before a setting can
affect USB descriptors; that boot ordering has not yet been measured (§5).
Writes run from the storage task, after edits when the sequencer is stopped
and before stock SYNC/SAVE/project-change jobs. They must not race CAPTURE or
recording CF writes. The exact schedule is a gate, not an assumption.

### 3.3 One shared container per scope

- `<set>/<project>/project.otx`: one file for **all installed and absent
  modules' PROJECT meta-settings** in that project.
- `/unit.otx` at the inserted CF card root: one optional file for **all
  modules' UNIT meta-settings**, shared across projects on that card. This
  does not follow the physical Octatrack when the card changes. With no
  readable card, use defaults; whether the USB preference needs different
  persistence remains open.

Both files use the same proposed binary TLV format. Integers are big-endian
on the ColdFire. A PROJECT file contains two WORK snapshots (A/B) and two
STORED snapshots (A/B); a UNIT file contains two snapshots (A/B). **Each
snapshot is a complete shared container**, not one slot per module. A save
writes the older slot of its kind, leaving the other valid slot intact. A
reader chooses the valid slot with the highest generation. `WORK` means the
current project state; SAVE PROJECT updates `STORED`; RELOAD PROJECT applies
`STORED`. Their exact transitions must be matched to stock behavior (§5).

The proposed file is preallocated once and overwritten in whole 512-byte
sectors, without rename or delete during a normal save. This method, its
capacity, and its behavior under a power cut are **unproven** on the MKI.
Each slot has a fixed `slot_bytes`; total file size is `4 × slot_bytes` for
PROJECT and `2 × slot_bytes` for UNIT. A slot starts with a bounded header:

```text
Slot header (32 bytes, proposed)
  0   char[4]  "OTX1"
  4   u16      header size = 32
  6   u8       format major = 1       7  u8  format minor = 0
  8   u8       kind (0 WORK, 1 STORED, 2 UNIT)
  9   u8       flags = 0              10 u16 reserved = 0
  12  u32      generation
  16  u32      used bytes (header + records, CRC excluded)
  20  u32      slot_bytes            24 u32 record count
  28  u32      reserved = 0
Records, bounded by `used`; one record per (module id, scope)
  0   u8       full id length (1..63)   1 u8 flags
  2   u16      schema major            4 u16 schema minor
  6   u16      reserved = 0
  8   u32      payload length         12 u32 payload CRC-32
  16  u32      record size (header + full id + payload + padding)
  20  byte[]   full namespaced ASCII module id, payload, 0..3 padding bytes
Then u32      slot CRC-32 (IEEE) over bytes 0 .. used-1
Rest            zero padding to `slot_bytes`
```

The CRC words are big-endian. `used + 4 <= slot_bytes`; lengths and record
counts must be checked before any allocation or callback. The **full** module
id is stored in each record, never an eight-byte prefix. Duplicate ids in
one snapshot invalidate those modules' records but do not erase their raw
bytes or stop other modules loading. A newer container major or an invalid
snapshot is not rewritten automatically; fall back to the other valid slot.

A known module's payload is a sequence of typed TLVs: stable `u16` key,
`u16` flags, `u32` length and value padded to four bytes. `Binary`/`Option`
values are one byte (at most 256 options); `Number` is a big-endian signed
16-bit value; bounded configuration blobs use their declared length. The
module record CRC isolates payload damage from other records. Unknown module
records and unknown inner TLVs are copied **byte for byte**, including their
padding. The reference tool and neutral test corpus (§5) must make that
promise executable, not merely descriptive.

If a future schema needs more space than the fixed slot allows, saving must
stop with a visible error while the previous snapshot stays readable. A
second-file migration and any deletion of an old file need their own tested
protocol; they are not part of draft 1. No module may solve the capacity
problem by writing a private `.otx` settings file.

### 3.4 One generated MODULES menu

The build emits one root category beside PROJECT / SYSTEM / CONTROL / MIDI
only when a selected module declares settings. The working name is
**MODULES**. Each present module gets a heading and rows generated from its
manifest; an absent module's stored record gets **no row**, while remaining
in the file:

```text
USB AUDIO                 <- heading, only in images with USB AUDIO
 PROFILE      LIGHT
OCTALAB
 SC PITCH     [X]
 FILL OVERWR  [ ]
```

`[ENTER]` advances an Option; Binary draws `[ ]` / `[X]`. When requested and
effective values differ, the row shows both (for example `FULL>OFF`). The
multi-value widget and maximum scrollable row count still need emulator and
MKI tests. No module has its own meta-settings root category.

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

The **shared container and module-owned creative files are the design rule**.
The open choices concern its safe encoding and integration:

1. Agree with other firmware authors on stable namespaced module ids, the
   `.OTX` name, the example header and the neutral test corpus. A firmware
   that does not implement the preservation contract cannot claim `.OTX`
   compatibility.
2. Implement `tools/hw/otx.py` on the computer: read, write, check and dump.
   Test known and absent modules, unsupported schema major, unknown inner
   key, duplicate id, invalid record CRC, torn slot, capacity overflow and
   **byte-identical unknown-record preservation after a known setting edit**.
3. Prove stock FS seek and fixed-sector overwrite in the emulator, then on a
   disposable MKI card. Test power cuts with both slots, exact file size,
   and that an overflow never rewrites the only valid snapshot.
4. Implement the shared core/menu in the emulator. Verify that project
   load, SAVE, RELOAD, change and rollback apply only the known blocks and
   leave absent-module records untouched. Match WORK/STORED timing to the
   stock project model.
5. Test stock SAVE TO NEW, COLLECT SAMPLES, EXPORT TO SET, PURGE and project
   copy. Determine whether they carry `project.otx`; if they do not, the
   shared core must copy the whole container, including unknown blocks.
6. Decide whether card-wide `unit.otx` is sufficient for UNIT settings or
   whether they must survive a CF card swap. Prove UNIT load and any USB
   profile application finish before the host reads descriptors. Until that
   point `NEXT_CONNECT` is only a requested behavior.
7. Test latency with several module records and the MKI's CF workload,
   including CAPTURE. Never perform `.OTX` I/O from an audio ISR.

---

## 6. What a module author does

- Declare a stable namespaced id, keys, defaults, scope and apply policy for
  **meta-settings**. Do not create a private `.otx` file, menu root or save
  hook for those settings.
- Keep grooves, Kits, presets and other transferable personal content in
  files whose format the module alone chooses and maintains. The shared
  settings core never dictates that format.
- Make callbacks idempotent and validate bounded blobs. A module only sees
  its own recognized record; it never parses another module's block.
- Add a neutral compatibility test: when this module is removed from an
  image, editing another module's setting and saving must preserve this
  module's complete record byte for byte.

## 7. Later, not in draft 1

Stable (module, key) addresses make a settings map possible, like norns'
`.pmap` for MIDI mappings: a MIDI CC or one of our USB vendor requests could
read or set any declared setting by address, with no code in the module.
For example, the computer could select the USB profile. Nothing here depends
on it.
