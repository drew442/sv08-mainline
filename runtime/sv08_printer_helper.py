#!/usr/bin/env python3
"""Fixed Cockpit RPC helper. All filesystem locations are installed constants."""
import json
import os
from pathlib import Path
import sys
import subprocess
from sv08_state import Store
from sv08_printer_catalog import Catalog, strict_json, DRAFT_LIMIT
from sv08_printer_store import PrinterStore
from sv08_printer_publish import validate_output


def publication_admit():
    # No connection to a physical MCU or execution of printer macros.
    for unit in ('sv08-klipper.service','klipper.service','sv08-moonraker.service','moonraker.service'):
        try:
            result=subprocess.run(['systemctl','show',unit,'-p','ActiveState','--value'],capture_output=True,text=True,timeout=3)
        except (OSError,subprocess.TimeoutExpired):return False
        if result.returncode or result.stdout.strip() not in ('inactive','failed'):return False
    return True


def main():
    try:
        if os.geteuid()!=0:raise ValueError('Administrator access is required')
        context=strict_json(Path('/usr/lib/sv08/admin-context.json').read_bytes())
        if context!={'format_version':1,'context':'host'}:raise ValueError('Unsupported host context')
        request=strict_json(sys.stdin.buffer.read(768*1024+1),768*1024)
        catalog=Catalog('/usr/share/sv08/printer/catalog.json',diagnostic=request.get('action')=='status')
        service=PrinterStore(Store('/data/sv08'),'/run/sv08/boot.json','/run/sv08/printer_data/config',catalog,publication_admit=publication_admit,publication_validate=validate_output)
        result=service.request(request)
        print(json.dumps(dict(ok=True,result=result),allow_nan=False))
    except ValueError as error:
        print(json.dumps(dict(ok=False,error=str(error))))
    except (OSError,KeyError,TypeError,RecursionError):
        # No identities, component values, private paths or raw parser errors in logs.
        print(json.dumps(dict(ok=False,error='Configuration request refused. Refresh, check missing fields or storage, and review again.')))
    return 0


if __name__=='__main__':sys.exit(main())
