/* SPDX-License-Identifier: MIT */
/* Whole-image transfer primitive: preserve redundant U-Boot env until last.
 * Custom gap: a sequential source copy arms an incomplete A slot. Retire when
 * a supported upstream updater provides the same raw-image ordering contract.
 */
#ifndef SV08_ENV_LAST_TRANSFER_H
#define SV08_ENV_LAST_TRANSFER_H

#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>

#define SV08_ENV_BYTES 65536U
#define SV08_ENV_COUNT 2U
static const uint64_t sv08_env_offsets[SV08_ENV_COUNT] = {4194304ULL,8388608ULL};

static int sv08_pwrite_all(int fd,const unsigned char *data,size_t length,uint64_t offset) {
  size_t done=0;
  while(done<length) {
    ssize_t n=pwrite(fd,data+done,length-done,(off_t)(offset+done));
    if(n<0&&errno==EINTR)continue;
    if(n<=0)return 0;
    done+=(size_t)n;
  }
  return 1;
}

static int sv08_pread_all(int fd,unsigned char *data,size_t length,uint64_t offset) {
  size_t done=0;
  while(done<length) {
    ssize_t n=pread(fd,data+done,length-done,(off_t)(offset+done));
    if(n<0&&errno==EINTR)continue;
    if(n<=0)return 0;
    done+=(size_t)n;
  }
  return 1;
}

/* Each call writes all bytes in [offset, offset+length) except the two exact
 * environment intervals. Caller provides ordered chunks of the verified
 * image and separately flushes/verifies all non-env bytes before finalization.
 */
static int sv08_write_without_env(int fd,const unsigned char *data,
                                  uint64_t offset,size_t length) {
  uint64_t end=offset+length,cursor=offset;
  if(end<offset)return 0;
  for(size_t i=0;i<SV08_ENV_COUNT;i++) {
    uint64_t start=sv08_env_offsets[i],stop=start+SV08_ENV_BYTES;
    if(stop<=cursor||start>=end)continue;
    if(start>cursor&&!sv08_pwrite_all(fd,data+(cursor-offset),
                                      (size_t)(start-cursor),cursor))return 0;
    if(stop>cursor)cursor=stop<end?stop:end;
  }
  return cursor>=end||sv08_pwrite_all(fd,data+(cursor-offset),
                                      (size_t)(end-cursor),cursor);
}

/* Compare only bulk-written regions. The old env ranges are checked
 * separately, then the source env records are written and verified last.
 */
static int sv08_equal_without_env(const unsigned char *source,
                                  const unsigned char *target,
                                  uint64_t offset,size_t length) {
  uint64_t end=offset+length,cursor=offset;
  if(end<offset)return 0;
  for(size_t i=0;i<SV08_ENV_COUNT;i++) {
    uint64_t start=sv08_env_offsets[i],stop=start+SV08_ENV_BYTES;
    if(stop<=cursor||start>=end)continue;
    if(start>cursor&&memcmp(source+(cursor-offset),target+(cursor-offset),
                            (size_t)(start-cursor)))return 0;
    if(stop>cursor)cursor=stop<end?stop:end;
  }
  return cursor>=end||!memcmp(source+(cursor-offset),target+(cursor-offset),
                              (size_t)(end-cursor));
}

#endif
