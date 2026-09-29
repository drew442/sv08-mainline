"""Fragmented fixed U-Boot transcripts; never opens a production serial port."""
from collections import deque
from pathlib import Path
from contextlib import ExitStack
import os
import tempfile
from unittest import mock
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
        if data in (b' ',b'\n'):self.queue.append(b'\r\nCB1@uboot:~$ ');return
        command=data.rstrip(b'\n')
        result={b'mmc dev 0':b'mmc0 is current device',
                b'mmc info':b'SD version 3.0' if self.sd else b'MMC version 5.1',
                b'fatload mmc 0:1 ${scriptaddr} boot.scr':f'{self.count} bytes read in 1 ms'.encode(),
                b'hash sha256 ${scriptaddr} ${filesize}':b'sha256 for 4fc00000 ... ==> '+self.digest.encode()}.get(command,b'')
        if command!=b'source ${scriptaddr}':self.queue.append(command+b'\r\n'+result+b'\r\nCB1@uboot:~$ ')

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
            if data.startswith(b'hash '):transcript.queue=deque([data+b'\r\nCB1@uboot:~$ '])
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



class StoppedPromptTests(unittest.TestCase):
    def test_stopped_route_one_newline_then_existing_gates(self):
        t=Transcript();t.queue.clear();t.session().route('sd-resume')
        self.assertEqual(t.writes,[b'\n',b'mmc dev 0\n',b'mmc info\n',b'fatload mmc 0:1 ${scriptaddr} boot.scr\n',b'hash sha256 ${scriptaddr} ${filesize}\n',b'source ${scriptaddr}\n'])

    def test_unknown_linux_or_mixed_prompt_stops_after_only_newline(self):
        for reply in (b'=> ',b'recovery@sv08:~$ ',b'root login: \r\nCB1@uboot:~$ ',b'root@sv08:~# \r\nCB1@uboot:~$ ',b'Password: \r\nCB1@uboot:~$ ',b''):
            t=Transcript();t.queue.clear()
            def write(data):t.writes.append(data);t.queue.append(reply)
            session=route.Session(t.read,write,clock=t.clock,timeout=1)
            with self.assertRaises((ValueError,TimeoutError)):session.route('sd-resume')
            self.assertEqual(t.writes,[b'\n'])

    def test_valid_prompt_cannot_hide_forbidden_output_in_same_read(self):
        for payload in (b'CB1@uboot:~$ \r\nroot login: ',b'root@sv08:~# \r\nCB1@uboot:~$ '):
            writes=[];chunks=deque([payload])
            session=route.Session(lambda timeout:chunks.popleft() if chunks else b'',writes.append)
            with self.assertRaises(ValueError):session.route('sd-resume')
            self.assertEqual(writes,[b'\n'])

    def test_stopped_bad_count_hash_or_mmc_never_sources(self):
        for values in ({'count':1074},{'digest':'0'*64},{'sd':False}):
            t=Transcript(**values);t.queue.clear()
            with self.assertRaises(ValueError):t.session().route('sd-resume')
            self.assertNotIn(b'source ${scriptaddr}\n',t.writes)


class RunCaptureTests(unittest.TestCase):
    """Actual run entrypoint, real capture files and Session; fixture serial I/O."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        self.capture=self.work/'capture.raw'
        self.serial=self.work/'serial-fixture';self.serial.touch()
        self.proc=self.work/'proc';self.proc.mkdir()
        self.policy={'capture_released':True,'fresh_environment_reviewed':True,
                     'mmc_mapping_reviewed':True,'ownership_lock':str(self.work/'lock'),
                     'device':str(self.serial)}
        self.transcript=Transcript()
        self.capture_fd=None;self.serial_fd=None
        self.received=bytearray()
        self.before_tx=[]
        self.fault=None
        self.ready_hook=None
        self.route_name='sd'
        self.admissions=[]

    def execute(self):
        real_open,real_write,real_fsync=os.open,os.write,os.fsync
        actual_session=route.Session
        def opens(path,*args):
            if str(path)==str(self.capture) and self.fault=='unwritable':
                raise PermissionError('Fixture capture directory is unwritable')
            fd=real_open(path,*args)
            if str(path)==str(self.capture):self.capture_fd=fd
            if str(path)==str(self.serial):self.serial_fd=fd
            return fd
        def writes(fd,data):
            if fd==self.serial_fd:
                # Every permitted TX sees durable raw capture already on disk.
                raw=self.capture.read_bytes();self.before_tx.append((data,raw))
                self.assertEqual(raw,bytes(self.received))
                self.transcript.write(data);return len(data)
            if fd==self.capture_fd and data:
                if self.fault=='append-after-countdown' and self.transcript.writes:
                    raise OSError('Fixture append failed after interception')
                if self.fault=='short-after-countdown' and self.transcript.writes:
                    return real_write(fd,data[:1])
                if self.fault=='append-after-hash' and b'hash sha256 ${scriptaddr} ${filesize}\n' in self.transcript.writes:
                    raise OSError('Fixture append failed during hash response')
            return real_write(fd,data)
        def flushes(fd):
            if fd==self.capture_fd:
                if self.fault=='preflight-fsync':raise OSError('Fixture preflight fsync failed')
                if self.fault=='fsync-after-countdown' and self.transcript.writes:
                    raise OSError('Fixture capture fsync failed after countdown')
                if self.fault=='fsync-after-hash' and route.SCRIPT_SHA.encode() in self.capture.read_bytes():
                    raise OSError('Fixture hash capture fsync failed')
            return real_fsync(fd)
        def reads(fd,n):
            data=self.transcript.read(.05)
            self.received.extend(data)
            return data
        actual_path=Path
        def paths(value):return self.proc if str(value)=='/proc' else actual_path(value)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(route,'verify_script',return_value={'script_sha256':route.SCRIPT_SHA}))
            stack.enter_context(mock.patch.object(route,'serial_identity'))
            stack.enter_context(mock.patch.object(route,'Path',side_effect=paths))
            stack.enter_context(mock.patch.object(route.os,'open',side_effect=opens))
            stack.enter_context(mock.patch.object(route.os,'write',side_effect=writes))
            stack.enter_context(mock.patch.object(route.os,'fsync',side_effect=flushes))
            stack.enter_context(mock.patch.object(route.os,'read',side_effect=reads))
            stack.enter_context(mock.patch.object(route.select,'select',return_value=([1],[],[])))
            stack.enter_context(mock.patch.object(route.fcntl,'ioctl',side_effect=lambda *args:self.admissions.append('exclusive')))
            stack.enter_context(mock.patch.object(route,'Session',side_effect=lambda read,write,**kw:
                actual_session(read,write,clock=self.transcript.clock,timeout=20,**kw)))
            return route.run(self.policy,self.route_name,'fixture.scr','fixture.cmd','fixture.json',self.capture,apply=True,ready_hook=self.ready_hook)

    def test_existing_capture_refuses_before_serial_open_and_tx(self):
        self.capture.write_bytes(b'retained evidence')
        with self.assertRaises(FileExistsError):self.execute()
        self.assertIsNone(self.serial_fd);self.assertEqual(self.transcript.writes,[])
        self.assertEqual(self.capture.read_bytes(),b'retained evidence')

    def test_symlink_capture_refuses_before_serial_open_and_tx(self):
        target=self.work/'retained';target.write_bytes(b'retained evidence')
        self.capture.symlink_to(target)
        with self.assertRaises(OSError):self.execute()
        self.assertIsNone(self.serial_fd);self.assertEqual(self.transcript.writes,[])
        self.assertEqual(target.read_bytes(),b'retained evidence')

    def test_unwritable_capture_refuses_before_serial_open_and_tx(self):
        self.fault='unwritable'
        with self.assertRaises(PermissionError):self.execute()
        self.assertIsNone(self.serial_fd);self.assertEqual(self.transcript.writes,[])
        self.assertFalse(self.capture.exists())

    def test_preflight_fsync_failure_keeps_file_without_serial_access(self):
        self.fault='preflight-fsync'
        with self.assertRaises(OSError):self.execute()
        self.assertIsNone(self.serial_fd);self.assertEqual(self.transcript.writes,[])
        self.assertEqual(self.capture.read_bytes(),b'')

    def test_success_streams_and_flushes_before_every_tx(self):
        result=self.execute()
        self.assertTrue(result['transmit'])
        self.assertEqual(self.capture.read_bytes(),bytes(self.received))
        self.assertEqual(self.transcript.writes[-1],b'source ${scriptaddr}\n')
        self.assertIn(route.SCRIPT_SHA.encode(),self.before_tx[-1][1])

    def test_short_append_append_and_fsync_after_countdown_stop_all_further_tx(self):
        for fault in ('short-after-countdown','append-after-countdown','fsync-after-countdown'):
            with self.subTest(fault=fault):
                if self.capture.exists():self.capture.unlink()
                self.transcript=Transcript();self.received.clear();self.fault=fault
                with self.assertRaises(OSError):self.execute()
                self.assertEqual(self.transcript.writes,[b' '])
                self.assertTrue(bytes(self.received).startswith(self.capture.read_bytes()))
                self.assertIn(b'Hit any key',self.capture.read_bytes())

    def test_hash_append_and_fsync_failure_never_source_and_keep_transcript(self):
        for fault in ('append-after-hash','fsync-after-hash'):
            with self.subTest(fault=fault):
                if self.capture.exists():self.capture.unlink()
                self.transcript=Transcript();self.received.clear();self.fault=fault
                with self.assertRaises(OSError):self.execute()
                self.assertNotIn(b'source ${scriptaddr}\n',self.transcript.writes)
                self.assertEqual(self.transcript.writes[-1],b'hash sha256 ${scriptaddr} ${filesize}\n')
                self.assertTrue(bytes(self.received).startswith(self.capture.read_bytes()))
                self.assertIn(b'1075 bytes read',self.capture.read_bytes())

    def test_timeout_retains_received_bytes_without_retry(self):
        self.transcript.queue=deque([b'unrecognized boot output'])
        with self.assertRaises(TimeoutError):self.execute()
        self.assertEqual(self.transcript.writes,[])
        self.assertEqual(self.capture.read_bytes(),b'unrecognized boot output')

    def test_refusal_retains_raw_hash_failure(self):
        self.transcript.digest='0'*64
        with self.assertRaises(ValueError):self.execute()
        self.assertNotIn(b'source ${scriptaddr}\n',self.transcript.writes)
        self.assertEqual(self.capture.read_bytes(),bytes(self.received))
        self.assertIn(b'0'*64,self.capture.read_bytes())

    def test_overlimit_retains_exact_bounded_prefix_and_stops_tx(self):
        # Countdown inside the overlimit chunk cannot authorize interception.
        self.transcript.queue=deque([b'X'*route.CAPTURE_LIMIT+b'Hit any key to stop autoboot:  3 '])
        original=self.transcript.read
        def whole(timeout):
            self.transcript.read=original
            self.transcript.time+=.05
            return self.transcript.queue.popleft()
        self.transcript.read=whole
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(self.transcript.writes,[])
        self.assertEqual(self.capture.stat().st_size,route.CAPTURE_LIMIT)
        self.assertEqual(self.capture.read_bytes(),b'X'*route.CAPTURE_LIMIT)


    def test_readiness_hook_runs_after_exclusive_and_capture_before_any_tx(self):
        calls=[]
        def hook(fd,raw):
            self.assertEqual(self.admissions,['exclusive'])
            self.assertEqual(fd,self.serial_fd);self.assertEqual(raw,self.capture_fd)
            self.assertEqual(self.transcript.writes,[])
            self.assertEqual(self.capture.read_bytes(),b'')
            calls.append('ready')
            return lambda:calls.append('live')
        self.ready_hook=hook
        self.execute()
        self.assertEqual(calls[0],'ready');self.assertIn('live',calls)

    def test_readiness_callback_or_ack_failure_has_zero_tx_and_keeps_capture(self):
        for error in (ValueError('callback failed'),TimeoutError('ack timed out'),EOFError('parent lost')):
            if self.capture.exists():self.capture.unlink()
            self.transcript=Transcript()
            def hook(fd,raw):raise error
            self.ready_hook=hook
            with self.assertRaises(type(error)):self.execute()
            self.assertEqual(self.transcript.writes,[])
            self.assertTrue(self.capture.exists())

    def test_parent_loss_liveness_gate_stops_before_tx(self):
        def hook(fd,raw):
            def lost():raise EOFError('primary connection lost')
            return lost
        self.ready_hook=hook
        with self.assertRaises(EOFError):self.execute()
        self.assertEqual(self.transcript.writes,[])

    def test_explicit_exception_needs_readiness_hook_and_preserves_unknowns(self):
        from tests.test_sv08_recovery_boot_guard import exception
        self.policy['fresh_environment_reviewed']=False
        self.policy['recovery_return_exception']=exception()
        with self.assertRaises(ValueError):self.execute()
        self.assertIsNone(self.serial_fd);self.assertEqual(self.transcript.writes,[])
        self.ready_hook=lambda fd,raw:None
        self.execute()
        self.assertFalse(self.policy['fresh_environment_reviewed'])

    def test_ordinary_freshness_and_unapproved_exception_refuse(self):
        from tests.test_sv08_recovery_boot_guard import exception
        self.policy['fresh_environment_reviewed']=False
        self.ready_hook=lambda fd,raw:None
        with self.assertRaises(ValueError):self.execute()
        self.policy['recovery_return_exception']={**exception(),'approval_sha256':'0'*64}
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(self.transcript.writes,[]);self.assertFalse(self.capture.exists())

    def admit_resume(self):
        from tests.test_sv08_recovery_boot_guard import exception
        self.route_name='sd-resume';self.transcript.queue.clear()
        self.policy.update(fresh_environment_reviewed=False,stopped_uboot_reviewed=True,
                           no_intervening_text_sender_reviewed=True,no_residual_command_reviewed=True,
                           stopped_capture_sha256='ed9074ded59d4aec42f11bbc95e4e2cd21b7283ba6a89336687fc7ff2c0102e9',
                           recovery_return_exception=exception())

    def test_actual_resume_admission_and_durable_capture(self):
        self.admit_resume();self.execute()
        self.assertEqual(self.transcript.writes[0],b'\n')
        self.assertEqual(self.transcript.writes.count(b'\n'),1)
        self.assertFalse(self.policy['fresh_environment_reviewed'])
        self.assertIn(b'source ${scriptaddr}\n',self.transcript.writes)

    def test_resume_missing_or_changed_review_refuses_before_serial_or_tx(self):
        self.admit_resume()
        for key in ('stopped_uboot_reviewed','no_intervening_text_sender_reviewed','no_residual_command_reviewed','stopped_capture_sha256','recovery_return_exception'):
            previous=self.policy.pop(key)
            with self.assertRaises(ValueError):self.execute()
            self.assertIsNone(self.serial_fd);self.assertEqual(self.transcript.writes,[])
            self.policy[key]=previous
        self.policy['fresh_environment_reviewed']=True
        with self.assertRaises(ValueError):self.execute()

    def test_resume_existing_capture_refuses_before_newline(self):
        self.admit_resume();self.capture.write_bytes(b'preserved')
        with self.assertRaises(FileExistsError):self.execute()
        self.assertEqual(self.transcript.writes,[])


if __name__=='__main__':unittest.main()
