# Audio input LED meters

Stock Octatrack OS 1.40C, MAIN OS SHA-256
`164f31224bf61181e3f50e7dec40df9afcae5b16dbf6e4c0d0cc5e986af0a84e`,
1,112,560 bytes, image base `0x40000400`.

## The meter path ✅ code and emulator

`FUN_40040938` is the input LED meter painter. It reads six 32-bit level
values at `0x800000f0..0x80000104`. The MKI uses the first four; a model
flag at `0x46c8d18c` enables all six on the MKII. For each value, the
painter finds the leading set bit and looks up two 4-bit brightness levels
in a table at `0x400a72e8`. It sends those levels to the two dies of a
bi-colour LED through `FUN_400135b0` (the brightness setter documented by
octamax). Thus both colour and intensity follow the audio level.

The LED base ids, in level-word order, are held at `0x400a72d0`:

| Level word | LED base id | Model |
|---|---:|---|
| `0x800000f0` | `0x38` | MKI and MKII |
| `0x800000f4` | `0x3a` | MKI and MKII |
| `0x800000f8` | `0x3e` | MKI and MKII |
| `0x800000fc` | `0x3c` | MKI and MKII |
| `0x80000100` | `0x80` | MKII only |
| `0x80000104` | `0x82` | MKII only |

The audio routine around `0x4000d562` updates these six words using MAC
instructions. The meter painter is reached through a callback at
`0x4002edfc` (pointer at `0x400ba4b2`), which calls it when the recorder
arming/configuration flags are clear. The separate arming painter
`FUN_4002ebb0` uses the same LEDs; following only that painter misses the
audio meter. Ghidra's initial analysis had not defined the callback as a
function.

The corresponding code, callback pointer and LED tables are byte-for-byte
identical in the stock image and in the OL90U image reported as flashed on
the owner's MKI. This confirms that the identified driver is present in that
build; it does not establish the mapping of physical input jacks.

With stock OS 1.40C running under octemu in MKI mode, a tone placed on one
ESAI RX0 slot at a time made exactly one level word nonzero and brightened
its corresponding LED id:

| Emulator RX0 slot | Level word | LED base id |
|---:|---|---:|
| 0 | `0x800000fc` | `0x3c` |
| 1 | `0x800000f0` | `0x38` |
| 2 | `0x800000f4` | `0x3a` |
| 3 | `0x800000f8` | `0x3e` |

## Physical mapping still open 🟡

The owner observes the MKI's A/B/C/D LEDs changing colour and intensity
with input level. The *addresses* above are established by code and
emulation, not by reading memory on a physical unit. Octemu's input names
refer to ESAI slots; they do not establish which physical jack is A, B, C
or D. The individual jack-to-word mapping, the numerical scale, and the
effect of the MIXER's input GAIN on these words remain unmeasured on the
MKI. A separate known discrepancy between DSP slot naming and the
ColdFire recorder's AB/CD pair naming makes a physical mapping from the
emulator alone unsafe.

The MKII-only pair may correspond to its INT L/R indicators, but that
identification and their audio tap point remain hypotheses; no MKII
hardware measurement is reported here.
