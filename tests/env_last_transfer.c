/* SPDX-License-Identifier: MIT */
/* Disposable regular-file exercise of the actual env-last transfer helpers. */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "fixtures/sd-network-root/env_last_transfer.h"

#define FILE_BYTES (12U*1024U*1024U)
#define CHUNK (1024U*1024U)
static unsigned char source_chunk[CHUNK],target_chunk[CHUNK];

static void demand(int good,const char *why) {
  if(!good){fprintf(stderr,"FAIL %s\n",why);exit(1);}
}

static void check_env(int fd,size_t index,unsigned char value) {
  unsigned char block[SV08_ENV_BYTES];
  demand(sv08_pread_all(fd,block,sizeof(block),sv08_env_offsets[index]),"read env");
  for(size_t i=0;i<sizeof(block);i++)demand(block[i]==value,"env changed too early");
}

int main(void) {
  FILE *source=tmpfile(),*target=tmpfile();
  demand(source&&target,"tmpfile");
  int in=fileno(source),out=fileno(target);
  demand(ftruncate(in,FILE_BYTES)==0&&ftruncate(out,FILE_BYTES)==0,"truncate");
  for(uint64_t pos=0;pos<FILE_BYTES;pos+=CHUNK) {
    for(size_t j=0;j<CHUNK;j++)source_chunk[j]=(unsigned char)(((pos+j)/4096U)%251U+1U);
    demand(sv08_pwrite_all(in,source_chunk,CHUNK,pos),"seed source");
  }
  for(size_t i=0;i<SV08_ENV_COUNT;i++) {
    memset(source_chunk,0x31+(int)i,SV08_ENV_BYTES);
    demand(sv08_pwrite_all(in,source_chunk,SV08_ENV_BYTES,sv08_env_offsets[i]),"source env");
    memset(source_chunk,0xa1+(int)i,SV08_ENV_BYTES);
    demand(sv08_pwrite_all(out,source_chunk,SV08_ENV_BYTES,sv08_env_offsets[i]),"old env");
  }
  /* A simulated power loss after any bulk chunk leaves old policy intact. */
  for(uint64_t pos=0;pos<FILE_BYTES;pos+=CHUNK) {
    demand(sv08_pread_all(in,source_chunk,CHUNK,pos),"read source");
    demand(sv08_write_without_env(out,source_chunk,pos,CHUNK),"bulk write");
    check_env(out,0,0xa1);check_env(out,1,0xa2);
  }
  demand(fsync(out)==0,"bulk flush");
  for(uint64_t pos=0;pos<FILE_BYTES;pos+=CHUNK) {
    demand(sv08_pread_all(in,source_chunk,CHUNK,pos)&&
           sv08_pread_all(out,target_chunk,CHUNK,pos),"bulk readback");
    demand(sv08_equal_without_env(source_chunk,target_chunk,pos,CHUNK),
           "bulk mismatch outside env");
  }
  /* A non-env readback fault must be detected before either env record moves. */
  unsigned char fault=0;
  demand(sv08_pwrite_all(out,&fault,1,1024),"inject fault");
  demand(sv08_pread_all(in,source_chunk,CHUNK,0)&&
         sv08_pread_all(out,target_chunk,CHUNK,0),"fault readback");
  demand(!sv08_equal_without_env(source_chunk,target_chunk,0,CHUNK),"missed fault");
  demand(sv08_write_without_env(out,source_chunk,0,CHUNK),"repair fixture");
  for(size_t i=0;i<SV08_ENV_COUNT;i++) {
    demand(sv08_pread_all(in,source_chunk,SV08_ENV_BYTES,sv08_env_offsets[i]),
           "read source env");
    demand(sv08_pwrite_all(out,source_chunk,SV08_ENV_BYTES,sv08_env_offsets[i])&&
           fsync(out)==0,"final env write");
    demand(sv08_pread_all(out,target_chunk,SV08_ENV_BYTES,sv08_env_offsets[i])&&
           !memcmp(source_chunk,target_chunk,SV08_ENV_BYTES),"final env readback");
    if(i==0)check_env(out,1,0xa2);
  }
  for(uint64_t pos=0;pos<FILE_BYTES;pos+=CHUNK) {
    demand(sv08_pread_all(in,source_chunk,CHUNK,pos)&&
           sv08_pread_all(out,target_chunk,CHUNK,pos)&&
           !memcmp(source_chunk,target_chunk,CHUNK),"final full readback");
  }
  fclose(source);fclose(target);
  puts("PASS env-last regular-file transfer, power-cut boundaries and readback");
  return 0;
}
