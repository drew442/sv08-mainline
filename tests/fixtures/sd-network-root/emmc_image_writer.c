/* SPDX-License-Identifier: MIT */
/* Disposable QEMU init only. Never install this in the SD diagnostic image. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define IMAGE_BYTES 7818182656ULL
#define TARGET_BYTES 32000000000ULL
#define CHUNK (1024 * 1024)
#define DEADLINE_SECONDS 4200
static unsigned char buffer[CHUNK];

/* SHA-256 as specified by FIPS 180-4, used independently for source/readback. */
struct sha256 { uint32_t h[8]; uint64_t count; unsigned char block[64]; size_t used; };
static const uint32_t k[64] = {
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};
static uint32_t rr(uint32_t x, unsigned n) { return (x >> n) | (x << (32-n)); }
static void transform(struct sha256 *s) {
  uint32_t w[64],a,b,c,d,e,f,g,h;
  for (int i=0;i<16;i++) w[i]=((uint32_t)s->block[i*4]<<24)|((uint32_t)s->block[i*4+1]<<16)|((uint32_t)s->block[i*4+2]<<8)|s->block[i*4+3];
  for (int i=16;i<64;i++) w[i]=(rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10))+w[i-7]+(rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3))+w[i-16];
  a=s->h[0];b=s->h[1];c=s->h[2];d=s->h[3];e=s->h[4];f=s->h[5];g=s->h[6];h=s->h[7];
  for (int i=0;i<64;i++) { uint32_t t1=h+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+k[i]+w[i];
    uint32_t t2=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));
    h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2; }
  s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;
}
static void sha_init(struct sha256 *s) {
  static const uint32_t initial[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  memcpy(s->h,initial,sizeof(initial));s->count=0;s->used=0;
}
static void sha_update(struct sha256 *s,const unsigned char *p,size_t n) {
  s->count+=(uint64_t)n;
  while(n) { size_t take=64-s->used;if(take>n)take=n;memcpy(s->block+s->used,p,take);
    s->used+=take;p+=take;n-=take;if(s->used==64){transform(s);s->used=0;} }
}
static void sha_final(struct sha256 *s,char hex[65]) {
  uint64_t bits=s->count*8;
  s->block[s->used++]=0x80;
  if(s->used>56){memset(s->block+s->used,0,64-s->used);transform(s);s->used=0;}
  memset(s->block+s->used,0,56-s->used);
  for(int i=0;i<8;i++)s->block[56+i]=(unsigned char)(bits>>(56-8*i));
  transform(s);
  for(int i=0;i<8;i++)snprintf(hex+i*8,9,"%08x",s->h[i]);
}
static int option_contains(char *opts,const char *flag) {
  char *save=NULL;
  for(char *item=strtok_r(opts,",",&save);item;item=strtok_r(NULL,",",&save))
    if(!strcmp(item,flag))return 1;
  return 0;
}
static int mounted(const char *where,const char *fs,const char *flag) {
  FILE *f=fopen("/proc/mounts","r");char src[256],path[256],type[64],opts[512];int found=0;
  if(!f)return 0;
  while(fscanf(f,"%255s %255s %63s %511s %*d %*d",src,path,type,opts)==4) {
    if(strcmp(path,where)||strcmp(type,fs))continue;
    if(option_contains(opts,flag))found=1;
  }
  fclose(f);return found;
}
static int exact_usb_serial(void) {
  char serial[128];
  char *resolved=realpath("/sys/block/sda/device",NULL);
  char path[4096];
  if(!resolved)return 0;
  if(strlen(resolved)>=sizeof(path)) { free(resolved);return 0; }
  strcpy(path,resolved);free(resolved);
  for(;;) {
    size_t used=strlen(path);
    if(used+8<sizeof(path)) {
      FILE *f;
      memcpy(path+used,"/serial",8);
      f=fopen(path,"r");path[used]=0;
      if(f) {
        int got=fgets(serial,sizeof(serial),f)!=NULL;
        fclose(f);
        if(got) {
          serial[strcspn(serial,"\n")]=0;
          if(!strcmp(serial,"SV08_QEMU_REIMAGE_TEST_ONLY"))return 1;
        }
      }
    }
    if(!strcmp(path,"/sys")||!strcmp(path,"/"))break;
    char *slash=strrchr(path,'/');if(!slash)break;
    if(slash==path)slash[1]=0;else *slash=0;
  }
  return 0;
}
static int exact_read(int fd,size_t n) {
  size_t done=0;while(done<n){ssize_t got=read(fd,buffer+done,n-done);
    if(got<0&&errno==EINTR)continue;
    if(got<=0)return 0;
    done+=(size_t)got;
  }return 1;
}
static int exact_write(int fd,size_t n) {
  size_t done=0;while(done<n){ssize_t got=write(fd,buffer+done,n-done);
    if(got<0&&errno==EINTR)continue;
    if(got<=0)return 0;
    done+=(size_t)got;
  }return 1;
}
static int expired(time_t started) {
  time_t now=time(NULL);
  return now<started || now-started>DEADLINE_SECONDS;
}
static void finish(const char *status) {
  printf("SV08_QEMU_REIMAGE_%s\n",status);fflush(stdout);sync();reboot(RB_POWER_OFF);for(;;)pause();
}
#if defined(SV08_SHA_SELFTEST)
int main(void) {
  struct sha256 hash;char hex[65];sha_init(&hash);
  sha_update(&hash,(const unsigned char *)"abc",3);sha_final(&hash,hex);
  puts(hex);return 0;
}
#elif defined(SV08_IO_SELFTEST)
int main(void) {
  char path[]="/tmp/sv08-writer-test-XXXXXX";
  int fd=mkstemp(path),full;
  if(fd<0)return 1;
  unlink(path);
  if(write(fd,"x",1)!=1||lseek(fd,0,SEEK_SET)!=0||exact_read(fd,2))return 2;
  close(fd);
  full=open("/dev/full",O_WRONLY|O_CLOEXEC);
  if(full<0||exact_write(full,1))return 3;
  close(full);
  if(fsync(-1)==0)return 4;
  if(!expired(time(NULL)-DEADLINE_SECONDS-1))return 5;
  char rw[]="rw,proto=tcp,vers=3",ro[]="ro,proto=tcp,vers=3";
  if(option_contains(rw,"ro")||!option_contains(ro,"ro"))return 6;
  puts("short-read short-write flush-failure timeout rw-proto refused");
  return 0;
}
#else
int main(void) {
  const char *source="/image.bin",*target="/dev/sda";
  char cmd[1024],expected[65],actual[65],readback[65];
  struct stat ss,ts;uint64_t capacity=0;struct sha256 hash;
  int in=-1,out=-1;FILE *f;time_t started=time(NULL);
  if(mount("proc","/proc","proc",0,NULL)&&!mounted("/proc","proc","rw"))finish("REFUSED_PROC");
  if(mount("sysfs","/sys","sysfs",0,NULL)&&!mounted("/sys","sysfs","rw"))finish("REFUSED_SYS");
  if(mount("devtmpfs","/dev","devtmpfs",0,"mode=0755")&&!mounted("/dev","devtmpfs","rw"))finish("REFUSED_DEV");
  f=fopen("/proc/cmdline","r");if(!f||!fgets(cmd,sizeof(cmd),f))finish("REFUSED_CMDLINE");fclose(f);
  if(!strstr(cmd,"sv08.qemu_reimage=1")||!(mounted("/","nfs","ro")||mounted("/","nfs4","ro")))finish("REFUSED_ROOT");
  if(!exact_usb_serial()||access("/sys/block/sdb",F_OK)==0)finish("REFUSED_TARGET_ID");
  f=fopen("/expected.sha256","r");if(!f||!fgets(expected,sizeof(expected),f))finish("REFUSED_MANIFEST");fclose(f);
  expected[strcspn(expected,"\n")]=0;
  if(strlen(expected)!=64||strspn(expected,"0123456789abcdef")!=64)finish("REFUSED_MANIFEST");
  in=open(source,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);out=open(target,O_RDWR|O_CLOEXEC|O_NOFOLLOW|O_EXCL);
  if(in<0||out<0||fstat(in,&ss)||fstat(out,&ts)||!S_ISREG(ss.st_mode)||!S_ISBLK(ts.st_mode)||
     (uint64_t)ss.st_size!=IMAGE_BYTES||ioctl(out,BLKGETSIZE64,&capacity)||capacity!=TARGET_BYTES||
     (ss.st_dev==ts.st_dev&&ss.st_ino==ts.st_ino))
    finish("REFUSED_INPUT");
  sha_init(&hash);
  for(uint64_t done=0;done<IMAGE_BYTES;) {size_t n=(IMAGE_BYTES-done)>CHUNK?CHUNK:(size_t)(IMAGE_BYTES-done);
    if(expired(started)||!exact_read(in,n))finish("FAILED_SOURCE_READ");
    sha_update(&hash,buffer,n);done+=n;}
  sha_final(&hash,actual);
  if(strcmp(actual,expected)||lseek(in,0,SEEK_SET)!=0)finish("REFUSED_SOURCE_HASH");
  sha_init(&hash);
  for(uint64_t done=0;done<IMAGE_BYTES;) {size_t n=(IMAGE_BYTES-done)>CHUNK?CHUNK:(size_t)(IMAGE_BYTES-done);
    if(expired(started)||!exact_read(in,n)||!exact_write(out,n))finish("FAILED_WRITE");
    sha_update(&hash,buffer,n);
    done+=n;}
  sha_final(&hash,actual);
  if(strcmp(actual,expected))finish("FAILED_SOURCE_CHANGED");
  if(fsync(out)||ioctl(out,BLKFLSBUF,0)||lseek(out,0,SEEK_SET)!=0)finish("FAILED_FLUSH");
  close(in);close(out);out=open(target,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
  if(out<0||fstat(out,&ts)||!S_ISBLK(ts.st_mode)||ioctl(out,BLKGETSIZE64,&capacity)||capacity!=TARGET_BYTES)
    finish("FAILED_READBACK_OPEN");
  sha_init(&hash);
  for(uint64_t done=0;done<IMAGE_BYTES;) {size_t n=(IMAGE_BYTES-done)>CHUNK?CHUNK:(size_t)(IMAGE_BYTES-done);
    if(expired(started)||!exact_read(out,n))finish("FAILED_READBACK");
    sha_update(&hash,buffer,n);done+=n;}
  sha_final(&hash,readback);close(out);
  if(strcmp(readback,expected))finish("FAILED_READBACK_HASH");
  printf("SV08_QEMU_REIMAGE_SOURCE bytes=%llu sha256=%s root_nfs_ro=1\n",IMAGE_BYTES,actual);
  printf("SV08_QEMU_REIMAGE_READBACK bytes=%llu sha256=%s target=/dev/sda target_serial=SV08_QEMU_REIMAGE_TEST_ONLY target_bytes=%llu\n",IMAGE_BYTES,readback,(unsigned long long)capacity);
  finish("PASS");
}
#endif
