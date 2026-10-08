# Trig modes — the stock popup, its tables and its state

What the stock firmware does when `[FUNCTION] + [UP]/[DOWN]` changes what the
sixteen trig keys do (TRACKS, CHROMATIC, SLOTS, SLICES, QUICK MUTE, DELAY
CTRL), for anyone who wants to read, extend or replace a trig mode.

Everything here is read out of OS 1.40C on the MKI (`sha256 164f3122…`, base
`0x40000400`). ✅ = read in the image or confirmed by running the stock code in
an emulator; 🟡 = inferred, with what would settle it. Nothing here was checked
on a MKII.

---

## 1. State ✅

| address | width | what |
|---|---|---|
| `0x460d16f0` | long | the active trig mode, a mode id (below) |
| `0x460d1736` | long | grid recording: non-zero while `[RECORD]` grid recording is on |
| `0x400bebae` | long | the trig mode popup's handle: 0 while it is closed |
| `0x46c7d330` | struct | the stock list object the popup uses: `+0x00` first visible row, `+0x08` selected row, `+0x0c` visible rows (3), `+0x10` row count |

🟡 `0x80000012` reads as the current track's kind (0 audio, non-zero MIDI) —
inferred from the popup choosing the MIDI table on it; not cross-checked.

🟡 `0x460d16f0` has many readers (about twenty references), among them the trig
LED view `0x40043fdc`. octamax uses the same cell as "the FUNC+[down] view
index, 3 = SLICES". **Writing a value outside the stock ids is not shown to be
safe**: nobody has followed every reader, nor checked whether the value is
saved with the project.

## 2. Tables ✅

Mode ids, as long words:

| table | entries |
|---|---|
| `0x400a74a8` audio tracks | `0 1 2 3 4 5` |
| `0x400a74c0` MIDI tracks | `0 1 4` |

A mode id indexes both following tables. On a MIDI track the popup therefore
offers TRACKS, CHROMATIC and QUICK MUTE.

| id | label pointer (`0x400beb72 + id*4`) | string | icon pointer (`0x400beb8a + id*4`) |
|---:|---|---|---|
| 0 | `0x400b5f4b` | `TRACKS` | `0x400beaaa` |
| 1 | `0x400b5366` | `CHROMATIC` | `0x400beae6` |
| 2 | `0x400b5370` | `SLOTS` | `0x400bea82` |
| 3 | `0x400b6cb9` | `SLICES` | `0x400bea96` |
| 4 | `0x400b5376` | `QUICK MUTE` | `0x400beabe` |
| 5 | `0x400b5381` | `DELAY CTRL` | `0x400bead2` |

The scroll arrows drawn in the popup are the one-character strings at
`0x400b4315` (up) and `0x400b4317` (down).

## 3. The popup ✅

Its three callbacks sit side by side: opener `0x400586cc` (pointer at
`0x400bebca`), closer `0x40055e70` (`0x400bebce`), redraw `0x400359ac`
(`0x400bebd2`).

- **Open**: a second call while it is open closes it (toggle). It allocates the
  window (`0x4005829c`), stores the handle at `0x400bebae`, registers the
  popup's input map `0x400bebb2` (`0x40031494`), initialises the list object
  (`0x4007ec60`, count 6 audio / 3 MIDI, 3 visible), selects the active mode
  (`0x4007edb0`), then redraws.
- **Redraw**: clears the inner rectangle (`0x40012254`). For each visible row
  it reads the mode id from the table, draws the icon (`0x400128a8`) and the
  label (`0x40012bd8`, font `0x400ba88a`), then the scroll arrows and the
  inverted selection bar. It sets the screen dirty flag `0x46c7c72c`.
- **Close**: frees the window (`0x40055db4`), unregisters `0x400bebb2`
  (`0x4003146c`) and clears the handle.

The row count is a parameter of the list initialisation and the labels come
from the tables above, both indexed by mode id. A seventh row therefore needs
its own redraw: the stock one would read past both six-entry tables.

## 4. How `[FUNCTION] + [UP]/[DOWN]` gets there ✅

`0x40051fc4` handles `UP` (`0x33`) and `DOWN` (`0x20`) with
`(code, down)` on the stack. It is reached through the stock FUNCTION
sub-map. Confirmed in the emulator: the dispatcher registers the sub-maps of
every layer before it calls a handler, so the combination still arrives when
a map higher up consumes the FUNCTION press itself.

- Popup closed, press: opens it.
- Popup open: `UP` steps through `0x40051f54` (list step `0x4007ec7c`),
  `DOWN` through `0x40051ee4` (`0x4007eca4`). Each step writes
  `0x460d16f0` from the table, then redraws.

🟡 The step is taken on the press only, read from the code. A replacement that
also steps on the release moves two rows per touch; this was seen in the
emulator with a non-stock handler.

## 5. Trig keys under a mode 🟡

Outside grid recording, trig presses go through `FUN_400501d8`, which branches
on `0x460d16f0`. This was read from the code, not decompiled in full. What it
does for an id it does not know is **unproven**.

## 6. Trig LEDs 🟡

Each trig has a red/green pair. The ids `trig*2` (red) and `trig*2 + 1`
(green) are inferred and not confirmed on a unit; the track LEDs are
`40 + track*2` (octamax). Primitives: on `0x400131a0 (id)`, off
`0x400131c8 (id)`, level `0x400135b0 (id, 0..15)`, flush `0x400136a8 ()`.
The stock trig LED painter is entered at `0x40034bd4`. A LED written outside
it is repainted by the stock and lost on the unit: paint after it, from
inside it.

## 7. Two dispatcher facts that matter to any layer over the trigs ✅

Both confirmed by driving the real dispatcher (`0x40031734`) in an emulator.

- **A map is a chain link of 26-byte key records** (code, 0, press, release,
  repeat, …, ending at code `0xff`). The chain is walked from its head; a
  later record overrides an earlier one unless its field is `-1` (pass to the
  layer below). A `0` field swallows the key. A map registered for the trig
  row therefore also takes any other key it lists, such as UP/DOWN, FUNCTION
  or NO, unless it hands those on.
- **A held key keeps the release handler chosen at its press**: the rebuild
  skips keys that are down. A layer that took a press receives its release
  even if another map has been registered on top meanwhile.
