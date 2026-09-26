# USB audio into Octatrack A/B/C/D — WIP findings

26 September 2026. Target: Octatrack MKI, stock OS 1.40C as the base image.
This is a research handoff, **not an implemented or hardware-tested USB input
feature**. Confidence labels distinguish a DSP emulator observation from a
working path on the unit.

For the output-only baseline and MKI responsiveness report, see
[USB AUDIO LIGHT WIP](USB_AUDIO_LIGHT_WIP.md).

| Status | Finding |
|---|---|
| **CONFIRMED in DSP emulation only** | Four independent two-second tone probes on the `OLB91` image (`out/olb91.os`) supplied 440, 660, 880 and 1100 Hz to the A, B, C and D ESAI RX callbacks respectively. With test routing, each tone reached MAIN (`--expect-tone`, detection ratio 0.950 in each run). This demonstrates a DSP receive path for samples presented before ESAI RX consumption. It does **not** demonstrate transfer from USB or the ColdFire to that point. |
| **CONFIRMED in the current code** | `OL92U` has no USB AudioStreaming OUT interface. `OL93L` is a four-channel MAIN/CUE **output-only** LIGHT image; it adds no USB audio input. Neither image makes USB audio available as an A/B/C/D source. |
| **STRONG HYPOTHESIS from OS 1.40C DSP analysis** | A receive ring is read before the input conditioner in DSP core 0, program A. Supplying or substituting four samples at this earlier boundary may let the existing A/B/C/D signal paths consume them. The readback window at ColdFire addresses `0x80005460..0x80005e60` is downstream of DSP transfer; writing there cannot establish that machines, DIR, THRU or the input conditioner receive USB samples. The candidate boundary has not been patched or measured on MKI. |
| **UNKNOWN** | A safe DSP buffer and injection site; a timed ColdFire-to-DSP transfer; actual A/B/C/D mapping and input gain behavior on MKI; routing to machines, recorder and CAPTURE; sustained duplex performance and latency. |

A host-to-device implementation would still need a USB AudioStreaming OUT
interface and isochronous OUT endpoint, receive buffering, clock-drift and
overrun handling, and validated DSP delivery. The local USB emulator currently
models EP0–EP3 only; this is an **emulator limit**, not proof of a hardware
endpoint limit. Asynchronous UAC2 OUT compatibility with Windows also needs
explicit feedback; see [Microsoft's UAC2 driver documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/usb-2-0-audio-drivers).

A first routing proposal is to select **JACK or USB per A/B and C/D pair**,
with JACK as the default, then feed the existing A/B/C/D paths before DSP
input processing. That would avoid changing every source table at once. This
is a proposal, not a demonstrated route, and does not provide simultaneous
independent jack and USB sources.

The next decisive evidence is a MKI test that traces four distinct incoming
tones through DIR/THRU, machines, recorder and CAPTURE while checking sample
loss, drift, DSP headroom and behavior on disconnect and DISK MODE. No USB
INPUT build or MKI USB INPUT result is claimed here.
