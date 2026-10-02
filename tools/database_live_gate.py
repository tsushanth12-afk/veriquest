"""Opt-in Windows private recovery/provisioning driver for the reviewed live gate.

Generated recovery artifacts are DPAPI-encrypted outside Git/build contexts.
The existing production runner CLI, flags, prompts and assertions are unchanged.
No secret is passed in argv, printed, or stored in a plaintext file.
"""
import argparse
import base64
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import re
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import database_gate as gate
from tools import database_live_resources as resources


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(data, decrypt=False):
    if os.name != 'nt':
        raise gate.GateError('Private recovery driver requires Windows CurrentUser DPAPI')
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    storage = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(storage, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    if decrypt:
        function = crypt.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,
                             ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        ok = function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target))
    else:
        function = crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.c_void_p,
                             ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        ok = function(ctypes.byref(source),'VeriQuest private local gate',None,None,None,1,ctypes.byref(target))
    if not ok:
        raise gate.GateError('CurrentUser DPAPI operation failed')
    try:
        return ctypes.string_at(target.data,target.size)
    finally:
        kernel.LocalFree(target.data)


def private_root():
    return Path(os.environ['LOCALAPPDATA'])/'VeriQuest'/'recovery'


def checked_directory(value):
    directory=Path(value).resolve()
    if directory.parent != private_root().resolve() or not directory.name.startswith('live-') or not directory.is_dir():
        raise gate.GateError('Unexpected private artifact directory; no fallback')
    return directory


def verify_acl(directory, sid):
    """Read the native Windows DACL without shell serialization/identity output."""
    security=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    dacl=ctypes.c_void_p(); descriptor=ctypes.c_void_p()
    security.GetNamedSecurityInfoW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,wintypes.DWORD,
        ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p)]
    if security.GetNamedSecurityInfoW(str(directory),1,4,None,None,ctypes.byref(dacl),None,ctypes.byref(descriptor)):
        raise gate.GateError('Native private directory DACL read failed')
    class ACLSize(ctypes.Structure):
        _fields_=[('count',wintypes.DWORD),('used',wintypes.DWORD),('free',wintypes.DWORD)]
    security.GetAclInformation.argtypes=[ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.c_int]
    security.GetAce.argtypes=[ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p)]
    security.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.LPWSTR)]
    security.GetSecurityDescriptorControl.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.WORD),ctypes.POINTER(wintypes.DWORD)]
    try:
        info=ACLSize(); control=wintypes.WORD(); revision=wintypes.DWORD()
        if not security.GetAclInformation(dacl,ctypes.byref(info),ctypes.sizeof(info),2):
            raise gate.GateError('Native private directory DACL inventory failed')
        if not security.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision)) or not control.value & 0x1000:
            raise gate.GateError('Private directory inheritance not protected')
        principals=set()
        for index in range(info.count):
            ace=ctypes.c_void_p()
            if not security.GetAce(dacl,index,ctypes.byref(ace)):
                raise gate.GateError('Native DACL entry inspection failed')
            header=ctypes.string_at(ace,8)
            if header[0]!=0 or header[1]&0x10 or int.from_bytes(header[4:8],'little')!=0x1f01ff:
                raise gate.GateError('Unexpected private directory ACE/rights')
            identity=wintypes.LPWSTR()
            if not security.ConvertSidToStringSidW(ace.value+8,ctypes.byref(identity)):
                raise gate.GateError('Native ACL principal conversion failed')
            try:principals.add(identity.value)
            finally:kernel.LocalFree(ctypes.cast(identity,ctypes.c_void_p))
        if info.count!=2 or principals!={sid,'S-1-5-18'}:
            raise gate.GateError('Private directory has unexpected ACL principal')
    finally:kernel.LocalFree(descriptor)


def protect_directory(directory):
    directory.mkdir(parents=True,exist_ok=False)
    sid=subprocess.run(['powershell','-NoProfile','-Command',
        '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],
        capture_output=True,check=True,timeout=15).stdout.decode().strip()
    if not sid.startswith('S-1-5-'):
        raise gate.GateError('Cannot establish private filesystem principal')
    proc=subprocess.run(['icacls',str(directory),'/inheritance:r','/grant:r',
                         '*'+sid+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],
                        capture_output=True,timeout=15)
    if proc.returncode:
        raise gate.GateError('Private recovery directory ACL setup failed')
    verify_acl(directory,sid)


def sealed_write(path,payload):
    encoded=json.dumps(payload).encode()
    encrypted=dpapi(encoded)
    with path.open('xb') as output:
        output.write(encrypted)
        output.flush()
        os.fsync(output.fileno())
    if dpapi(path.read_bytes(),decrypt=True)!=encoded:
        raise gate.GateError('Private artifact roundtrip verification failed')


def read_sealed(path):
    return json.loads(dpapi(path.read_bytes(),decrypt=True))


def run(docker,arguments,stdin=None,timeout=120):
    proc=subprocess.run([docker,*arguments],input=stdin,capture_output=True,timeout=timeout)
    if proc.returncode:
        raise gate.GateError('Private Docker operation failed; diagnostics withheld')
    return proc.stdout


def fresh(docker,plan):
    gate.verify_target(docker)
    state=gate.preflight(docker,plan)
    if state['state']!='fresh' or state['roles'] or state['auth_users']:
        raise gate.GateError('Fresh target drift: unexpected schema/roles/accounts; stop')
    return state


def restore_readability(docker,dump):
    if not dump.startswith(b'PGDMP'):
        raise gate.GateError('Snapshot lacks custom PostgreSQL archive header')
    toc=run(docker,['exec','-i','-u','postgres',gate.DB,'pg_restore','--list'],dump)
    sql=run(docker,['exec','-i','-u','postgres',gate.DB,'pg_restore','--file=-'],dump)
    if b'auth' not in toc or b'PostgreSQL database dump' not in sql:
        raise gate.GateError('Snapshot content/restore prerequisites missing')
    return {'toc_readable':True,'all_archive_blocks_readable':True,
            'toc_entries':len([line for line in toc.splitlines() if line and not line.startswith(b';')]),
            'restore_executed':False}


def snapshot(docker):
    plan=gate.load_plan()
    before=fresh(docker,plan)
    directory=private_root()/('live-'+uuid4().hex)
    protect_directory(directory)
    dump=run(docker,['exec','-u','postgres',gate.DB,'pg_dump','-Fc','-U','supabase_admin','-d','postgres'])
    globals_sql=run(docker,['exec','-u','postgres',gate.DB,'pg_dumpall','--globals-only','-U','supabase_admin'])
    readable=restore_readability(docker,dump)
    versions=run(docker,['exec','-u','postgres',gate.DB,'sh','-c',
        'pg_dump --version; pg_restore --version']).decode().strip().splitlines()
    inspected=gate.verify_target(docker)
    payload={'format':1,'project':'veriquest-local-test','container_id':inspected['Id'],
             'image_id':inspected['Image'],'manifest':plan,
             'database_dump':base64.b64encode(dump).decode(),
             'globals_sql':base64.b64encode(globals_sql).decode(),
             'dump_sha256':hashlib.sha256(dump).hexdigest(),'preflight':before}
    if b'CREATE ROLE' not in globals_sql:
        raise gate.GateError('Snapshot global role prerequisites missing')
    sealed_write(directory/'snapshot.dpapi',payload)
    restored=read_sealed(directory/'snapshot.dpapi')
    checkdump=base64.b64decode(restored['database_dump'])
    if hashlib.sha256(checkdump).hexdigest()!=payload['dump_sha256']:
        raise gate.GateError('Saved snapshot integrity check failed')
    restore_readability(docker,checkdump)
    credentials={'api_password':secrets.token_urlsafe(40),'worker_password':secrets.token_urlsafe(40)}
    if credentials['api_password']==credentials['worker_password']:
        raise gate.GateError('Credential separation failure')
    sealed_write(directory/'runtime-credentials.dpapi',credentials)
    fresh(docker,plan)
    return {'private_directory':str(directory),'snapshot_bytes':len(dump),
            'encrypted_artifact_bytes':(directory/'snapshot.dpapi').stat().st_size,
            'dump_sha256':payload['dump_sha256'],'globals_snapshot_present':True,
            'filesystem_acl':'current user + SYSTEM only','encryption':'Windows CurrentUser DPAPI',
            'versions':versions,**readable,'fresh_state_rechecked':True}


def validate_snapshot(docker,directory):
    payload=read_sealed(directory/'snapshot.dpapi')
    db=gate.verify_target(docker)
    if (payload['project']!='veriquest-local-test' or payload['container_id']!=db['Id']
        or payload['image_id']!=db['Image'] or payload['manifest']!=gate.load_plan()):
        raise gate.GateError('Target/image/manifest drift from recovery snapshot')
    dump=base64.b64decode(payload['database_dump'])
    if hashlib.sha256(dump).hexdigest()!=payload['dump_sha256']:
        raise gate.GateError('Recovery artifact checksum mismatch')
    restore_readability(docker,dump)


def documented_runner(docker,mode,credentials=None):
    # Windows getpass normally reads its console instead of piped stdin.
    # Give it a distinct stdin wrapper so its standard secure captured-stdin
    # fallback is used. Run the unchanged CLI/main, not replacement assertions.
    entry="import io,runpy,sys; path=sys.argv.pop(1); sys.argv[0]=path; sys.stdin=io.TextIOWrapper(sys.stdin.buffer); runpy.run_path(path,run_name='__main__')"
    command=[sys.executable,'-B','-c',entry,str(ROOT/'tools/database_gate.py'),'--docker',docker,'--mode',mode]
    if mode in ('bootstrap','apply'):
        command+=['--authorize-local-write']
    stdin=None if credentials is None else (credentials['api_password']+'\n'+credentials['worker_password']+'\n').encode()
    proc=subprocess.run(command,input=stdin,capture_output=True,timeout=120)
    if proc.returncode:
        raise gate.GateError('Reviewed runner '+mode+' failed; dependent steps stopped; diagnostics withheld')
    return {'mode':mode,'exit_code':proc.returncode,'result':json.loads(proc.stdout)}


def apply(docker,directory):
    validate_snapshot(docker,directory)
    fresh(docker,gate.load_plan())  # Immediately before bootstrap writes.
    credentials=read_sealed(directory/'runtime-credentials.dpapi')
    results=[documented_runner(docker,'bootstrap',credentials)]
    results.append(documented_runner(docker,'apply'))
    results.append(documented_runner(docker,'preflight'))
    results.append(documented_runner(docker,'apply'))  # Tracked asserted no-op.
    removed=json.loads(gate.psql(docker,"""BEGIN TRANSACTION READ ONLY;
      SELECT json_build_object('no_auth_usage',NOT has_schema_privilege('vq_owner','auth','USAGE'),
       'no_auth_trigger',NOT has_table_privilege('vq_owner','auth.users','TRIGGER'),
       'no_auth_references',NOT has_column_privilege('vq_owner','auth.users','id','REFERENCES'),
       'no_database_create',NOT has_database_privilege('vq_owner','postgres','CREATE'),
       'no_public_create',NOT has_schema_privilege('vq_owner','public','CREATE')); ROLLBACK;"""))
    if not all(value is True for value in removed.values()):
        raise gate.GateError('Temporary privilege inspection failed')
    return {'runner_commands':results,'temporary_owner_privileges_removed':True}


def secure_directory(directory):
    sid=subprocess.run(['powershell','-NoProfile','-Command',
        '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],
        capture_output=True,check=True,timeout=15).stdout.decode().strip()
    verify_acl(directory,sid)


def journal_path(directory,value):
    path=Path(value).resolve()
    if path.parent!=directory or not re.fullmatch(r'journal-[0-9a-f]{32}\.dpapi',path.name):
        raise gate.GateError('Unexpected journal path; exact private artifact required')
    return path


def live(docker,directory,image,interruption=None,recover=None):
    validate_snapshot(docker,directory)
    secure_directory(directory)
    target=gate.verify_target(docker);manifest=gate.load_plan()
    if gate.preflight(docker,manifest)['state']!='complete':
        raise gate.GateError('Applied ledger required before resource writes')
    gate.psql(docker,'BEGIN TRANSACTION READ ONLY;'+gate.assertions_sql()+'ROLLBACK;')
    if recover:
        path=journal_path(directory,recover);plan=read_sealed(path)
        resources.validate_plan(plan,target,manifest)
    else:
        plan=resources.new_plan(target,manifest)
        path=directory/('journal-'+uuid4().hex+'.dpapi')  # Not the account-name nonce.
        sealed_write(path,plan)  # fsync + decrypt/readback BEFORE releasing writes.
        resources.validate_plan(read_sealed(path),target,manifest)
    credentials=read_sealed(directory/'runtime-credentials.dpapi')
    entry="import io,runpy,sys; path=sys.argv.pop(1); sys.argv[0]=path; sys.stdin=io.TextIOWrapper(sys.stdin.buffer); runpy.run_path(path,run_name='__main__')"
    command=[sys.executable,'-B','-c',entry,str(ROOT/'tests/database_permission_live.py'),
             '--docker',docker,'--image',image,'--live','--authorize-local-test-writes','--journal',str(path)]
    if recover:command+=['--recover']
    if interruption:command+=['--interrupt-point',interruption]
    proc=subprocess.run(command,input=(credentials['api_password']+'\n'+credentials['worker_password']+'\n').encode(),
                        capture_output=True)
    if proc.stdout:
        report=json.loads(proc.stdout)
        sealed_write(directory/('receipt-'+uuid4().hex+'.dpapi'),report)
        return {'exit_code':proc.returncode,'journal_path':str(path),'report':report}
    raise gate.GateError('Opt-in live harness failed before safe report; dependent steps stopped')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',required=True)
    parser.add_argument('--phase',choices=['snapshot','apply','live','recover'],required=True)
    parser.add_argument('--authorize-live-database-gate',action='store_true')
    parser.add_argument('--private-directory')
    parser.add_argument('--image')
    parser.add_argument('--journal')
    parser.add_argument('--interrupt-point',choices=['signup_response','challenge_response','populated_fixtures'])
    args=parser.parse_args()
    if not args.authorize_live_database_gate:
        print('Refused: explicit local live-gate authorization required',file=sys.stderr)
        return 2
    try:
        if args.phase=='snapshot': result=snapshot(args.docker)
        else:
            directory=checked_directory(args.private_directory)
            if args.phase=='apply':result=apply(args.docker,directory)
            else:
                if not args.image:raise gate.GateError('Actual API image required')
                if args.phase=='recover' and (not args.journal or args.interrupt_point):
                    raise gate.GateError('Recovery requires one journal and no interruption flag')
                result=live(args.docker,directory,args.image,args.interrupt_point,
                            args.journal if args.phase=='recover' else None)
        print(json.dumps(result,indent=2))
        return result.get('exit_code',0)
    except Exception as exc:
        print(json.dumps({'failed':True,'phase':args.phase,'failure_type':type(exc).__name__,
                         'blocker':str(exc) if isinstance(exc,gate.GateError) else 'Private diagnostics withheld'}))
        return 1


if __name__=='__main__':sys.exit(main())
