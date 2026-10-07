"""Bounded public GitHub JSON sources. All files fetched from ONE resolved commit."""
import base64
import hashlib
import re
import time
import urllib.parse
import urllib.request
from sv08_printer_catalog import keys, digest, encoded, strict_json
from sv08_printer_definitions import public_json, validate_definition, FORMAT, FILE_LIMIT, SOURCE_LIMIT, MAX_DEFINITIONS
from sv08_printer_compact import compile_records


def relative(path):
    if not isinstance(path,str) or len(path)>200 or '\\' in path or '%' in path or path.startswith('/') or any(x in ('','..','.') for x in path.split('/')):raise ValueError('Unsafe catalogue-relative path')
    if not path.endswith('.json'):raise ValueError('Only indexed JSON files are supported')
    return path


def repository(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.hostname!='github.com' or p.username or p.password or p.port or p.query or p.fragment:raise ValueError('Use a public HTTPS GitHub repository URL')
    parts=p.path.strip('/').split('/')
    if len(parts)<2 or not all(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',v) for v in parts[:2]):raise ValueError('Invalid GitHub repository')
    owner,repo=parts[:2];repo=repo.removesuffix('.git')
    ref=None;path='catalog.json'
    if len(parts)>2:
        if len(parts)<5 or parts[2]!='blob' or not re.fullmatch(r'[0-9a-f]{40}',parts[3]):raise ValueError('Manifest URLs need an exact commit; otherwise use repository URL and advanced ref/path')
        ref=parts[3];path=relative('/'.join(parts[4:]))
    return owner,repo,ref,path


class GitHub:
    def __init__(self, fetch=None):self.fetch=fetch or self.http;self.calls=0;self.deadline=time.monotonic()+60
    def http(self,path):
        request=urllib.request.Request('https://api.github.com'+path,headers={'Accept':'application/vnd.github+json','User-Agent':'SV08-Printer-Definitions','X-GitHub-Api-Version':'2022-11-28'})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args):raise ValueError('Repository redirect requires explicit acknowledgment')
        try:
            with urllib.request.build_opener(NoRedirect).open(request,timeout=10) as response:
                raw=response.read(768*1024+1)
            return strict_json(raw,768*1024)
        except (OSError,urllib.error.HTTPError):raise ValueError('GitHub request failed or rate limited; retained sources are unchanged, retry later') from None
    def get(self,path):
        self.calls+=1
        if self.calls>96 or time.monotonic()>self.deadline:raise ValueError('Source fetch request/time budget exceeded')
        result=self.fetch(path)
        if time.monotonic()>self.deadline:raise ValueError('Source fetch deadline exceeded')
        return result
    def preview(self,url,catalog,ref=None,path=None):
        owner,repo,url_ref,url_path=repository(url);path=relative(path or url_path);ref=ref or url_ref
        root='/repos/'+owner+'/'+repo;metadata=self.get(root)
        if metadata.get('private'):raise ValueError('Private repositories are not supported')
        repo_id=metadata.get('id')
        if type(repo_id) is not int or repo_id<=0:raise ValueError('Missing stable repository identity')
        commit=self.get(root+'/commits/'+urllib.parse.quote(ref or metadata['default_branch'],safe=''))['sha']
        if not re.fullmatch(r'[0-9a-f]{40}',commit):raise ValueError('Invalid resolved revision')
        tree=self.get(root+'/git/commits/'+commit)['tree']['sha'];trees={};total=0
        def tree_entries(sha):
            if sha not in trees:
                response=self.get(root+'/git/trees/'+sha)
                if response.get('truncated'):raise ValueError('Git tree too large')
                trees[sha]=response['tree']
            return trees[sha]
        def blob(name):
            nonlocal total
            parts=name.split('/');node=tree
            for i,part in enumerate(parts):
                found=next((x for x in tree_entries(node) if x['path']==part),None)
                if not found:raise ValueError('Indexed definition file not found')
                if i<len(parts)-1:
                    if found['mode']!='040000' or found['type']!='tree':raise ValueError('Non-directory source ancestry')
                    node=found['sha']
                else:
                    if found['mode']!='100644' or found['type']!='blob':raise ValueError(name+': source links, submodules and executable files are refused; commit JSON files with mode 100644 (git update-index --chmod=-x '+name+')')
                    if found.get('size',FILE_LIMIT+1)>FILE_LIMIT:raise ValueError('Indexed file oversized')
                    content=self.get(root+'/git/blobs/'+found['sha'])
                    if content.get('encoding')!='base64' or content.get('size',FILE_LIMIT+1)>FILE_LIMIT:raise ValueError('Unsupported blob encoding/size')
                    raw=base64.b64decode(content['content'],validate=False)
                    if len(raw)>FILE_LIMIT:raise ValueError('Indexed file oversized')
                    total+=len(raw)
                    if total>SOURCE_LIMIT:raise ValueError('Source exceeds cache budget')
                    return raw
        manifest_raw=blob(path);manifest=public_json(manifest_raw);validate_manifest(manifest)
        directory=path.rsplit('/',1)[0]+'/' if '/' in path else ''
        records=[];unavailable=[];file_hashes={};authored=[]
        for index in manifest['definitions']:
            name=relative(index['path']);raw=blob(directory+name);file_hash=hashlib.sha256(raw).hexdigest()
            if file_hash!=index['sha256']:raise ValueError('Definition content digest mismatch; previous source retained')
            d=public_json(raw)
            if d.get('id')!=index['id'] or d.get('version')!=index['version']:raise ValueError('Definition/index identity mismatch')
            file_hashes[d['id']+'@'+d['version']]=file_hash
            authored.append(d)
        records,errors=compile_records(authored,catalog)
        unavailable=[dict(id=d['id'],version=d['version'],reason=errors[d['id']]) for d in authored if d['id'] in errors]
        source_id='github:'+str(repo_id)+':'+(directory.rstrip('/') or '.')
        return dict(id=source_id,origin='github',repository=metadata['full_name'],repository_id=repo_id,url='https://github.com/'+metadata['full_name'],path=path,ref=ref or metadata['default_branch'],commit=commit,manifest=manifest,manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),file_hashes=file_hashes,records=records,unavailable=unavailable,enabled=True,bytes=total)


def validate_manifest(m):
    keys(m,('$schema','format_version','catalog_id','name','description','publisher','homepage','issues','license','definitions','extensions'),('format_version','catalog_id','name','publisher','license','definitions'))
    if m['format_version']!=FORMAT:raise ValueError('Unsupported catalogue version')
    if not isinstance(m['definitions'],list) or not 1<=len(m['definitions'])<=MAX_DEFINITIONS:raise ValueError('Definition count must be 1–32')
    ids=set();paths=set()
    for entry in m['definitions']:
        keys(entry,('id','version','path','sha256'),('id','version','path','sha256'));relative(entry['path'])
        if entry['id'] in ids or entry['path'] in paths:raise ValueError('Duplicate catalogue identity/path')
        ids.add(entry['id']);paths.add(entry['path'])
        if not re.fullmatch(r'[0-9a-f]{64}',entry['sha256']):raise ValueError('Invalid indexed digest')
    if len(str(m.get('extensions',{})))>8192:raise ValueError('Metadata extensions oversized')


def accept_source(sources, candidate, catalog):
    keys(candidate,('id','origin','repository','repository_id','url','path','ref','commit','manifest','manifest_sha256','file_hashes','records','unavailable','enabled','bytes','raw_files'),('id','origin','commit','manifest','records','file_hashes','enabled','bytes'))
    validate_manifest(candidate['manifest'])
    if candidate['origin'] not in ('github','local') or candidate['id']=='builtin':raise ValueError('External source cannot claim built-in origin')
    if candidate['origin']=='github':
        directory=candidate['path'].rsplit('/',1)[0] if '/' in candidate['path'] else '.'
        if candidate['id']!='github:'+str(candidate['repository_id'])+':'+directory:raise ValueError('Source identity mismatch')
        repository(candidate['url'])
        if not re.fullmatch(r'[0-9a-f]{40}',candidate['commit']):raise ValueError('Source commit required')
    indexed={r['id']+'@'+r['version']:r for r in candidate['manifest']['definitions']}
    if candidate['file_hashes']!={k:r['sha256'] for k,r in indexed.items()}:raise ValueError('Source index/digest mismatch')
    for d in candidate['records']:
        validate_definition(d,catalog)
        if d['id']+'@'+d['version'] not in indexed:raise ValueError('Source record is not indexed')
    if candidate['origin']=='local':
        verified=bundle_preview(dict(manifest=candidate['manifest'],files=candidate.get('raw_files',{})),catalog)
        if digest(verified)!=digest(candidate):raise ValueError('Local bundle preview changed; preview again')
    old=sources.get(candidate['id'])
    if old:
        if old.get('repository')!=candidate.get('repository'):raise ValueError('Source owner/rename changed; re-add with explicit review')
        for key,h in candidate['file_hashes'].items():
            if key in old['file_hashes'] and old['file_hashes'][key]!=h:raise ValueError('Published version changed bytes; author must bump version')
    result={**sources,candidate['id']:{k:v for k,v in candidate.items() if k!='raw_files'}}
    if len(encoded(result))>512*1024 or len(result)>8:raise ValueError('Source cache limit reached; retained source unchanged')
    return result


def bundle_preview(bundle,catalog):
    keys(bundle,('manifest','files'),('manifest','files'));m=bundle['manifest'];validate_manifest(m);records=[];unavailable=[];hashes={};authored=[];total=len(encoded(m))
    if set(bundle['files'])!={x['path'] for x in m['definitions']}:raise ValueError('Bundle must contain exactly indexed files')
    for row in m['definitions']:
        raw=base64.b64decode(bundle['files'][row['path']],validate=True);total+=len(raw)
        if total>SOURCE_LIMIT or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Bundle budget/digest mismatch')
        d=public_json(raw)
        if d.get('id')!=row['id'] or d.get('version')!=row['version']:raise ValueError('Bundle index mismatch')
        hashes[d['id']+'@'+d['version']]=row['sha256']
        authored.append(d)
    records,errors=compile_records(authored,catalog)
    unavailable=[dict(id=d['id'],version=d['version'],reason=errors[d['id']]) for d in authored if d['id'] in errors]
    return dict(id='local:'+digest(m),origin='local',commit=digest(m),manifest=m,records=records,file_hashes=hashes,unavailable=unavailable,enabled=True,bytes=total,raw_files=bundle['files'])
