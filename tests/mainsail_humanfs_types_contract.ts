// SPDX-License-Identifier: AGPL-3.0-or-later
// Shared strict contract: run unchanged against original and replacement declarations.
import type { HfsImpl, HfsDirectoryEntry, HfsWalkEntry } from '@humanfs/types';
import { Hfs, Path, NotFoundError, PermissionError, DirectoryError, NotEmptyError } from '@humanfs/core';
import { NodeHfs, NodeHfsImpl, hfs } from '@humanfs/node';
// Compile-only assertions: never invoke this function.
function humanfsTypesContract(): void {
    type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;
    type Assert<T extends true> = T;
    type Directory = Assert<Equal<HfsDirectoryEntry, { name: string; isDirectory: boolean; isFile: boolean; isSymlink: boolean }>>;
    type Walk = Assert<Equal<keyof HfsWalkEntry, keyof HfsDirectoryEntry | 'path' | 'depth'>>;
    type WalkFields = Assert<Equal<Pick<HfsWalkEntry, 'path' | 'depth'>, { path: string; depth: number }>>;
    const optional: HfsImpl = {};
    const directory: HfsDirectoryEntry = { name: 'item', isDirectory: false, isFile: true, isSymlink: false };
    const walk: HfsWalkEntry = { ...directory, path: 'item', depth: 1 };
    // @ts-expect-error all directory flags are required
    const missingFlag: HfsDirectoryEntry = { name: 'item', isFile: true, isDirectory: false };
    // @ts-expect-error depth is numeric
    const badWalk: HfsWalkEntry = { ...directory, path: 'item', depth: 'one' };
    // @ts-expect-error walk adds required path and depth
    const missingWalk: HfsWalkEntry = directory;
    type Methods = Assert<Equal<keyof HfsImpl, 'bytes' | 'write' | 'append' | 'isFile' | 'isDirectory' | 'createDirectory' | 'delete' | 'deleteAll' | 'list' | 'size' | 'lastModified' | 'copy' | 'copyAll' | 'move' | 'moveAll'>>;
    type bytesContract = Assert<Equal<HfsImpl["bytes"], ((path: string | URL) => Promise<Uint8Array | undefined>) | undefined>>;
    // @ts-expect-error bytes rejects an invalid path
    optional.bytes?.(42);
    // @ts-expect-error bytes rejects an invalid return type
    const badbytes: HfsImpl = { bytes: async () => "invalid" };
    type writeContract = Assert<Equal<HfsImpl["write"], ((path: string | URL, contents: Uint8Array) => Promise<void>) | undefined>>;
    // @ts-expect-error write rejects an invalid path
    optional.write?.(42, new Uint8Array());
    // @ts-expect-error write rejects an invalid return type
    const badwrite: HfsImpl = { write: async () => "invalid" };
    type appendContract = Assert<Equal<HfsImpl["append"], ((path: string | URL, contents: Uint8Array) => Promise<void>) | undefined>>;
    // @ts-expect-error append rejects an invalid path
    optional.append?.(42, new Uint8Array());
    // @ts-expect-error append rejects an invalid return type
    const badappend: HfsImpl = { append: async () => "invalid" };
    type isFileContract = Assert<Equal<HfsImpl["isFile"], ((path: string | URL) => Promise<boolean>) | undefined>>;
    // @ts-expect-error isFile rejects an invalid path
    optional.isFile?.(42);
    // @ts-expect-error isFile rejects an invalid return type
    const badisFile: HfsImpl = { isFile: async () => "invalid" };
    type isDirectoryContract = Assert<Equal<HfsImpl["isDirectory"], ((path: string | URL) => Promise<boolean>) | undefined>>;
    // @ts-expect-error isDirectory rejects an invalid path
    optional.isDirectory?.(42);
    // @ts-expect-error isDirectory rejects an invalid return type
    const badisDirectory: HfsImpl = { isDirectory: async () => "invalid" };
    type createDirectoryContract = Assert<Equal<HfsImpl["createDirectory"], ((path: string | URL) => Promise<void>) | undefined>>;
    // @ts-expect-error createDirectory rejects an invalid path
    optional.createDirectory?.(42);
    // @ts-expect-error createDirectory rejects an invalid return type
    const badcreateDirectory: HfsImpl = { createDirectory: async () => "invalid" };
    type deleteContract = Assert<Equal<HfsImpl["delete"], ((path: string | URL) => Promise<boolean>) | undefined>>;
    // @ts-expect-error delete rejects an invalid path
    optional.delete?.(42);
    // @ts-expect-error delete rejects an invalid return type
    const baddelete: HfsImpl = { delete: async () => "invalid" };
    type deleteAllContract = Assert<Equal<HfsImpl["deleteAll"], ((path: string | URL) => Promise<boolean>) | undefined>>;
    // @ts-expect-error deleteAll rejects an invalid path
    optional.deleteAll?.(42);
    // @ts-expect-error deleteAll rejects an invalid return type
    const baddeleteAll: HfsImpl = { deleteAll: async () => "invalid" };
    type listContract = Assert<Equal<HfsImpl["list"], ((path: string | URL) => AsyncIterable<HfsDirectoryEntry>) | undefined>>;
    // @ts-expect-error list rejects an invalid path
    optional.list?.(42);
    // @ts-expect-error list rejects an invalid return type
    const badlist: HfsImpl = { list: async () => "invalid" };
    type sizeContract = Assert<Equal<HfsImpl["size"], ((path: string | URL) => Promise<number | undefined>) | undefined>>;
    // @ts-expect-error size rejects an invalid path
    optional.size?.(42);
    // @ts-expect-error size rejects an invalid return type
    const badsize: HfsImpl = { size: async () => "invalid" };
    type lastModifiedContract = Assert<Equal<HfsImpl["lastModified"], ((path: string | URL) => Promise<Date | undefined>) | undefined>>;
    // @ts-expect-error lastModified rejects an invalid path
    optional.lastModified?.(42);
    // @ts-expect-error lastModified rejects an invalid return type
    const badlastModified: HfsImpl = { lastModified: async () => "invalid" };
    type copyContract = Assert<Equal<HfsImpl["copy"], ((source: string | URL, destination: string | URL) => Promise<void>) | undefined>>;
    // @ts-expect-error copy rejects an invalid path
    optional.copy?.(42, 'dest');
    // @ts-expect-error copy rejects an invalid return type
    const badcopy: HfsImpl = { copy: async () => "invalid" };
    type copyAllContract = Assert<Equal<HfsImpl["copyAll"], ((source: string | URL, destination: string | URL) => Promise<void>) | undefined>>;
    // @ts-expect-error copyAll rejects an invalid path
    optional.copyAll?.(42, 'dest');
    // @ts-expect-error copyAll rejects an invalid return type
    const badcopyAll: HfsImpl = { copyAll: async () => "invalid" };
    type moveContract = Assert<Equal<HfsImpl["move"], ((source: string | URL, destination: string | URL) => Promise<void>) | undefined>>;
    // @ts-expect-error move rejects an invalid path
    optional.move?.(42, 'dest');
    // @ts-expect-error move rejects an invalid return type
    const badmove: HfsImpl = { move: async () => "invalid" };
    type moveAllContract = Assert<Equal<HfsImpl["moveAll"], ((source: string | URL, destination: string | URL) => Promise<void>) | undefined>>;
    // @ts-expect-error moveAll rejects an invalid path
    optional.moveAll?.(42, 'dest');
    // @ts-expect-error moveAll rejects an invalid return type
    const badmoveAll: HfsImpl = { moveAll: async () => "invalid" };
    // @ts-expect-error write takes bytes, not text
    optional.write?.('file', 'text');
    // @ts-expect-error append takes bytes, not text
    optional.append?.('file', 'text');
    const impl: HfsImpl = new NodeHfsImpl();
    const core = new Hfs({ impl });
    const node = new NodeHfs();
    const publicImpls: HfsImpl[] = [core, node, hfs];
    const path = new Path(['directory', 'file']);
    path.push('child'); path.pop(); path.name = 'other';
    const pathText: string = path.toString();
    const errors: Error[] = [new NotFoundError('file'), new PermissionError('file'), new DirectoryError('file'), new NotEmptyError('directory')];
    const bytes: Promise<Uint8Array | undefined> = core.bytes(new URL('file:///tmp/file'));
    const listed: AsyncIterable<HfsDirectoryEntry> = hfs.list('directory');
    const walked: AsyncIterable<HfsWalkEntry> = core.walk('directory', {
        directoryFilter: entry => entry.isDirectory,
        entryFilter: entry => entry.depth > 0 && entry.path.length > 0,
    });
    core.write('file', 'text'); core.append('file', new Uint8Array());
    core.text('file'); core.json('file'); core.arrayBuffer('file');
    core.logStart('test'); core.logEnd('test'); core.isBaseImpl(); core.setImpl(impl); core.resetImpl();
    node.bytes('file');
    node.write('file', new Uint8Array());
    node.append('file', new Uint8Array());
    node.isFile('file');
    node.isDirectory('file');
    node.createDirectory('file');
    node.delete('file');
    node.deleteAll('file');
    node.list('file');
    node.size('file');
    node.lastModified('file');
    node.copy('source', new URL('file:///dest'));
    node.copyAll('source', new URL('file:///dest'));
    node.move('source', new URL('file:///dest'));
    node.moveAll('source', new URL('file:///dest'));

    Path.from('file'); Path.fromString('file'); Path.fromURL(new URL('file:///tmp'));
    const steps: IterableIterator<string> = path.steps(); const count: number = path.size;
}
