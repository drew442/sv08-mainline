"""Compiled claim acquisition: injected failures and real timer interruption.

PID namespace creation tests process semantics, not sandboxing. An unavailable
namespace is explicitly skipped and continues to block physical preparation.
"""
import errno
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
import subprocess
import tempfile

import unittest

from scripts.ed25519_build import ED25519_SOURCES, raw_public_key
from tests.sv08_emmc_job import receipt_message, sign_receipt

REPO = Path(__file__).resolve().parents[1]
WRITER = REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'
KEYS = WRITER.parent / 'receipt-test-keys'

HARNESS = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <setjmp.h>
#define main writer_main
#define clock_gettime fake_clock
#define sigprocmask fake_sigprocmask
#define sigpending fake_sigpending
#define sigaction(...) fake_sigaction(__VA_ARGS__)
#define timer_create fake_timer_create
#define timer_settime fake_timer_settime
#define timer_delete fake_timer_delete
#define sigtimedwait fake_sigtimedwait
#define getrandom fake_random
#define socket fake_socket
#define setsockopt fake_setsockopt
#define connect fake_connect
#define send fake_send
#define recv fake_recv
#define close fake_close
#define open fake_open
#define read fake_read
#define fopen fake_fopen
#define mount fake_mount
#define time fake_time
#define sync fake_sync
#define reboot fake_reboot
#include "@WRITER@"
#undef main
#undef clock_gettime
#undef sigprocmask
#undef sigpending
#undef sigaction
#undef timer_create
#undef timer_settime
#undef timer_delete
#undef sigtimedwait
#undef getrandom
#undef socket
#undef setsockopt
#undef connect
#undef send
#undef recv
#undef close
#undef open
#undef read
#undef fopen
#undef mount
#undef time
#undef sync
#undef reboot
static const char *scenario;
static long long elapsed;
static int active,blocked=1,installed,pending_notice,cleaned,mask_calls,action_calls;
static int clocks,randoms,sleeps,bytes,sockets,connects,sends,recvs,target_opens;
static size_t sent_bytes,response_at;
static char sent_request[1280];
static jmp_buf finished;
static const char response[] = "@RESPONSE@";
#define IS(s) (!strcmp(scenario,s))
int fake_clock(clockid_t id,struct timespec *out) {
 assert(id==CLOCK_MONOTONIC);clocks++;
 if(IS("clock-start")||(IS("clock-retry")&&clocks==3)||
    (IS("clock-complete")&&bytes==32)||(IS("clock-admit")&&cleaned)){errno=EIO;return -1;}
 out->tv_sec=123+elapsed/1000000000LL;
 out->tv_nsec=500000000L+elapsed%1000000000LL;
 if(out->tv_nsec>=1000000000L){out->tv_sec++;out->tv_nsec-=1000000000L;}
 return 0;
}
static struct sigaction saved_action;
int fake_sigprocmask(int how,const sigset_t *set,sigset_t *old) {
 mask_calls++;
 if((IS("mask-start")&&mask_calls==1)||(IS("mask-wait")&&mask_calls==2)||
    (IS("mask-cleanup")&&mask_calls==3)||(IS("mask-restore")&&mask_calls==4)){
   errno=EPERM;return -1;
 }
 if(old){sigemptyset(old);sigaddset(old,SIGUSR1);
   if(IS("inherited-blocked"))sigaddset(old,SIGRTMIN);}
 if(how==SIG_BLOCK)blocked=1;
 else {assert(how==SIG_SETMASK&&sigismember(set,SIGUSR1));blocked=sigismember(set,SIGRTMIN);}
 if(mask_calls>=3&&!active&&!installed&&!pending_notice)cleaned=1;
 return 0;
}
int fake_sigpending(sigset_t *out) {
 if(IS("pending-query")){errno=EIO;return -1;}
 sigemptyset(out);if(IS("inherited-pending"))sigaddset(out,SIGRTMIN);return 0;
}
int fake_sigaction(int sig,const struct sigaction *action,struct sigaction *old) {
 assert(sig==SIGRTMIN&&blocked);action_calls++;
 if((IS("action-start")&&action_calls==1)||(IS("action-restore")&&action_calls==2)){
   errno=EINVAL;return -1;
 }
 if(old){memset(&saved_action,0,sizeof(saved_action));
   saved_action.sa_handler=IS("inherited-ignored")?SIG_IGN:SIG_DFL;*old=saved_action;}
 if(action_calls==1){assert(action->sa_handler==random_timer_notice&&!(action->sa_flags&SA_RESTART));installed=1;}
 else {assert(action->sa_handler==saved_action.sa_handler);installed=0;}
 return 0;
}
int fake_timer_create(clockid_t clock,struct sigevent *event,timer_t *timer) {
 assert(clock==CLOCK_MONOTONIC&&event->sigev_notify==SIGEV_SIGNAL&&event->sigev_signo==SIGRTMIN);
 if(IS("timer-create")){errno=EAGAIN;return -1;}*timer=(timer_t)1;return 0;
}
int fake_timer_settime(timer_t timer,int flags,const struct itimerspec *value,struct itimerspec *old) {
 assert(timer==(timer_t)1&&old==NULL);
 if(flags==TIMER_ABSTIME){
   assert(value->it_value.tv_sec==183&&value->it_value.tv_nsec==500000000L);
   assert(value->it_interval.tv_sec==0&&value->it_interval.tv_nsec==100000000L);
   if(IS("timer-arm")){errno=EINVAL;return -1;}active=1;
   if(IS("setup-deadline"))elapsed=60000000000LL;
 }else{assert(flags==0&&value->it_value.tv_sec==0&&value->it_value.tv_nsec==0);
   if(IS("timer-disarm")){errno=EIO;return -1;}active=0;
   if(IS("cleanup-deadline"))elapsed=60000000000LL;
 }
 return 0;
}
int fake_timer_delete(timer_t timer) {
 assert(timer==(timer_t)1);if(IS("timer-delete")){errno=EIO;return -1;}active=0;return 0;
}
int fake_sigtimedwait(const sigset_t *set,siginfo_t *info,const struct timespec *wait) {
 assert(blocked&&!active&&sigismember(set,SIGRTMIN)&&info==NULL&&wait->tv_sec==0&&wait->tv_nsec==0);
 if(IS("drain-error")){errno=EIO;return -1;}
 if(IS("drain-flood"))return SIGRTMIN;
 if(IS("drain-eintr")){errno=EINTR;return -1;}
 if(pending_notice){pending_notice=0;return SIGRTMIN;}errno=EAGAIN;return -1;
}
ssize_t fake_random(void *out,size_t size,unsigned flags) {
 assert(flags==0&&size==32-(size_t)bytes&&active&&installed&&!blocked);randoms++;
 assert(elapsed<60000000000LL);
 if(IS("permanent")){errno=EIO;return -1;}
 if(IS("unavailable")){errno=ENOSYS;return -1;}
 if(IS("again")){errno=EAGAIN;return -1;}
 if(IS("zero")){errno=EACCES;return 0;}
 if(IS("timeout")||IS("eintr")){
   elapsed+=10000000000LL;errno=EINTR;return -1;
 }
 if((IS("eintr-ready")&&randoms==1)||(IS("partial-eintr")&&randoms==2)){
   errno=EINTR;return -1;
 }
 if(IS("pre-syscall")){
   /* First expiry delivered between the last check and syscall entry. The
    * repeated notification interrupts the call 100 ms later. */
   elapsed=60000000000LL;random_timer_notice(SIGRTMIN);
   elapsed+=100000000LL;random_timer_notice(SIGRTMIN);errno=EINTR;return -1;
 }
 if(IS("partial-deadline")&&randoms==1){elapsed=60000000000LL;size=8;}
 else if(IS("boundary")||IS("pending-expiry")){elapsed=60000000000LL;pending_notice=1;}
 else if(IS("just-before")){elapsed=59999999999LL;}
 else if((IS("partial")||IS("partial-eintr")||IS("clock-retry"))&&randoms==1)size=8;
 if(IS("pending-complete"))pending_notice=1;
 memset(out,0xab,size);bytes+=(int)size;return (ssize_t)size;
}
static void timely(void){assert(bytes==32&&elapsed<60000000000LL&&cleaned&&!active&&!installed&&!pending_notice);}
int fake_socket(int domain,int type,int protocol){
 timely();assert(domain==AF_INET&&type==(SOCK_STREAM|SOCK_CLOEXEC)&&protocol==0);
 assert(++sockets==1);if(IS("socket")){errno=EMFILE;return -1;}return 99;
}
int fake_setsockopt(int fd,int level,int option,const void *value,socklen_t size){
 (void)fd;(void)level;(void)option;(void)value;(void)size;
 if(IS("sockopt")){errno=EINVAL;return -1;}return 0;
}
int fake_connect(int fd,const struct sockaddr *addr,socklen_t size){
 (void)fd;(void)addr;(void)size;timely();assert(++connects==1);
 if(IS("connect")){errno=ECONNREFUSED;return -1;}return 0;
}
ssize_t fake_send(int fd,const void *data,size_t size,int flags){
 (void)fd;(void)flags;timely();sends++;
 if(IS("send")){errno=EPIPE;return -1;}
 if(IS("send-zero")){errno=EACCES;return 0;}
 if(IS("send-partial-error")&&sends==2){errno=EPIPE;return -1;}
 if((IS("transport-eintr")&&sends==1)){errno=EINTR;return -1;}
 if((IS("send-partial")||IS("send-partial-error"))&&size>7)size=7;
 assert(sent_bytes+size<sizeof(sent_request));memcpy(sent_request+sent_bytes,data,size);
 sent_bytes+=size;return (ssize_t)size;
}
ssize_t fake_recv(int fd,void *out,size_t size,int flags){
 (void)fd;(void)flags;recvs++;
 if(IS("recv")){errno=ECONNRESET;return -1;}
 if(IS("transport-eintr")&&recvs==1){errno=EINTR;return -1;}
 errno=EACCES;
 if(IS("receipt"))return 0;
 size_t left=sizeof(response)-1-response_at;if(size>left)size=left;
 if(size>17)size=17;memcpy(out,response+response_at,size);response_at+=size;return (ssize_t)size;
}
int fake_close(int fd){(void)fd;errno=EBADF;return 0;}
int fake_open(const char *path,int flags,...){
 (void)flags;
 if(!strcmp(path,"/proc/device-tree/compatible"))return 88;
 if(!strcmp(path,"/job.json")||!strcmp(path,"/job.sig")||
    !strcmp(path,"/commissioning-target-policy.json"))return 77;
 target_opens++;assert(0&&"unexpected downstream open");return -1;
}
ssize_t fake_read(int fd,void *out,size_t size){
 if(fd==88){static const char board[]="linux,dummy-virt";assert(size>=sizeof(board));
 memcpy(out,board,sizeof(board));return sizeof(board);}assert(fd==77);return 0;
}
FILE *fake_fopen(const char *path,const char *mode){
 (void)mode;
 static char cmd[]="sv08.h616_commissioning=1 sv08.claim_port=1234\n";
 static char mounts[]="server:/root / nfs ro 0 0\n";
 if(!strcmp(path,"/proc/cmdline"))return fmemopen(cmd,sizeof(cmd)-1,"r");
 assert(!strcmp(path,"/proc/mounts"));return fmemopen(mounts,sizeof(mounts)-1,"r");
}
int fake_mount(const char *a,const char *b,const char *c,unsigned long d,const void *e){
 (void)a;(void)b;(void)c;(void)d;(void)e;return 0;
}
time_t fake_time(time_t *out){if(out)*out=1500;return 1500;}
void fake_sync(void){}
int fake_reboot(int operation){assert(operation==RB_POWER_OFF);longjmp(finished,1);}
int main(int argc,char **argv){
 assert(argc==2||argc==3);scenario=argv[1];volatile int admitted=0;
 if(argc==3){if(!setjmp(finished))writer_main();}
 else admitted=claim_once("sv08.claim_port=1234","1212121212121212121212121212121212121212121212121212121212121212");
 if(sent_bytes){assert(!memcmp(sent_request,"POST /claim HTTP/1.1",sent_bytes<19?sent_bytes:19));
 assert(strstr(sent_request+1,"POST /claim")==NULL);}
 printf("%d %d %d %d %d %d %d %lld %d\n",admitted,bytes,randoms,sleeps,
 sockets,connects,sends,elapsed,target_opens);return 0;
}
'''


# Real kernel timer/mask/disposition operations; only the entropy syscall is
# replaced with a pipe read that cannot complete (the writer end remains open).
# The entry clock alone is shifted 59 s to exercise the same production 60 s
# arithmetic/absolute timer with a one-second test wait, not a new runtime knob.
INTERRUPTION_HARNESS = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
static int clocks,reads,pipe_fds[2],lost_wake;
static int fixture_clock(clockid_t id,struct timespec *out) {
  int result=clock_gettime(id,out);if(!result&&++clocks==1)out->tv_sec-=59;return result;
}
static ssize_t blocked_random(void *out,size_t size,unsigned flags) {
  assert(flags==0);reads++;
  if(lost_wake) {
    struct timespec pause={2,0};
    /* First timer notice is caught before the blocked syscall starts. */
    assert(nanosleep(&pause,NULL)==-1&&errno==EINTR);
  }
  ssize_t result=read(pipe_fds[0],out,size);
  assert(result==-1&&errno==EINTR);return result;
}
#define main writer_main
#define clock_gettime fixture_clock
#define getrandom blocked_random
#include "@WRITER@"
#undef main
#undef clock_gettime
#undef getrandom
static void inherited_handler(int sig){(void)sig;assert(0&&"late acquisition notification");}
int main(int argc,char **argv) {
  assert(argc==2);lost_wake=!strcmp(argv[1],"lost-wake");
  assert(pipe(pipe_fds)==0);
  sigset_t initial,current;sigemptyset(&initial);
  sigaddset(&initial,SIGRTMIN);sigaddset(&initial,SIGUSR1);
  assert(sigprocmask(SIG_SETMASK,&initial,NULL)==0);
  struct sigaction inherited={0},restored;sigemptyset(&inherited.sa_mask);
  inherited.sa_handler=!strcmp(argv[1],"ignored")?SIG_IGN:inherited_handler;
  inherited.sa_flags=SA_RESTART;
  assert(sigaction(SIGRTMIN,&inherited,NULL)==0);
  char challenge[65];struct timespec start,end;
  assert(clock_gettime(CLOCK_MONOTONIC,&start)==0);
  assert(random_challenge(challenge)==0);
  assert(clock_gettime(CLOCK_MONOTONIC,&end)==0);
  long long ns=(end.tv_sec-start.tv_sec)*1000000000LL+end.tv_nsec-start.tv_nsec;
  assert(reads==1&&ns>=1000000000LL&&ns<2000000000LL);
  assert(sigaction(SIGRTMIN,NULL,&restored)==0&&restored.sa_handler==inherited.sa_handler);
  assert((restored.sa_flags&SA_RESTART)==SA_RESTART);
  assert(sigprocmask(SIG_SETMASK,NULL,&current)==0);
  assert(sigismember(&current,SIGRTMIN)&&sigismember(&current,SIGUSR1));
  /* Unmask the restored caught handler and wait two timer periods: a leaked
   * notification would hit inherited_handler and fail instead of a socket. */
  sigdelset(&current,SIGRTMIN);assert(sigprocmask(SIG_SETMASK,&current,NULL)==0);
  struct timespec grace={0,250000000L};assert(nanosleep(&grace,NULL)==0);
  printf("pid=%ld elapsed_ns=%lld blocked_read_eintr=%d lost_wake=%d\n",(long)getpid(),ns,reads,lost_wake);
  close(pipe_fds[0]);close(pipe_fds[1]);return 0;
}
'''


def record_evidence(name, data):
    """Optional assigned scratch output; never a workflow approval record."""
    destination = os.environ.get('SV08_ENTROPY_EVIDENCE_DIR')
    if destination:
        path = Path(destination) / name
        if path.exists():
            for attempt in range(2, 100):
                alternative = path.with_name(f'{path.stem}-{attempt}{path.suffix}')
                if not alternative.exists():
                    path = alternative
                    break
            else:
                raise RuntimeError('bounded evidence output names exhausted')
        path.write_text(json.dumps(data, indent=2) + '\n')


def interruption_binary():
    with tempfile.TemporaryDirectory(prefix='claim-interruption-') as tmp:
        root = Path(tmp)
        source = root / 'case.c'
        source.write_text(INTERRUPTION_HARNESS.replace('@WRITER@', str(WRITER)))
        binary = root / 'case'
        command = ['cc', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-function', '-ffunction-sections', '-fdata-sections',
                   '-Wl,--gc-sections', f'-I{REPO / "upstream/monocypher/src"}',
                   f'-I{REPO / "upstream/monocypher/src/optional"}', str(source),
                   *(str(p) for p in ED25519_SOURCES), '-o', str(binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        record_evidence('interruption-build.json', {
            'argv': command, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'writer_sha256': hashlib.sha256(WRITER.read_bytes()).hexdigest(),
            'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'binary_bytes': binary.stat().st_size, 'stderr': result.stderr})
        yield binary


class RealInterruptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = interruption_binary()
        cls.binary = next(cls.fixture)
        cls.addClassCleanup(cls.fixture.close)

    def exercise(self, command, evidence_name, expected_pid_one=False):
        start = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, timeout=4)
        record_evidence(evidence_name, {'argv': command, 'exit': result.returncode,
                                      'stdout': result.stdout, 'stderr': result.stderr,
                                      'seconds': time.monotonic() - start,
                                      'kernel': os.uname().release, 'arch': os.uname().machine})
        if (expected_pid_one and result.returncode != 0 and
                ('unshare failed' in result.stderr or
                 'write failed /proc/self/uid_map: Operation not permitted' in result.stderr)):
            self.skipTest('PID 1 namespace unavailable: ' + result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, 'SV08_QEMU_REIMAGE_CLAIM_RANDOM_TIMEOUT errno=110\n')
        self.assertIn('blocked_read_eintr=1', result.stdout)
        if expected_pid_one:
            self.assertTrue(result.stdout.startswith('pid=1 '), result.stdout)

    def test_real_ordinary_process_interruption(self):
        for mode in ('caught', 'ignored', 'lost-wake'):
            with self.subTest(mode=mode):
                self.exercise([str(self.binary), mode], f'ordinary-{mode}.json')

    def test_real_namespace_pid_one_interruption(self):
        unshare = shutil.which('unshare')
        if not unshare:
            self.skipTest('installed unshare unavailable; physical preparation blocked')
        for mode in ('caught', 'ignored', 'lost-wake'):
            self.exercise([unshare, '--user', '--map-root-user', '--pid', '--fork',
                           str(self.binary), mode], f'pid-one-{mode}.json', True)


def startup_binary():
    with tempfile.TemporaryDirectory(prefix='claim-startup-') as tmp:
        root = Path(tmp)
        public = raw_public_key((KEYS / 'test-verification-key.pem').read_bytes()).hex()
        signature = sign_receipt(receipt_message('startup-test', '12' * 32, 'ab' * 32),
                                 KEYS / 'test-signing-key.pem')
        response = ('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n'
                    'Content-Length: 129\r\nConnection: close\r\n\r\n' + signature.hex() + '\n')
        source = HARNESS.replace('@WRITER@', str(WRITER)).replace('@RESPONSE@', json.dumps(response)[1:-1])
        (root / 'case.c').write_text(source)
        empty_hash = hashlib.sha256(b'').hexdigest()
        flags = ['-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_SYNTHETIC_TEST=1',
                 '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000001"',
                 '-DSV08_H616_EXPECTED_DEV_T="8:0"', '-DSV08_H616_BOARD_COMPATIBLE="test,synthetic-h616"',
                 '-DSV08_H616_CLAIM_SERVER="192.0.2.1"', '-DSV08_JOB_ID="startup-test"',
                 '-DSV08_JOB_NOT_BEFORE=1000LL', '-DSV08_JOB_EXPIRES=2000LL',
                 f'-DSV08_RECEIPT_PUBLIC_KEY_HEX="{public}"']
        flags += [f'-D{name}="{empty_hash}"' for name in
                  ('SV08_JOB_DESCRIPTOR_SHA256', 'SV08_JOB_SIGNATURE_SHA256', 'SV08_TARGET_POLICY_SHA256')]
        binary = root / 'case'
        command = ['cc', '-O2', '-Wall', '-Wextra', '-Werror',
                                 '-Wno-unused-function', '-Wno-misleading-indentation',
                                 *flags, f'-I{REPO / "upstream/monocypher/src"}',
                                 f'-I{REPO / "upstream/monocypher/src/optional"}',
                                 str(root / 'case.c'), *(str(p) for p in ED25519_SOURCES),
                                 '-o', str(binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        record_evidence('deterministic-build.json', {
            'argv': command, 'source_sha256': hashlib.sha256((root / 'case.c').read_bytes()).hexdigest(),
            'writer_sha256': hashlib.sha256(WRITER.read_bytes()).hexdigest(),
            'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'binary_bytes': binary.stat().st_size, 'stderr': result.stderr})
        yield binary


def run(binary, scenario, main=False):
    result = subprocess.run([str(binary), scenario, *(['main'] if main else [])],
                            capture_output=True, text=True, timeout=3)
    assert result.returncode == 0, result.stderr
    for secret in ('ab' * 32, '12' * 32, 'POST /claim', 'HTTP/1.1', 'PRIVATE KEY'):
        assert secret not in result.stdout + result.stderr
    return list(map(int, result.stdout.splitlines()[-1].split())), result




REFUSALS = [
    *[(s, 'RANDOM_TIMEOUT', errno.ETIMEDOUT) for s in
      ('timeout', 'eintr', 'boundary', 'partial-deadline', 'pre-syscall',
       'pending-expiry', 'cleanup-deadline', 'setup-deadline')],
    ('permanent', 'RANDOM', errno.EIO), ('unavailable', 'RANDOM', errno.ENOSYS),
    ('again', 'RANDOM', errno.EAGAIN), ('zero', 'RANDOM', 0),
    *[(s, 'RANDOM_CLOCK', errno.EIO) for s in ('clock-start', 'clock-retry', 'clock-complete', 'clock-admit')],
    *[(s, 'RANDOM_SETUP', e) for s, e in (
      ('mask-start', errno.EPERM), ('mask-wait', errno.EPERM),
      ('pending-query', errno.EIO), ('inherited-pending', errno.EBUSY),
      ('action-start', errno.EINVAL), ('timer-create', errno.EAGAIN), ('timer-arm', errno.EINVAL))],
    *[(s, 'RANDOM_CLEANUP', e) for s, e in (
      ('mask-cleanup', errno.EPERM), ('mask-restore', errno.EPERM),
      ('action-restore', errno.EINVAL), ('timer-disarm', errno.EIO),
      ('timer-delete', errno.EIO), ('drain-error', errno.EIO),
      ('drain-flood', errno.EBUSY), ('drain-eintr', errno.EBUSY))],
]


class ClaimStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = startup_binary()
        cls.binary = next(cls.fixture)
        cls.addClassCleanup(cls.fixture.close)

    def test_complete_secure_challenge_before_one_request(self):
        for scenario in ('ready', 'eintr-ready', 'partial', 'partial-eintr', 'just-before',
                         'inherited-blocked', 'inherited-ignored', 'pending-complete',
                         'send-partial', 'transport-eintr'):
            with self.subTest(scenario=scenario):
                values, result = run(self.binary, scenario)
                self.assertEqual(values[0:2], [1, 32])
                self.assertEqual(values[4:6], [1, 1])
                self.assertGreaterEqual(values[6], 1)
                self.assertLess(values[7], 60_000_000_000)
                self.assertEqual(values[8], 0)
                self.assertEqual(result.stderr, '')
                self.assertEqual(values[3], 0)  # no readiness polling/sleeps

    def test_random_refusal_never_reaches_transport_or_downstream_open(self):
        for scenario, stage, error in REFUSALS:
            for main in (False, True):
                with self.subTest(scenario=scenario, main=main):
                    values, result = run(self.binary, scenario, main)
                    self.assertEqual(values[0], 0)
                    self.assertEqual(values[4:7], [0, 0, 0])
                    self.assertEqual(values[8], 0)
                    self.assertEqual(result.stderr, f'SV08_H616_COMMISSIONING_CLAIM_{stage} errno={error}\n')
                    if main:
                        self.assertIn('SV08_H616_COMMISSIONING_REFUSED_OR_UNCERTAIN_CLAIM\n', result.stdout)
                    if stage == 'RANDOM_TIMEOUT':
                        self.assertGreaterEqual(values[7], 60_000_000_000)
                        self.assertLessEqual(values[7], 60_100_000_000)
                        self.assertLessEqual(values[2], 600)
                        self.assertLessEqual(values[3], 1200)

    def test_transport_failure_diagnostics_capture_errno_without_retry(self):
        for scenario, stage, error in (
            ('socket', 'SOCKET', errno.EMFILE), ('sockopt', 'SOCKET', errno.EINVAL),
            ('connect', 'CONNECT', errno.ECONNREFUSED), ('send', 'SEND', errno.EPIPE),
            ('send-zero', 'SEND', 0), ('send-partial-error', 'SEND', errno.EPIPE),
            ('recv', 'RECV', errno.ECONNRESET), ('receipt', 'RECEIPT', 0),
        ):
            with self.subTest(scenario=scenario):
                values, result = run(self.binary, scenario)
                self.assertEqual(values[0:2], [0, 32])
                self.assertEqual(values[4], 1)
                self.assertLessEqual(values[5], 1)
                self.assertEqual(result.stderr, f'SV08_H616_COMMISSIONING_CLAIM_{stage} errno={error}\n')
                self.assertEqual(values[8], 0)


if __name__ == '__main__':
    unittest.main()
