"""Fragmented fixed U-Boot transcripts; never opens a production serial port."""
from collections import deque
from pathlib import Path
import unittest
from scripts import sv08_serial_boot_route as route


class Transcript:
    def __init__(self, *, count=route.SCRIPT_BYTES, digest=route.SCRIPT_SHA, sd=True):
        self.queue=deque([b'U-Boot 2026.07\r\nHit any key to stop autoboot:  3 '])
        self.writes=[];self.count=count;self.digest=digest;self.sd=sd
        self.time=0

    def clock(self):return self.time

    def read(self,timeout):
        self.time+=.05
        if not self.queue:return b''
        chunk=self.queue[0][:3];self.queue[0]=self.queue[0][3:]
        if not self.queue[0]:self.queue.popleft()
        return chunk

    def write(self,data):
        self.writes.append(data)
        if data==b' ':self.queue.append(b'\r\n=> ');return
        command=data.rstrip(b'\n')
        result={b'mmc dev 0':b'mmc0 is current device',
                b'mmc info':b'SD version 3.0' if self.sd else b'MMC version 5.1',
                b'fatload mmc 0:1 ${scriptaddr} boot.scr':f'{self.count} bytes read in 1 ms'.encode(),
                b'hash sha256 ${scriptaddr} ${filesize}':b'sha256 for 4fc00000 ... ==> '+self.digest.encode()}.get(command,b'')
        if command!=b'source ${scriptaddr}':self.queue.append(command+b'\r\n'+result+b'\r\n=> ')

    def session(self):return route.Session(self.read,self.write,clock=self.clock,timeout=20)


class SerialTests(unittest.TestCase):
    def test_fragmented_verified_sd_route(self):
        transcript=Transcript();transcript.session().route('sd')
        self.assertEqual(transcript.writes,[b' ',b'mmc dev 0\n',b'mmc info\n',
            b'fatload mmc 0:1 ${scriptaddr} boot.scr\n',
            b'hash sha256 ${scriptaddr} ${filesize}\n',b'source ${scriptaddr}\n'])

    def test_normal_route_transmits_nothing(self):
        transcript=Transcript();transcript.session().route('emmc')
        self.assertEqual(transcript.writes,[])

    def test_hash_count_and_mapping_refusals_never_source(self):
        for values in ({'count':1074},{'digest':'0'*64},{'sd':False}):
            transcript=Transcript(**values)
            with self.assertRaises(ValueError):transcript.session().route('sd')
            self.assertNotIn(b'source ${scriptaddr}\n',transcript.writes)

    def test_linux_shell_never_transmits(self):
        for data in (b'root login: ',b'root@sv08:~# ',b'recovery@sv08:~$ '):
            transcript=Transcript();transcript.queue=deque([data])
            with self.assertRaises(ValueError):transcript.session().route('sd')
            self.assertEqual(transcript.writes,[])

    def test_timeout_after_interrupt_stops_without_retry(self):
        transcript=Transcript()
        original=transcript.write
        def write(data):
            original(data)
            if data==b' ':transcript.queue.clear()
        session=route.Session(transcript.read,write,clock=transcript.clock,timeout=20)
        with self.assertRaises(TimeoutError):session.route('sd')
        self.assertEqual(transcript.writes,[b' '])

    def test_forbidden_arbitrary_command_even_with_prompt(self):
        transcript=Transcript();session=transcript.session();session.at_prompt=True
        for command in ('reset','boot','mmc write 0 0 100','setenv bootcmd evil','echo x; source ${scriptaddr}'):
            with self.assertRaises(ValueError):session.command(command)
        self.assertEqual(transcript.writes,[])

    def test_command_requires_current_prompt(self):
        transcript=Transcript()
        with self.assertRaises(ValueError):transcript.session().command('mmc info')
        self.assertEqual(transcript.writes,[])

    def test_unknown_gate_times_out_without_tx(self):
        transcript=Transcript();transcript.queue=deque([b'weird prompt> '])
        with self.assertRaises(TimeoutError):transcript.session().route('sd')
        self.assertEqual(transcript.writes,[])

    def test_hash_in_command_echo_cannot_count_as_result(self):
        transcript=Transcript()
        original=transcript.write
        def write(data):
            original(data)
            if data.startswith(b'hash '):transcript.queue=deque([data+b'=> '])
        session=route.Session(transcript.read,write,clock=transcript.clock,timeout=20)
        with self.assertRaises(ValueError):session.route('sd')
        self.assertNotIn(b'source ${scriptaddr}\n',transcript.writes)

    def test_capture_is_bounded(self):
        transcript=Transcript();transcript.queue=deque([b'X'*(route.CAPTURE_LIMIT+1)])
        def read(timeout):transcript.time+=.1;return transcript.queue.popleft() if transcript.queue else b''
        with self.assertRaises(ValueError):route.Session(read,transcript.write,clock=transcript.clock).route('sd')

    def test_actual_unchanged_script_binding(self):
        p=Path(__file__).resolve().parents[1]/'local/managed-boot-inputs'
        if not (p/'boot.scr').exists():self.skipTest('Supplied public script artifacts absent')
        result=route.verify_script(p/'boot.scr',p/'boot.cmd',p/'composition.json')
        self.assertEqual(result['script_sha256'],route.SCRIPT_SHA)


if __name__=='__main__':unittest.main()
