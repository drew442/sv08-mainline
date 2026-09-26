/* SPDX-License-Identifier: MIT */
/* Disposable QEMU init only. Never install this in the SD diagnostic image. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

#define IMAGE_BYTES 7818182656ULL
#define TARGET_BYTES 32000000000ULL
#define CHUNK (1024 * 1024)
#define DEADLINE_SECONDS 4200
#define SYNTHETIC_MMC_BASE "/synthetic-mmc"
#define SYNTHETIC_MMC_CID "00000000000000000000000000000001"
#define SYNTHETIC_MMC_DEVICE "/dev/mmcblk0"
/* QEMU USB disk is deliberately not H616 MMC. This test-local adapter maps
 * one synthetic MMC inventory entry to its USB block descriptor by dev_t. */
#define SV08_EMMC_SECTORS (TARGET_BYTES / 512ULL)
#define SV08_CID_NO_OPEN_WRAPPER 1
#include "emmc_cid_admission.h"
#ifndef SV08_JOB_ID
#define SV08_JOB_ID "qemu-reimage-test-001"
#endif
#ifndef SV08_JOB_DESCRIPTOR_SHA256
#define SV08_JOB_DESCRIPTOR_SHA256 ""
#endif
#ifndef SV08_TEST_FAULT
#define SV08_TEST_FAULT ""
#endif
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
static int exact_usb_capacity(void) {
  FILE *f=fopen("/sys/block/sda/size","r");unsigned long long sectors=0;
  if(!f)return 0;
  int ok=fscanf(f,"%llu",&sectors)==1;fclose(f);
  return ok&&sectors==TARGET_BYTES/512;
}
/* Compare the opened block descriptor, not a second resolution of /dev/sda,
 * with the kernel's major:minor for this disposable QEMU target. */
static int read_sysfs_dev(const char *path,dev_t *number) {
  char value[64];size_t used=0;unsigned int major_num=0,minor_num=0;
  int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
  if(fd<0)return 0;
  for(;;) {
    ssize_t n=read(fd,value+used,sizeof(value)-used);
    if(n<0&&errno==EINTR)continue;
    if(n<0){close(fd);return 0;}
    if(n==0)break;
    used+=(size_t)n;
    if(used==sizeof(value)){close(fd);return 0;}
  }
  close(fd);
  if(used<4)return 0;
  size_t pos=0;
  for(int field=0;field<2;field++) {
    unsigned int number=0;size_t start=pos;
    while(pos<used&&value[pos]>='0'&&value[pos]<='9') {
      unsigned int digit=(unsigned int)(value[pos]-'0');
      if(number>(UINT32_MAX-digit)/10)return 0;
      number=number*10+digit;pos++;
    }
    if(pos==start)return 0;
    if(field==0)major_num=number;else minor_num=number;
    if(field==0) {if(pos==used||value[pos++]!=':')return 0;}
  }
  if(pos>=used||value[pos++]!='\n'||pos!=used||major_num==0)return 0;
  *number=makedev(major_num,minor_num);
  return major(*number)==major_num&&minor(*number)==minor_num;
}
static int sysfs_dev_matches(const struct stat *opened,const char *path) {
  dev_t number;
  return S_ISBLK(opened->st_mode)&&read_sysfs_dev(path,&number)&&opened->st_rdev==number;
}
static int synthetic_mmc_identity_at(const char *base,dev_t *number) {
  char device[64],path[1024];unsigned long long sectors=0;
  if(!sv08_emmc_cid_device_at(base,SYNTHETIC_MMC_CID,
                              device,sizeof(device),&sectors)||
     strcmp(device,SYNTHETIC_MMC_DEVICE)||sectors!=TARGET_BYTES/512ULL)return 0;
  /* This adapter has one fixed synthetic card path. A renamed card may still
   * pass the locator, but cannot pass this fixed mapping and is refused. */
  if(snprintf(path,sizeof(path),"%s/mmc0/mmc0:0001/block/mmcblk0/dev",base)>=
     (int)sizeof(path))return 0;
  return read_sysfs_dev(path,number)&&*number==makedev(8,0);
}
static int synthetic_mmc_identity(dev_t *number) {
  return synthetic_mmc_identity_at(SYNTHETIC_MMC_BASE,number);
}
static int hash_file(const char *path,char hex[65]) {
  int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);struct sha256 hash;
  if(fd<0)return 0;
  sha_init(&hash);
  for(;;) { ssize_t n=read(fd,buffer,sizeof(buffer));
    if(n<0&&errno==EINTR)continue;
    if(n<0){close(fd);return 0;}
    if(n==0)break;
    sha_update(&hash,buffer,(size_t)n);
  }
  close(fd);sha_final(&hash,hex);return 1;
}
static int claim_once(const char *cmd,const char *descriptor_hash) {
  char *port_arg=strstr(cmd,"sv08.claim_port=");char *end=NULL;
  long port;int fd;struct sockaddr_in address;struct timeval timeout={5,0};
  char body[512],request[1024],response[4096];size_t used=0;ssize_t n;
  const char *body_start,*expected_body;
  if(!port_arg)return 0;
  port_arg+=strlen("sv08.claim_port=");errno=0;port=strtol(port_arg,&end,10);
  if(errno||end==port_arg||port<1||port>65535||
     (*end&&*end!=' '&&*end!='\n'&&*end!='\t'))return 0;
  int body_size=snprintf(body,sizeof(body),"{\"descriptor_sha256\":\"%s\",\"job_id\":\"%s\"}",
                         descriptor_hash,SV08_JOB_ID);
  if(body_size<0||(size_t)body_size>=sizeof(body))return 0;
  int request_size=snprintf(request,sizeof(request),
      "POST /claim HTTP/1.1\r\nHost: 10.0.2.2:%ld\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s",
      port,body_size,body);
  if(request_size<0||(size_t)request_size>=sizeof(request))return 0;
  fd=socket(AF_INET,SOCK_STREAM|SOCK_CLOEXEC,0);if(fd<0)return 0;
  setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
  setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
  memset(&address,0,sizeof(address));address.sin_family=AF_INET;address.sin_port=htons((uint16_t)port);
  if(inet_pton(AF_INET,"10.0.2.2",&address.sin_addr)!=1||
     connect(fd,(struct sockaddr *)&address,sizeof(address))) {close(fd);return 0;}
  size_t sent=0;
  while(sent<(size_t)request_size) { n=send(fd,request+sent,(size_t)request_size-sent,0);
    if(n<0&&errno==EINTR)continue;
    if(n<=0){close(fd);return 0;}sent+=(size_t)n; }
  while(used<sizeof(response)-1) { n=recv(fd,response+used,sizeof(response)-1-used,0);
    if(n<0&&errno==EINTR)continue;
    if(n<0){close(fd);return 0;}
    if(n==0)break;
    used+=(size_t)n;
  }
  close(fd);response[used]=0;
  body_start=strstr(response,"\r\n\r\n");
  if(!body_start||strncmp(response,"HTTP/1.1 200 OK\r\n",17))return 0;
  body_start+=4;
  char success[512];
  int success_size=snprintf(success,sizeof(success),"CLAIMED %s %s\n",SV08_JOB_ID,descriptor_hash);
  if(success_size<0||(size_t)success_size>=sizeof(success))return 0;
  expected_body=success;
  return used-(size_t)(body_start-response)==(size_t)success_size&&
         !memcmp(body_start,expected_body,(size_t)success_size);
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
#elif defined(SV08_IDENTITY_SELFTEST)
int main(int argc,char **argv) {
  dev_t number;
  if(argc!=2||!synthetic_mmc_identity_at(argv[1],&number)) {
    puts("refused");return 0;
  }
  printf("admitted %u:%u\n",major(number),minor(number));return 0;
}
#elif defined(SV08_BINDING_SELFTEST)
int main(void) {
  char path[]="/tmp/sv08-sysfs-dev-test-XXXXXX";
  struct stat opened={0};int fd=mkstemp(path);
  if(fd<0)return 1;
  opened.st_mode=S_IFBLK;opened.st_rdev=makedev(8,0);
  const char *cases[]={"8:0\n","8:1\n","broken\n","8:0 extra\n","4294967296:0\n","8:0\n8:1\n","8:0"};
  for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
    if(ftruncate(fd,0)||lseek(fd,0,SEEK_SET)!=0||write(fd,cases[i],strlen(cases[i]))!=(ssize_t)strlen(cases[i]))return 2;
    int matched=sysfs_dev_matches(&opened,path);
    if(matched!=(i==0))return 3;
  }
  opened.st_mode=S_IFREG;
  if(sysfs_dev_matches(&opened,path))return 4;
  close(fd);unlink(path);
  puts("block-rdev match mismatch malformed changed nonblock refused");
  return 0;
}
#else
int main(void) {
  const char *source="/image.bin",*target="/dev/sda";
  char cmd[1024],expected[65],actual[65],readback[65],descriptor_hash[65];
  struct stat ss,ts;uint64_t capacity=0;struct sha256 hash;dev_t admitted_dev,confirmed_dev;
  int in=-1,out=-1;FILE *f;time_t started=time(NULL);
  if(mount("proc","/proc","proc",0,NULL)&&!mounted("/proc","proc","rw"))finish("REFUSED_PROC");
  if(mount("sysfs","/sys","sysfs",0,NULL)&&!mounted("/sys","sysfs","rw"))finish("REFUSED_SYS");
  if(mount("devtmpfs","/dev","devtmpfs",0,"mode=0755")&&!mounted("/dev","devtmpfs","rw"))finish("REFUSED_DEV");
  f=fopen("/proc/cmdline","r");if(!f||!fgets(cmd,sizeof(cmd),f))finish("REFUSED_CMDLINE");fclose(f);
  if(!strstr(cmd,"sv08.qemu_reimage=1")||!(mounted("/","nfs","ro")||mounted("/","nfs4","ro")))finish("REFUSED_ROOT");
  if(!exact_usb_serial()||!exact_usb_capacity()||access("/sys/block/sdb",F_OK)==0)finish("REFUSED_TARGET_ID");
  if(!hash_file("/job.json",descriptor_hash)||strlen(SV08_JOB_DESCRIPTOR_SHA256)!=64||
     strcmp(descriptor_hash,SV08_JOB_DESCRIPTOR_SHA256))finish("REFUSED_DESCRIPTOR");
  /* One request only. A timeout/lost response consumes the server-side job
   * but cannot reach target open; a later boot will be refused as consumed. */
  if(!claim_once(cmd,descriptor_hash))finish("REFUSED_OR_UNCERTAIN_CLAIM");
#if defined(SV08_CLAIM_ONLY)
  finish("CLAIM_ONLY_PASS");
#endif
  if(!synthetic_mmc_identity(&admitted_dev))finish("REFUSED_SYNTHETIC_MMC");
  f=fopen("/expected.sha256","r");if(!f||!fgets(expected,sizeof(expected),f))finish("REFUSED_MANIFEST");fclose(f);
  expected[strcspn(expected,"\n")]=0;
  if(strlen(expected)!=64||strspn(expected,"0123456789abcdef")!=64)finish("REFUSED_MANIFEST");
  in=open(source,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
  if(in<0||fstat(in,&ss)||!S_ISREG(ss.st_mode)||(uint64_t)ss.st_size!=IMAGE_BYTES)
    finish("REFUSED_SOURCE");
  /* This is the first target open. The single-use claim is already durable. */
  out=open(target,O_RDWR|O_CLOEXEC|O_NOFOLLOW|O_EXCL);
  if(out<0||fstat(out,&ts)||!S_ISBLK(ts.st_mode)||
     (uint64_t)ss.st_size!=IMAGE_BYTES||ioctl(out,BLKGETSIZE64,&capacity)||capacity!=TARGET_BYTES||
     !exact_usb_serial()||!exact_usb_capacity()||
     !sysfs_dev_matches(&ts,"/sys/block/sda/dev")||ts.st_rdev!=admitted_dev||
     (ss.st_dev==ts.st_dev&&ss.st_ino==ts.st_ino))
    finish("REFUSED_INPUT");
  sha_init(&hash);
  for(uint64_t done=0;done<IMAGE_BYTES;) {size_t n=(IMAGE_BYTES-done)>CHUNK?CHUNK:(size_t)(IMAGE_BYTES-done);
    if(expired(started)||!exact_read(in,n))finish("FAILED_SOURCE_READ");
    sha_update(&hash,buffer,n);done+=n;}
  sha_final(&hash,actual);
  if(strcmp(actual,expected)||lseek(in,0,SEEK_SET)!=0)finish("REFUSED_SOURCE_HASH");
  /* Recheck CID, inventory and dev_t after hashing, at the write boundary. */
  if(!synthetic_mmc_identity(&confirmed_dev)||confirmed_dev!=admitted_dev||
     !sysfs_dev_matches(&ts,"/sys/block/sda/dev"))finish("REFUSED_SYNTHETIC_MMC_CHANGED");
#if defined(SV08_TEST_FAULT) && (defined(__GNUC__) || defined(__clang__))
  if(!strcmp(SV08_TEST_FAULT,"before-write"))finish("INJECTED_BEFORE_WRITE");
  if(!strcmp(SV08_TEST_FAULT,"partial-write")||
     !strcmp(SV08_TEST_FAULT,"flush")||!strcmp(SV08_TEST_FAULT,"readback")) {
    if(!exact_read(in,CHUNK)||!exact_write(out,CHUNK))finish("FAILED_TEST_PHASE_WRITE");
    if(!strcmp(SV08_TEST_FAULT,"partial-write"))finish("INJECTED_PARTIAL_WRITE");
    if(fsync(out)||ioctl(out,BLKFLSBUF,0))finish("FAILED_FLUSH");
    if(!strcmp(SV08_TEST_FAULT,"flush"))finish("INJECTED_AFTER_FLUSH");
    close(in);
    if(lseek(out,0,SEEK_SET)!=0||!exact_read(out,CHUNK))finish("FAILED_READBACK");
    finish("INJECTED_DURING_READBACK");
  }
#endif
  sha_init(&hash);
  for(uint64_t done=0;done<IMAGE_BYTES;) {size_t n=(IMAGE_BYTES-done)>CHUNK?CHUNK:(size_t)(IMAGE_BYTES-done);
    if(expired(started)||!exact_read(in,n)||!exact_write(out,n))finish("FAILED_WRITE");
    sha_update(&hash,buffer,n);
    done+=n;}
  sha_final(&hash,actual);
  if(strcmp(actual,expected))finish("FAILED_SOURCE_CHANGED");
  if(fsync(out)||ioctl(out,BLKFLSBUF,0)||lseek(out,0,SEEK_SET)!=0)finish("FAILED_FLUSH");
  close(in);
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
