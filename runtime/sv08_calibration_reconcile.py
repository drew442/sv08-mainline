#!/usr/bin/env python3
"""Observe native SAVE_CONFIG on one persistent Klipper connection.

No publishing, restart, heat or motion. The only script is the finite guard
variable assignment. A reconnect creates a fresh validation attempt. No lease
or continued daemon availability is required after a successful acknowledgement.
"""
import sys
# The installed script is invoked with isolated Python; only its fixed runtime
# directory is admitted, never caller-controlled PYTHONPATH or working directory.
if __name__=='__main__':sys.path.insert(0,'/usr/lib/sv08')
import json
import logging
import os
from pathlib import Path
import socket
import time

from sv08_printer_calibration import KLIPPER_REVISION,canonical,parse,dependency_binding
from sv08_printer_catalog import digest,Catalog
from sv08_printer_publish import Publisher,regular,sha,persistent_context
from sv08_printer_store import PrinterStore
from sv08_state import Store

SOCKET='/run/sv08/printer_data/comms/klippy.sock'
CONFIG='/run/sv08/printer_data/config/printer.cfg'
GUARD='gcode_macro SV08_CALIBRATION_STATUS'


class AdmissionBusy(ValueError):
    """A busy state writer does not invalidate an already loaded configuration."""


def busy_admission(error):
    return isinstance(error,ValueError) and str(error).startswith((
        'System state is busy.', 'Printer configuration is busy;',
        'Shared data allocation is busy;'))


class Connection:
    def __init__(self,path=SOCKET):
        self.socket=socket.socket(socket.AF_UNIX);self.socket.settimeout(5)
        try:self.socket.connect(str(path))
        except OSError:
            self.socket.close();raise
        self.buffer=b'';self.sequence=0
    def close(self):self.socket.close()
    def call(self,method,params=None):
        self.sequence+=1;ident=self.sequence
        self.socket.sendall(json.dumps(dict(id=ident,method=method,params=params or {})).encode()+b'\x03')
        while True:
            while b'\x03' not in self.buffer:
                chunk=self.socket.recv(65536)
                if not chunk:raise ConnectionError('Klipper connection closed')
                self.buffer+=chunk
                if len(self.buffer)>4*1024*1024:raise ValueError('Klipper response exceeds limit')
            raw,self.buffer=self.buffer.split(b'\x03',1);reply=json.loads(raw)
            if reply.get('id')!=ident:continue
            if 'error' in reply:raise ValueError('Klipper request refused')
            return reply['result']
    def guard(self,ready):
        return self.call('gcode/script',dict(script='SET_GCODE_VARIABLE MACRO=SV08_CALIBRATION_STATUS VARIABLE=ready VALUE='+str(int(ready))))


def loaded(connection,config_path=CONFIG):
    info=connection.call('info')
    if info.get('state')!='ready':raise ValueError('Klipper is not ready')
    if info.get('config_file')!=str(config_path):raise ValueError('Unexpected loaded configuration path')
    # Klipper identifies its source revision in its normal v0.x-N-gHASH string.
    version=info.get('software_version','') or ''
    revision=version.rsplit('-g',1)[-1]
    if not 7<=len(revision)<=40 or not KLIPPER_REVISION.startswith(revision):raise ValueError('Unsupported loaded Klipper revision')
    status=connection.call('objects/query',dict(objects={'configfile':None}))['status']
    configfile=status.get('configfile',{})
    if not isinstance(configfile.get('config'),dict) or not isinstance(configfile.get('settings'),dict):raise ValueError('Loaded configuration is unavailable')
    connection.guard_available=GUARD in configfile['config']
    if not connection.guard_available:raise ValueError('Legacy configuration has no calibration guard')
    guard=connection.call('objects/query',dict(objects={GUARD:None}))['status'].get(GUARD,{})
    connection.setup=guard.get('setup');connection.guard_ready=guard.get('ready')
    return info,configfile


def expected_config(found,records):
    config={}
    for raw in found.values():
        if raw is None:continue
        for section,options in parse(raw.decode()).items():
            if not section.startswith('include '):config.setdefault(section,{}).update(options)
    for section,options in records.items():config.setdefault(section,{}).update(options)
    return config


def validate_loaded(configfile,expected,records):
    if canonical(configfile['config'])!=canonical(expected):raise ValueError('Loaded configuration differs from the observed publication')
    if configfile.get('save_config_pending'):raise ValueError('Calibration has unsaved changes')
    # The ready parser's settings must agree for scalar measurements too. This
    # checks effective options, rather than relying solely on textual raw config.
    for section,options in records.items():
        settings=configfile['settings'].get(section,{})
        for key in ('z_offset','position_endstop','pid_kp','pid_ki','pid_kd'):
            if key in options and (key not in settings or float(settings[key])!=float(options[key])):raise ValueError('Loaded calibration setting disagrees with native persistence')


def readiness_error(connection,expected,records):
    if getattr(connection,'setup',None)!=0 or expected.get(GUARD,{}).get('variable_setup')!='0':return ValueError('Setup configuration cannot acknowledge printing')
    for section in ('probe','bltouch'):
        if section in expected and 'z_offset' not in records.get(section,{}):return ValueError('Probe starting offset is not persisted native calibration')
    for section,options in expected.items():
        if (section in ('extruder','heater_bed') or section.startswith('heater_generic ')) and options.get('control')=='pid' and not {'control','pid_kp','pid_ki','pid_kd'}<=set(records.get(section,{})):return ValueError('PID gains require persisted native calibration')
    return None


def failure_feedback(error):
    message=str(error)
    if isinstance(error,(OSError,ConnectionError)) or message=='Klipper is not ready':
        return dict(state='pending',message='Waiting for Klipper startup or reconnection; this load remains guarded until calibration is reconciled.')
    if message=='Legacy configuration has no calibration guard' or message=='Active publication has no native calibration contract':
        return dict(state='pending',message='Prepare and review a managed Full configuration to enable automatic calibration reconciliation.')
    if message=='Setup configuration cannot acknowledge printing':
        return dict(state='pending',message='Setup keeps printing blocked. Use supported calibration tools and SAVE_CONFIG, then prepare Full when ready.')
    if message in ('Probe starting offset is not persisted native calibration','PID gains require persisted native calibration','Calibration has unsaved changes'):
        return dict(state='pending',message='Calibration is needed or has unsaved changes. Run supported Klipper calibration tools and SAVE_CONFIG, or report measured local values explicitly.')
    return dict(state='conflict',message='Native calibration cannot be acknowledged. Review unsupported SAVE_CONFIG records or configuration drift before printing.')


def mark_failure(service,pending=False,feedback=None):
    """Retain last good values; write a changed failure state once, not per poll."""
    try:
        with service.locked() as (context,record):
            state=service.load();mirror=state['draft'].get('native_calibration')
            status=feedback or (dict(state='pending',message='Waiting for Klipper to load persisted calibration. Use SAVE_CONFIG to persist any pending calibration changes.') if pending else dict(state='conflict',message='Native calibration cannot be acknowledged. Save supported calibration in Klipper and review configuration changes before printing.'))
            if mirror and mirror.get('status')!=status:
                mirror['status']=status;state['revision']+=1;service.publish(state,record)
    except (OSError,ValueError,KeyError,TypeError):pass


def reconcile_once(service,connection,config_path=CONFIG,source=None):
    """Store-before-feature lock, import mirror, recheck, same-connection ack."""
    try:
        info,configfile=loaded(connection,config_path)
        if configfile.get('save_config_pending'):raise ValueError('Calibration has unsaved changes')
        with service.locked() as (context,record):
            state=service.load()
            publisher=Publisher(service.directory.parent,source=source)
            receipt,records,root,found=publisher.active_calibration(context)
            expected=expected_config(found,records)
            validate_loaded(configfile,expected,records)
            pending=readiness_error(connection,expected,records)
            if pending and not records:raise pending
            origins=publisher.calibration_origins(receipt,records)
            mirror=dict(format_version=1,publication=receipt['review'],context=persistent_context(context),records=records,origins=origins,
                        bindings={s:dependency_binding(receipt['native']['config'],s,(receipt['native'].get('binding') or {}).get('calibration_sources')) for s in records},status=dict(state='accepted',message='Native calibration was persisted and acknowledged for this applied hardware. Each Klipper load keeps printing blocked until its own reconciliation.'))
            if 'user-reported' in origins.values():mirror['status']['message']='Persisted calibration includes user-reported values, not verified measurements. Each Klipper load requires its own reconciliation before printing.'
            if pending:mirror['status']=failure_feedback(pending)
            changed=state['draft'].get('native_calibration')!=mirror
            # Same socket, fresh info/config/settings; RESTART destroys this
            # connection. No response or acknowledgement survives that boundary.
            again_info,again=loaded(connection,config_path)
            validate_loaded(again,expected,records)
            if str(readiness_error(connection,expected,records))!=str(pending):raise ValueError('Readiness changed during reconciliation')
            if again_info!=info or again!=configfile:raise ValueError('Loaded Klipper instance changed during reconciliation')
            final,final_records,final_root,final_found=publisher.active_calibration(context)
            if final!=receipt or final_records!=records or final_root!=root:raise ValueError('Configuration changed before acknowledgement')
            def recheck_context():
                current_context,current_record=service.context()
                if current_context!=context or current_record!=record or service.directory.parent!=publisher.root:
                    raise ValueError('Current generation/boot context changed during reconciliation')
            recheck_context()
            if changed:
                state['draft']['format_version']=2;state['draft']['native_calibration']=mirror
                state['revision']+=1;service.publish(state,record)
            recheck_context()
            if pending:
                if getattr(connection,'acknowledged',False) or getattr(connection,'guard_ready',0)==1:connection.guard(False)
                connection.acknowledged=False
                return dict(changed=changed,revision=state['revision'],publication=receipt['review'],pending=mirror['status'])
            try:
                if not getattr(connection,'acknowledged',False):connection.guard(True)
                connection.acknowledged=True
            except Exception:
                # Do not expose an accepted status if acknowledgement failed.
                mirror['status']=dict(state='conflict',message='Klipper acknowledgement was interrupted; waiting for automatic reconciliation before printing.')
                state['draft']['format_version']=2;state['draft']['native_calibration']=mirror
                state['revision']+=1;service.publish(state,record)
                raise
            return dict(changed=changed,revision=state['revision'],publication=receipt['review'])
    except Exception as error:
        if busy_admission(error) and getattr(connection,'acknowledged',False):raise AdmissionBusy('State writer is busy; retained this loaded instance acknowledgement') from None
        mark_failure(service,feedback=failure_feedback(error))
        was_acknowledged=getattr(connection,'acknowledged',False);connection.acknowledged=False
        if getattr(connection,'guard_available',False) and (was_acknowledged or getattr(connection,'guard_ready',0)==1):
            try:connection.guard(False)
            except (OSError,ValueError,ConnectionError):pass
        raise


def serve(service,connect=Connection,interval=1):
    connection=None;last_warning=None
    while True:
        try:
            if connection is None:
                connection=connect()
                # A new connection always validates fully. It does not revoke
                # a prior instance acknowledgement merely because the observer
                # reconnected; each actual Klipper load initializes ready=0.
            outcome=reconcile_once(service,connection)
            feedback=outcome.get('pending')
            if feedback:
                key=(feedback['state'],feedback['message'])
                if key!=last_warning:logging.warning('%s',feedback['message']);last_warning=key
            else:last_warning=None
        except AdmissionBusy:
            pass
        except (OSError,ValueError,KeyError,TypeError,ConnectionError,json.JSONDecodeError) as error:
            feedback=failure_feedback(error)
            if connection is None:mark_failure(service,feedback=feedback)
            # Fixed actionable messages only; unchanged expected states log once.
            key=(feedback['state'],feedback['message'])
            if key!=last_warning:logging.warning('%s',feedback['message']);last_warning=key
            if connection:
                connection.close();connection=None
        time.sleep(interval)


def main():
    if os.geteuid()!=0:raise ValueError('Root-owned reconciliation service required')
    service=PrinterStore(Store('/data/sv08'),'/run/sv08/boot.json','/run/sv08/printer_data/config',Catalog('/usr/share/sv08/printer/catalog.json'))
    serve(service)


if __name__=='__main__':main()
