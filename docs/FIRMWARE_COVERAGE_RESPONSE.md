# OCTALAB findings relevant to the firmware coverage review

This short note responds to *Octatrack firmware coverage: manual vs. octabam
docs* (21 September 2026). It lists findings from OCTALAB's own work that
partly answer gaps in that review. It does not claim that any whole subsystem
is mapped.

**Image identity:** stock OS 1.40C, MAIN OS SHA-256
`164f31224bf61181e3f50e7dec40df9afcae5b16dbf6e4c0d0cc5e986af0a84e`, 1,112,560
bytes, load base `0x40000400`. Addresses below refer to that image unless
identified as RAM. ✅ marks a directly decoded path or a result observed on a
MKI; 🟡 marks a tentative interpretation or an emulator-only measurement
awaiting an isolated hardware test. A row can contain both.

| Gap | OCTALAB finding | Boundary |
|---|---|---|
| Sequencer steps and locks | ✅ Four placeable trig masks each cover 64 steps; the exact name of the `+0x10` type remains 🟡. The per-step record is 32 bytes; byte 31 is the sample lock. The stock sample-lock store `0x40040ee0` works outside the picker on a MKI. [Trig evidence](TRIGS.md) | The step evaluator and full scheduling path remain open. |
| Pattern length and scale | 🟡 The SCALE page reads normal-mode length/scale at `pattern + 0x8e53/+0x8e54`, per-track length/scale at `TRAC + 0x50/+0x51`, and master length at `pattern + 0x8e50`. [Field map](FINDINGS.md#pattern-length-and-scale--code-read) | Pattern chaining and the complete SCALE-menu write path remain open. |
| Card filesystem | ✅ The live FAT implementation has a 23-slot vtable at `0x46c823fa`; the stock sample path calls the recursive directory walker `0x40090a14`. [Filesystem evidence](FS_LAYER.md) | This does not map the entire FAT implementation or card timing. |
| STATIC sample loading | ✅ The storage job follows `ot_static_slot_load` with post-load setup and refreshes. Without these, a slot can display its name but cannot preview or trig; verified on a MKI. [Loading evidence](SLOT_LOADING.md) | Real-time STATIC streaming remains open. |
| Recorder reservation | 🟡 In an emulated project, each of eight recorders held 460 blocks of `0x1800` bytes: 2,826,240 bytes, or 16.0 seconds of 16-bit stereo at 44.1 kHz. The length and cap arrays are at `0x461053a8` and `0x461053e8`. [Findings](FINDINGS.md) | This measures one default project configuration in an emulator, not every recorder setting on hardware. |
| Audio editor and saving | ✅ [TRIG]+[BANK] opened the stock audio editor on a held trig's sample or the track sample on a MKI. CAPTURE's stock WAV save path wrote real audio on the unit. The writer `0x40024168` takes its object from RAM globals `0x460be9e8` (kind) and `0x460be9ec` (object); leaving these unset produced header-only WAV files, then setting them before each job fixed the failure on the unit. [Editor](INPUT.md) · [saving](FINDINGS.md) | The editor's internal edits and all storage-job completion paths remain open. |

The [findings index](FINDINGS.md) also covers input-map layers and Part,
pattern, and SRAM copies. Those refine areas the review already describes as
relatively well covered. Its main open questions, notably per-step evaluation
and the end-to-end audio frame pipeline, remain open for OCTALAB too.
