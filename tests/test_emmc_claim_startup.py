"""Deterministic syscall injection into the compiled production claim boundary."""
import errno
import hashlib
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
#define nanosleep fake_sleep
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
#undef nanosleep
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
static int clocks,randoms,sleeps,bytes,sockets,connects,sends,recvs,target_opens;
static size_t sent_bytes,response_at;
static char sent_request[1280];
static jmp_buf finished;
static const char response[] = "@RESPONSE@";
#define IS(s) (!strcmp(scenario,s))
int fake_clock(clockid_t id,struct timespec *out) {
 assert(id==CLOCK_MONOTONIC);clocks++;
 if(IS("clock-start")||(IS("clock-retry")&&clocks==3)||
    (IS("clock-complete")&&bytes==32)){errno=EIO;return -1;}
 out->tv_sec=123+elapsed/1000000000LL;
 out->tv_nsec=500000000L+elapsed%1000000000LL;
 if(out->tv_nsec>=1000000000L){out->tv_sec++;out->tv_nsec-=1000000000L;}
 return 0;
}
int fake_sleep(const struct timespec *req,struct timespec *rem) {
 long long ns=req->tv_sec*1000000000LL+req->tv_nsec;
 assert(ns>0&&ns<=100000000LL&&ns<=60000000000LL-elapsed);sleeps++;
 if(IS("sleep-error")){errno=EINVAL;return -1;}
 if(IS("sleep-zero")){elapsed+=ns;rem->tv_sec=0;rem->tv_nsec=0;errno=EINTR;return -1;}
 if(IS("sleep-eintr")||(IS("sleep-once")&&sleeps==1)){
   long long spent=ns<25000000LL?ns:25000000LL;
   elapsed+=spent;rem->tv_sec=0;rem->tv_nsec=ns-spent;
   /* A delivered signal may also delay rescheduling beyond the pause. */
   if(IS("sleep-eintr")){elapsed+=25000000LL;rem->tv_nsec=75000000L;}
   errno=EINTR;return -1;
 }
 elapsed+=ns;return 0;
}
ssize_t fake_random(void *out,size_t size,unsigned flags) {
 assert(flags==GRND_NONBLOCK&&size==32-(size_t)bytes);randoms++;
 assert(elapsed<60000000000LL);
 if(IS("permanent")){errno=EIO;return -1;}
 if(IS("zero")){errno=EACCES;return 0;}
 if(IS("eintr")||(IS("eintr-ready")&&randoms==1)){errno=EINTR;return -1;}
 if(IS("partial-deadline")&&randoms==1){elapsed=60000000000LL;size=8;}
 else if(IS("boundary")){elapsed=60000000000LL;}
 else if(IS("just-before")){elapsed=59999999999LL;}
 else if(IS("bounded-sleep")&&randoms==1){elapsed=59950000000LL;errno=EAGAIN;return -1;}
 else if(IS("timeout")||IS("sleep-eintr")||
         ((IS("again")||IS("sleep-error")||IS("sleep-once")||IS("sleep-zero")||IS("clock-retry"))&&randoms==1)||
         (IS("partial-again")&&randoms==2)){errno=EAGAIN;return -1;}
 else if((IS("partial")||IS("partial-again"))&&randoms==1)size=8;
 memset(out,0xab,size);bytes+=(int)size;return (ssize_t)size;
}
static void timely(void){assert(bytes==32&&elapsed<60000000000LL);}
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


def startup_binary():
    with tempfile.TemporaryDirectory(prefix='claim-startup-') as tmp:
        root = Path(tmp)
        public = raw_public_key((KEYS / 'test-verification-key.pem').read_bytes()).hex()
        signature = sign_receipt(receipt_message('startup-test', '12' * 32, 'ab' * 32),
                                 KEYS / 'test-signing-key.pem')
        response = ('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n'
                    'Content-Length: 129\r\nConnection: close\r\n\r\n' + signature.hex() + '\n')
        import json
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
        result = subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror',
                                 '-Wno-unused-function', '-Wno-misleading-indentation',
                                 *flags, f'-I{REPO / "upstream/monocypher/src"}',
                                 f'-I{REPO / "upstream/monocypher/src/optional"}',
                                 str(root / 'case.c'), *(str(p) for p in ED25519_SOURCES),
                                 '-o', str(binary)], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        yield binary


def run(binary, scenario, main=False):
    result = subprocess.run([str(binary), scenario, *(['main'] if main else [])],
                            capture_output=True, text=True, timeout=3)
    assert result.returncode == 0, result.stderr
    for secret in ('ab' * 32, '12' * 32, 'POST /claim', 'HTTP/1.1', 'PRIVATE KEY'):
        assert secret not in result.stdout + result.stderr
    return list(map(int, result.stdout.splitlines()[-1].split())), result




REFUSALS = [
    ('timeout', 'RANDOM_TIMEOUT', errno.ETIMEDOUT), ('eintr', 'RANDOM_TIMEOUT', errno.ETIMEDOUT),
    ('sleep-eintr', 'RANDOM_TIMEOUT', errno.ETIMEDOUT), ('bounded-sleep', 'RANDOM_TIMEOUT', errno.ETIMEDOUT),
    ('boundary', 'RANDOM_TIMEOUT', errno.ETIMEDOUT), ('partial-deadline', 'RANDOM_TIMEOUT', errno.ETIMEDOUT),
    ('permanent', 'RANDOM', errno.EIO), ('zero', 'RANDOM', 0),
    ('clock-start', 'RANDOM_CLOCK', errno.EIO), ('clock-retry', 'RANDOM_CLOCK', errno.EIO),
    ('clock-complete', 'RANDOM_CLOCK', errno.EIO), ('sleep-error', 'RANDOM_SLEEP', errno.EINVAL),
]


class ClaimStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = startup_binary()
        cls.binary = next(cls.fixture)
        cls.addClassCleanup(cls.fixture.close)

    def test_complete_secure_challenge_before_one_request(self):
        for scenario in ('ready', 'again', 'eintr-ready', 'partial', 'partial-again',
                         'sleep-once', 'sleep-zero', 'just-before', 'send-partial', 'transport-eintr'):
            with self.subTest(scenario=scenario):
                values, result = run(self.binary, scenario)
                self.assertEqual(values[0:2], [1, 32])
                self.assertEqual(values[4:6], [1, 1])
                self.assertGreaterEqual(values[6], 1)
                self.assertLess(values[7], 60_000_000_000)
                self.assertEqual(values[8], 0)
                self.assertEqual(result.stderr, '')
                if scenario in ('again', 'eintr-ready', 'partial-again', 'sleep-once'):
                    self.assertGreater(values[3], 0)

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
                        self.assertLessEqual(values[7], 60_050_000_000)
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
