#!/usr/bin/env python3
"""One private isolated production-validator invocation in a disposable ARM64 guest.

Stage this file, recovery_restore_stack.py and sv08_printer_publish.py together
in a root-owned 0700 /run directory. Installed /usr/lib/sv08 dependencies,
/usr/share/sv08/printer catalog/dictionary and /opt pinned Klipper are required.
No credentials, MCU, Identity, service or network provisioning is performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

SOURCE=Path(__file__).resolve().parent
sys.path[:0]=[str(SOURCE),'/usr/lib/sv08']
from recovery_restore_stack import factory, MARKER, require, write_json
from sv08_printer_generate import generate
from sv08_printer_publish import Publisher, validate_output, inventory


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def probe(work, marker):
    work=Path(work).absolute();marker=Path(marker).absolute()
    require(os.geteuid()==0 and platform.system()=='Linux' and platform.machine().lower() in ('arm64','aarch64'),
            'Isolated root Linux ARM64 guest required')
    require(all(not p.is_symlink() for p in (work,*work.parents,marker,*marker.parents)),'Real private probe paths required')
    require(work.parent.stat().st_uid==0 and not work.parent.stat().st_mode & 0o077 and not work.exists(),
            'Fresh work beneath root-owned private directory required')
    require(marker.stat().st_uid==0 and not marker.stat().st_mode & 0o077 and marker.read_text()==MARKER,'Private disposable marker required')
    for name in ('printer_validator_probe.py','sv08_printer_publish.py','recovery_restore_stack.py'):
        path=SOURCE/name
        require(path.is_file() and not path.is_symlink() and path.stat().st_uid==0 and not path.stat().st_mode & 0o022,
                'Current source-bound staged probe/helper/driver required')
    require(Path(sys.modules['sv08_printer_publish'].__file__).resolve()==SOURCE/'sv08_printer_publish.py',
            'Staged validator must be invoked')
    work.mkdir(mode=0o700);config=work/'config';config.mkdir(mode=0o700)
    catalog,draft=factory('/usr/share/sv08/printer/catalog.json','restored')
    generated=generate(catalog,draft,'full')
    require(generated['complete'] and not generated['printing_enabled'],'Uncalibrated full factory protections required')
    # Provision publishes only hardware.cfg into an initially empty activation
    # root; its remaining software files are written after publication.
    preview=Publisher(config).preview({'hardware.cfg':generated['text']},{'probe':'restored'},'probe')
    paths={'helper':SOURCE/'sv08_printer_publish.py','guest_factory':SOURCE/'recovery_restore_stack.py',
           'probe':SOURCE/'printer_validator_probe.py','catalog':Path('/usr/share/sv08/printer/catalog.json'),
           'dictionary':Path('/usr/share/sv08/printer/validation/klipper.dict'),
           'klippy':Path('/opt/sv08-mainline/klipper/klippy/klippy.py'),
           'python':Path('/opt/sv08-mainline/venvs/klipper-f0892d8/bin/python')}
    record=dict(operation='restored factory publication preview',result='FAIL',physical_hardware=False,printing_ready=False,
                source_sha256={key:sha(path) for key,path in paths.items()},kernel=platform.release(),architecture=platform.machine(),
                python_version=sys.version,installed_helper_sha256=sha('/usr/lib/sv08/sv08_printer_publish.py'),
                activation_sha256=hashlib.sha256(preview['activation'].encode()).hexdigest(),
                files_sha256={key:hashlib.sha256(value.encode()).hexdigest() for key,value in generated['files'].items()},
                validator_input_sha256={'printer.cfg':hashlib.sha256(preview['activation'].encode()).hexdigest(),
                    'printer-managed/'+preview['review']+'/hardware.cfg':hashlib.sha256(generated['text'].encode()).hexdigest(),
                    'printer-managed/'+preview['review']+'/bundle.cfg':hashlib.sha256(b'[include hardware.cfg]\n').hexdigest()},
                loaded_module_sha256={name:sha(module.__file__) for name,module in sys.modules.copy().items()
                    if name.startswith('sv08_') and getattr(module,'__file__',None) and Path(module.__file__).is_file()},
                hardware_sha256=hashlib.sha256(generated['text'].encode()).hexdigest(),current_include_closure=list(inventory(config)[0]))
    write_json(work/'preview-private.json',preview)
    captures=[]
    try:
        record['validation']=validate_output(preview,config,private_diagnostics=captures.append,isolated_children=True)
        require(record['validation'].get('validated') and len(captures)==1,'Real validator and private capture required')
        record['result']='PASS'
    except Exception as error:
        record['failure_type']=type(error).__name__;record['failure_private']=str(error)
    finally:
        record['diagnostics_private']=captures
        write_json(work/'probe-private.json',record)
    return record['result']=='PASS'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True);parser.add_argument('--marker',type=Path,required=True)
    args=parser.parse_args()
    passed=probe(args.work,args.marker)
    print('Validator probe PASS' if passed else 'Validator probe FAIL; inspect private receipt')
    return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
