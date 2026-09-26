# USB input PR #468: buffer placement, latency, and test evidence

27 September 2026. This note reviews [Bryan Tysinger's draft PR #468](https://github.com/sambanks/octabam/pull/468), head `f1432c9d83b4596ba6c6274d5434a18ee7355c25`, against Octatrack OS 1.40C. It records what I checked locally and what remains for a MKI test. The USB input implementation belongs to Bryan's `usb-io` remix; it has not been integrated into Octalab.

## Evidence and limits

| Level | Observation |
|---|---|
| **CONFIRMED on Bryan's unit, as reported in the PR** | Four host channels reached A–D. Under a busy project, bad USB OUT packet completions went from 1,189/min with stock crossbar settings to 5–11/min with SCM bursting, then zero over ten minutes after assigning USB first priority on the SDRAM and SRAM crossbar slaves. This is strong evidence for a USB receive service problem, but the exact FIFO-overflow mechanism is still a hardware interpretation. |
| **CONFIRMED in PR source** | dTDs and USB OUT packet buffers occupy the top 1 KiB of on-chip SRAM, `0x80007c00..0x80007fff`. The 1,024-frame CPU ring remains in the DRAM unit's data area. The 256-byte DSP transfer buffer is also in DRAM, accessed through its uncached alias. Moving packet buffers to SRAM did not itself eliminate the bad packets; the crossbar changes did in Bryan's measurements. |
| **CONFIRMED locally, without USB hardware** | The exact PR head built as `usb-io`, version `OCTABAM94`; BIN packaging passed its checksum and round-trip check. Static descriptors have six interfaces, high-speed EP3 OUT at 192 B/250 µs and EP3 IN marked as implicit feedback. The FX menu check and static cycle report passed. An older local ColdFire port booted the image, ran the DRAM loader once and read back the linked runtime exactly. |
| **UNVERIFIED locally** | The PR's own USB OUT emulator gate and complete `make check` gate. The local `dsp56300` is older than the PR pin, so the PR port does not compile here; `make check` stops in the shared stock FLANGER self-test using the older local `dsp_host`. No USB input hardware result is claimed for this particular local build. |

## Where the latency comes from

`OUT_TARGET=384` makes the host-to-OT ring prefill by at least 384 frames before it plays. At 44.1 kHz that is **8.71 ms**. The ring capacity of 1,024 frames (23.22 ms) is a bound on storage, not its normal delay. The 16-frame DSP block is 0.36 ms; USB packet scheduling, the host audio stack and the rest of the OT signal path add more. No end-to-end latency has been measured here.

The outgoing OT-to-host path has `AUD_TARGET=512` (11.61 ms) and a servo deadband `AUD_BAND=128` (±2.90 ms). The host uses that outgoing stream as implicit feedback for its incoming packets. Consequently its fill variation can propagate into the OUT ring. `AUD_TARGET` is directly a delay in the **OT-to-host** direction; treating it as another fixed 11.61 ms added to the **host-to-OT** direction would overstate the latter. Reducing it may help round-trip monitoring and change the incoming stream's dynamics, but it needs a separate measurement.

Bryan's suggested targets have these nominal OUT-ring cushions: 128 frames = 2.90 ms; 64 frames = 1.45 ms. The source comments estimate that the current ±128-frame servo band can let the OUT fill swing over roughly 256 frames. A 64- or 128-frame target with that band may underrun even with zero bad USB packets. The `minfill`/`maxfill` counters are sampled while consuming, after prefill; an underrun resets prefill. Read them together with `underruns`, `overruns`, `bad`, `err`, `partial`, `dry`, `late`, and the USB IN counters, over a sustained host stream. An idle emulator run alone cannot set a safe target for a busy MKI.

## Proposed sequence for latency work

1. **Baseline on the exact PR build:** keep both audio directions open, route a distinct signal to each A–D input, record the USB IN and OUT counters for at least ten minutes idle and under a busy project, then measure a host-output → OT-DIR/MAIN → host-input impulse loop. Record the host interface, buffer size and sample rate. Repeat after stopping and reopening the stream, a project load, CF writes, and a USB disconnect. Note whether physical A–D jacks return when the stream closes.
2. **Change `OUT_TARGET` alone**, using the lowest sustained `minfill` and a margin for unobserved host and CF stalls. Test 256, then 128 only if the measured margin supports it. Compare the same impulse route and counters. The existing PR data are insufficient to recommend 64 frames.
3. **Tighten `AUD_BAND` separately**, checking for servo hunting, alternating packet sizes, USB IN underruns/overruns, and OUT fill excursions. Only then consider lowering `AUD_TARGET`; that target mainly reduces OT-to-host latency and protection against producer stalls. Use one parameter change per build so a regression has a cause.

The packet-error fix and latency tuning should remain separate experiments. A zero `bad` count does not prove zero ring underruns or low round-trip latency.

## Open PR issues before broad use

- **DISK MODE:** Bryan reports a failure on an earlier image; the current head has not been retested. Check transition into and out of DISK MODE after a streaming session on a disposable card/project.
- **USB state:** full-speed OUT is advertised but not served. `GET_INTERFACE(5)` reports alt 0 while alt 1 streams. `SET_INTERFACE(5)` also accepts any nonzero alt as 1. These need specification-correct handling or an explicit supported-speed limit.
- **Global bus priority:** `out_up` enables SCM bursting and gives USB first priority on two crossbar slaves; `out_down` does not restore the stock settings. The packet result is compelling, but CAPTURE/CF-write and UI responsiveness under this priority have not been measured on our MKI.
- **SRAM claim:** the top 1 KiB was checked statically and under Bryan's port workloads. Recheck it during DISK MODE, CF activity and the configurations intended to be supported on hardware.
- **Diagnostic vendor requests:** the draft exposes peripheral reads and allowlisted register writes over USB. They are useful for experiments; shipping code should remove or tightly gate them.
- **Integration:** this `usb-io` build has no Octalab or CAPTURE. Four-channel recording during CAPTURE requires a later combined image and its own stress test.

No firmware image or stock OS bytes are published with this note.
