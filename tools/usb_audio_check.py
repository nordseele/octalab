#!/usr/bin/env python3
"""Portable, bounded output-only Octatrack USB AUDIO diagnostic. See docs/USB_AUDIO_CHECK.md."""
import argparse
import datetime
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import time

RATE = 44100
NAMES = {
    'ep3_in': ('consumed', 'acc', 'overruns', 'underruns', 'lastn', 'lastfill',
               'lastbank', 'bankdup', 'lastsamp', 'srcjump', 'reprimes', 'minfill',
               'maxfill', 'anchor', 'produced'),
    'ep3_out': ('produced', 'consumed', 'pkts', 'lastn', 'lastfill', 'underruns',
                'overruns', 'reprimes', 'bad', 'frames', 'seconds', 'minfill',
                'maxfill', 'err', 'partial', 'errmask', 'lasttok', 'lastslot',
                'depth', 'badfr', 'badfr_prev', 'dry', 'late', 'maxpass',
                'good_nz', 'bad_nz', 'bad_nzw', 'last_nzw'),
}
ERRORS = ('overruns', 'underruns', 'reprimes', 'bankdup', 'srcjump', 'bad', 'err', 'partial')
CUMULATIVE = ('produced', 'consumed', 'pkts') + ERRORS
WARNING = ('No input captured: routing A-D and continuous analogue audio require human observation. '
           'Output-only may activate driver duplex/implicit feedback. Ring consumed includes '
           'anchors/overflow/packet preparation: it is NOT completed USB bytes. No bus-rate verdict.')


def stamp():
    return {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'monotonic': time.monotonic()}


def diagnostic(exc):
    # No traceback, user paths, USB serial or hostname in the portable report.
    text = str(exc).replace(str(Path.home()), '<home>')
    text = re.sub(r'(?:[A-Za-z]:[\\/]|/)[^\s\'\"]+', '<path>', text)
    return {'type': type(exc).__name__, 'message': text}


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def decode(key, raw):
    minimum = 12 if key == 'ep3_in' else 15
    if len(raw) % 4 or len(raw) < minimum * 4:
        raise ValueError(f'{key}: short/misaligned counters ({len(raw)} bytes; minimum {minimum * 4})')
    longs = struct.unpack('>' + 'I' * (len(raw) // 4), raw)
    return {'schema_longs': len(longs), 'values': dict(zip(NAMES[key], longs)),
            'unknown_tail': list(longs[len(NAMES[key]):])}


def summarize(rows, report):
    """Only polls fully inside the actual started stream contribute deltas."""
    active = [r for r in rows if r.get('phase') == 'stream']
    summary = {'active_polls': len(active), 'directions': {}, 'flags': []}
    observed = bool(report.get('callback_status'))
    incomplete = report.get('result') != 'completed' or len(active) < 2 or bool(report.get('truncated_sample_line'))
    if report.get('preflight'):
        summary['flags'].append('preflight_has_no_audio_test')
    for key in NAMES:
        good = [r[key] for r in active if r.get(key, {}).get('values')]
        missing = len(active) - len(good)
        changes = {k: 0 for k in ERRORS if any(k in g['values'] for g in good)}
        resets, anchors, intervals = [], [], []
        for prev, now in zip(active, active[1:]):
            p, n = prev.get(key, {}), now.get(key, {})
            if not p.get('values') or not n.get('values'):
                continue
            a, b = p['values'], n['values']
            reset = [k for k in CUMULATIVE if k in a and k in b and b[k] < a[k]]
            anchor = 'anchor' in a and 'anchor' in b and a['anchor'] != b['anchor']
            if reset:
                resets.append({'monotonic': n['monotonic'], 'fields': reset})
            if anchor:
                anchors.append(n['monotonic'])
            growth = {k: b[k] - a[k] for k in changes if k in a and k in b and b[k] >= a[k]}
            for k, v in growth.items():
                changes[k] += v
            intervals.append({'start': p['monotonic'], 'end': n['monotonic'],
                              'reset_or_wrap': reset, 'anchor_changed': anchor,
                              'error_growth': growth,
                              'ring_rate_valid': False})
        observed |= any(v > 0 for v in changes.values())
        incomplete |= missing > 0 or len(good) < 2 or bool(resets) or bool(anchors)
        # A missed/restarted stream between snapshots may still be invisible.
        states = {k: {'first': good[0]['values'][k], 'last': good[-1]['values'][k]}
                  for k in ('minfill', 'maxfill', 'lastfill', 'anchor')
                  if good and k in good[0]['values'] and k in good[-1]['values']}
        summary['directions'][key] = {'valid_polls': len(good), 'missing_polls': missing,
            'observed_positive_error_growth': changes, 'resets_or_wraps': resets,
            'anchor_changes': anchors, 'states_not_deltas': states, 'intervals': intervals}
    if any(b['monotonic'] - a['monotonic'] > 2 for a, b in zip(active, active[1:])):
        incomplete = True
        summary['flags'].append('poll_gap_over_2s')
    if report.get('poll_errors'):
        incomplete = True
        summary['flags'].append('counter_poll_failed')
    summary['verdict'] = ('OBSERVED_ERRORS' if observed else
                          'INCONCLUSIVE' if incomplete else 'NO_ERROR_OBSERVED')
    summary['warning'] = WARNING
    return summary


def worker(args):
    base = Path(args.output)
    report_path = base / 'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    rows, stream = [], None
    def checkpoint():
        save(report_path, report)
    def event(name):
        report.setdefault('markers', []).append({'event': name, **stamp()})
        checkpoint()
    def poll(phase):
        row = {'phase': phase, **stamp()}
        for key, req, length in [('ep3_in', 0x55, 60), ('ep3_out', 0x56, 112)]:
            entry = stamp()
            try:
                raw = bytes(dev.ctrl_transfer(0xc0, req, 0, 0, length, timeout=500))
                entry['raw_hex'] = raw.hex()
                entry.update(decode(key, raw))
            except Exception as exc:
                entry['error'] = diagnostic(exc)
                report.setdefault('poll_errors', []).append({'direction': key, **entry})
            entry['monotonic_end'] = time.monotonic()
            row[key] = entry
        # A poll that overlaps stream completion is excluded from stream deltas.
        if phase == 'stream' and not stream.active:
            row['phase'] = 'stream_end_overlap'
        rows.append(row)
        with (base / 'samples.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            handle.flush()
        checkpoint()
    try:
        import numpy as np
        import sounddevice as sd
        import usb.core
        import usb.backend.libusb1
        report['dependencies'] = {p: importlib.metadata.version(p) for p in ('numpy', 'sounddevice', 'pyusb')}
        report['portaudio'] = sd.get_portaudio_version()
        library = os.environ.get('LIBUSB_LIBRARY')
        backend = usb.backend.libusb1.get_backend(find_library=lambda _: library) if library else usb.backend.libusb1.get_backend()
        if backend is None:
            raise RuntimeError('libusb backend unavailable; use system library search path (see checklist)')
        devices = list(sd.query_devices())
        hosts = sd.query_hostapis()
        report['audio_devices'] = [dict(d, index=i, host_api_name=hosts[d['hostapi']]['name'])
                                   for i, d in enumerate(devices)]
        matches = [i for i, d in enumerate(devices) if args.device.casefold() in d['name'].casefold()
                   and d['max_output_channels'] > 0]
        if len(matches) != 1:
            raise RuntimeError(f'Expected one matching output device, found {len(matches)}; use --list-devices / --device')
        index = matches[0]
        nch = int(devices[index]['max_output_channels'])
        if nch not in (2, 4):
            raise RuntimeError(f'Expected a 2/4 output profile, advertised {nch}; select correct firmware/profile')
        if max(args.channels) > nch:
            raise RuntimeError('Selected channel exceeds advertised outputs')
        report['selected_device'] = report['audio_devices'][index]
        report['output_channels'] = nch
        sd.check_output_settings(device=index, channels=nch, dtype='float32', samplerate=RATE)
        units = list(usb.core.find(find_all=True, idVendor=0x1935, idProduct=0x0002, backend=backend))
        if len(units) != 1:
            raise RuntimeError(f'Expected one USB Octatrack 1935:0002, found {len(units)}')
        dev = units[0]
        report['usb'] = {'vid': dev.idVendor, 'pid': dev.idProduct, 'bcd_device': dev.bcdDevice,
                         'bcd_usb': dev.bcdUSB, 'speed': getattr(dev, 'speed', None)}
        poll('baseline')  # EP0 device requests only; never claim/configure/detach.
        if args.preflight:
            report['result'] = 'preflight_completed'
            return
        total = round(args.duration * RATE)
        position = 0
        statuses = []
        def callback(outdata, frames, timing, status):
            nonlocal position
            if status:
                statuses.append(str(status))
            outdata.fill(0)
            count = min(frames, total - position)
            if count > 0:
                t = (np.arange(count, dtype=np.float64) + position) / RATE
                tone = (10 ** (args.level_dbfs / 20) * np.sin(2 * np.pi * args.freq * t)).astype(np.float32)
                for channel in args.channels:
                    outdata[:count, channel - 1] = tone
                position += count
            if position >= total:
                raise sd.CallbackStop
        t0 = time.monotonic()
        event('stream_open_requested')
        stream = sd.OutputStream(device=index, samplerate=RATE, channels=nch,
                                 dtype='float32', callback=callback)
        report['negotiated'] = {'sample_rate': stream.samplerate, 'channels': stream.channels,
                                 'latency_s': stream.latency}
        stream.start()
        event('stream_started')
        while stream.active:
            poll('stream')
            time.sleep(0.1)
        report['stream_wall_s'] = time.monotonic() - t0
        report['requested_over_wall_informational'] = args.duration / report['stream_wall_s']
        report['callback_status'] = statuses
        report['submitted_frames'] = position
        event('stream_inactive_observed')
        event('stream_close_requested')
        stream.close()
        stream = None
        event('stream_closed')
        poll('after_close')
        report['result'] = 'completed'
    except Exception as exc:
        report['result'] = 'failed'
        report['error'] = diagnostic(exc)
    finally:
        if stream is not None:
            event('cleanup_close_requested')
            stream.abort()
            stream.close()
            event('cleanup_closed')
        report['summary'] = summarize(rows, report)
        checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-devices', action='store_true')
    parser.add_argument('--preflight', action='store_true', help='metadata/EP0 only; no audio stream')
    parser.add_argument('--unit', choices=('mki', 'mkii'))
    parser.add_argument('--build-note', help='firmware/profile reference, no personal data')
    parser.add_argument('--connection-note', default='unspecified', help='direct/hub/cable description, no personal data')
    parser.add_argument('--output', help='new report directory (refuses existing files)')
    parser.add_argument('--duration', type=float, default=3)
    parser.add_argument('--channels', default='1,2')
    parser.add_argument('--device', default='Octatrack')
    parser.add_argument('--freq', type=float, default=440)
    parser.add_argument('--level-dbfs', type=float, default=-26)
    parser.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.list_devices:
        try:
            import sounddevice as sd
            for i, d in enumerate(sd.query_devices()):
                print(f"{i}: {d['name']} | input={d['max_input_channels']} output={d['max_output_channels']} | default Hz={d['default_samplerate']}")
            return 0
        except Exception as exc:
            print(json.dumps(diagnostic(exc)))
            return 2
    if not args.unit or not args.build_note or not args.output:
        parser.error('--unit, --build-note and --output required')
    if not math.isfinite(args.duration) or not 0 < args.duration <= 30:
        parser.error('--duration must be >0 and <=30 seconds')
    if not math.isfinite(args.freq) or not 0 < args.freq < RATE / 2:
        parser.error('--freq must be >0 and <22050 Hz')
    if not math.isfinite(args.level_dbfs) or not -100 <= args.level_dbfs <= -6:
        parser.error('--level-dbfs must be between -100 and -6')
    try:
        channels = [int(x) for x in args.channels.split(',')]
        if not channels or len(set(channels)) != len(channels) or any(c not in range(1, 5) for c in channels):
            raise ValueError()
    except ValueError:
        parser.error('--channels: unique comma-separated outputs 1..4')
    if args._worker:
        args.channels = channels
        worker(args)
        return 0
    base = Path(args.output)
    base.mkdir(parents=True, exist_ok=True)
    if any((base / name).exists() for name in ('report.json', 'samples.jsonl', 'result.txt')):
        parser.error('output directory already contains a report; choose a new directory')
    report = {'format_version': 1, **stamp(), 'unit_declared': args.unit,
              'build_note_declared': args.build_note, 'connection_note_declared': args.connection_note, 'preflight': args.preflight,
              'host': {'os': platform.system(), 'release': platform.release(),
                       'os_version': platform.mac_ver()[0] if platform.system() == 'Darwin' else platform.version(),
                       'architecture': platform.machine(), 'python': platform.python_version()},
              'parameters': {'duration_s': args.duration, 'sample_rate': RATE,
                             'channels': channels, 'freq_hz': args.freq, 'level_dbfs': args.level_dbfs},
              'warning': WARNING, 'result': 'starting'}
    save(base / 'report.json', report)
    (base / 'samples.jsonl').touch()
    limit = min(70, max(20, args.duration * 2 + 10))
    print(f'Own child bounded to {limit:g}s; output only, keep monitor volume low.', flush=True)
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], '--_worker'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    stopped = None
    try:
        child.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        stopped = 'own_child_timeout'
        child.kill()
        child.wait()
    except KeyboardInterrupt:
        stopped = 'interrupted'
        child.kill()
        child.wait()
    report = json.loads((base / 'report.json').read_text(encoding='utf-8'))
    rows = []
    for line in (base / 'samples.jsonl').read_text(encoding='utf-8').splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            report['truncated_sample_line'] = True
    if stopped:
        report['result'] = stopped
    elif child.returncode != 0:
        report['result'] = 'own_child_failed'
        report['child_returncode'] = child.returncode
    report['watchdog_limit_s'] = limit
    report['summary'] = summarize(rows, report)
    save(base / 'report.json', report)
    result = f"{report['summary']['verdict']} (result={report['result']}, active polls={report['summary']['active_polls']})\n{WARNING}\n"
    (base / 'result.txt').write_text(result, encoding='utf-8')
    print(result, end='')
    return 0 if report['summary']['verdict'] == 'NO_ERROR_OBSERVED' else 2


if __name__ == '__main__':
    sys.exit(main())
