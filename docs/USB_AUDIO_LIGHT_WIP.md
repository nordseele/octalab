# USB AUDIO LIGHT — four-channel output baseline (WIP)

26 September 2026 · Octatrack MKI · OS 1.40C-derived `OL93L`.
This note is for anyone continuing the USB audio work. No firmware image is
published here.

## What LIGHT does

**CONFIRMED in the build:** LIGHT sends four 24-bit audio channels from the
Octatrack to the computer at 44.1 kHz: MAIN L/R on channels 1/2 and CUE L/R
on channels 3/4. Its audio producer copies these four channels per frame,
instead of the 20 channels copied by the earlier `OL92U` FULL variant (eight
stereo track pairs plus MAIN/CUE). The unused 20-channel producer was removed.
This substantially reduces the amount of audio data handled by that producer;
its exact CPU saving has not been measured.

**CONFIRMED in emulation:** with the corrected 1 kHz USB bench, 800/800 audio
packets were delivered (704 or 720 bytes), with no empty packets, underruns
or overruns. MIDI, disk-mode descriptors and audio alt 0 passed the same bench.
The DRAM boot and Octalab functional gates passed before packaging.

**MKI user report:** with Ableton tracks open during a demanding CAPTURE test,
`OL93L` feels **much lighter and more responsive** than the previous 20-channel
USB build. HOLD had no UI freezes and card saves were fairly quick. CHOP also
worked; at `SLICE ADDED`, the VU meter and millisecond counter paused briefly,
which the user found tolerable. The earlier `OL92U` had severe UI freezes and
audio dropouts under the heavy comparison workload. This is a qualitative
hardware result, not a measured CPU profile or a verified USB stream-state
trace.

## Boundary for the next contributor

`OL93L` is **output only**. It has no computer-to-Octatrack audio stream, no
A/B/C/D USB input routing, and no OFF/LIGHT/FULL menu switch. For the incoming
audio path, see the separate [USB INPUT A/B/C/D WIP findings](USB_AUDIO_INPUT_WIP.md).
A shared `.OTX` settings format has been [proposed](OTX_PROJECT_PROPOSAL.md),
but is not implemented in this image.
