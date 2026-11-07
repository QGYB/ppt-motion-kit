# SPDX-License-Identifier: AGPL-3.0-only
"""Inspect and assemble the playback-verified, portable PPT component subset."""
from pathlib import Path
import argparse,json,hashlib,importlib.util

ROOT=Path(__file__).resolve().parents[1]

def read(path):return json.loads(Path(path).read_text('utf-8-sig'))

def relative_file(value):
    path=(ROOT/value).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Component path escapes the installed skill')
    return path

def modules():
    rows=read(ROOT/'references/modules.json')['modules']
    return {row['module_id']:row for row in rows}

def load_native():
    spec=importlib.util.spec_from_file_location('ppt_motion_native',ROOT/'scripts/native_components.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    return native

def assemble(plan,output):
    rows=modules();selections=[];bundles=[];pages=[];previous=None
    if not plan.get('components'):raise ValueError('components must contain at least one module')
    if output.exists():raise FileExistsError('Refusing to overwrite an existing presentation')
    for item in plan['components']:
        row=rows[item['module_id']]
        if row.get('status') in ('requires_assets','requires_cleanup','reference_only'):
            raise ValueError('Module is not available for production binding')
        if item.get('pages') is not None:
            raise ValueError('This release calls complete modules; per-page slicing is not supported')
        if item.get('mechanism_parameters') and row.get('parameter_contract',{}).get('kind')!='semicircle_progress':
            raise ValueError('This module has no verified mechanism parameter contract')
        if previous and row.get('entry_requires_shared_window') and previous.get('exit_contract')!='shared_window':
            raise ValueError('This module requires a compatible shared-window predecessor')
        if row.get('locked_bindings'):
            slots=read(relative_file(row['bindings_path']))['text_slots']
            for lock in row['locked_bindings']:
                if lock['expected_text'] in item.get('text_replacements',{}):raise ValueError(lock['reason'])
                matching=[s for s in slots if s['object_name']==lock['object_name']]
                for edit in item.get('object_text_replacements',[]):
                    if any(edit['page']==s['page'] and str(edit['object_id'])==str(s['object_id']) for s in matching):
                        raise ValueError(lock['reason'])
        for field in ('object_media_replacements',):
            for edit in item.get(field,[]):
                edit['path']=str(Path(edit['path']).expanduser().resolve())
        selections.append({**{k:v for k,v in item.items() if k!='module_id'},'template_id':row['module_id']})
        previous=row
    for row in rows.values():
        count=row['page_count']
        bundles.append({'template_id':row['module_id'],'source':str(relative_file(row['native_package'])),
            'sha256':row['package_sha256'],'non_splittable_page_groups':[
                {'pages':list(range(1,count+1)),'reason':row['invocation_unit']}] if count>1 else []})
        pages.extend({'template_id':row['module_id'],'page':page,'requires_previous_state':page>1} for page in range(1,count+1))
    native=load_native()
    receipt=native.assemble({**plan,'components':selections},output,{'template_bundles':bundles,'native_components':pages})
    receipt.update({'module_ids':[x['module_id'] for x in plan['components']],
                    'prior_component_playback_inherited_for_new_output':False})
    output.with_suffix('.reuse.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8')
    return receipt

def doctor():
    from zipfile import ZipFile
    native=load_native();problems=[];checked=0;total_pages=0
    for row in modules().values():
        package=relative_file(row['native_package']);binding=relative_file(row['bindings_path'])
        if not package.exists():
            problems.append({'module_id':row['module_id'],'error':'PPT component missing; install the full skill archive from GitHub Release'});continue
        if native.digest(package)!=row['package_sha256']:
            problems.append({'module_id':row['module_id'],'error':'PPT component hash mismatch'});continue
        if not binding.exists() or read(binding)['module_id']!=row['module_id']:
            problems.append({'module_id':row['module_id'],'error':'Binding manifest mismatch'});continue
        with ZipFile(package) as z:
            if z.testzip() is not None:problems.append({'module_id':row['module_id'],'error':'Damaged ZIP member'})
            pages=len(native.ordered(z)[2])
            if pages!=row['page_count']:problems.append({'module_id':row['module_id'],'error':'Page count mismatch'})
            total_pages+=pages
        checked+=1
    return {'success':not problems,'checked_modules':checked,'pages':total_pages,'errors':problems,
            'historical_new_content_playback_verified':True,'new_output_playback_verified':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('list');p.add_argument('--query',default='');p.add_argument('--role');p.add_argument('--limit',type=int,default=30)
    p=sub.add_parser('inspect');p.add_argument('module_id');p.add_argument('--bindings',action='store_true');p.add_argument('--page',type=int)
    p=sub.add_parser('resolve');p.add_argument('--video-index',type=int,required=True)
    p=sub.add_parser('assemble');p.add_argument('plan',type=Path);p.add_argument('--output',type=Path,required=True)
    sub.add_parser('doctor');args=parser.parse_args();rows=modules()
    if args.command=='list':
        candidates=[m for m in rows.values() if (not args.role or args.role in m['role']) and args.query.casefold() in json.dumps(m,ensure_ascii=False).casefold()]
        if args.limit<1 or args.limit>100:parser.error('limit must be between 1 and 100')
        result={'total':len(candidates),'modules':[{k:m.get(k) for k in ('module_id','name','role','page_count','verification')} for m in candidates[:args.limit]]}
    elif args.command=='inspect':
        result=dict(rows[args.module_id])
        if args.bindings:
            result['bindings']=read(relative_file(result['bindings_path']))
            if args.page is not None:
                if not 1<=args.page<=result['page_count']:parser.error('page outside the module range')
                for field in ('text_slots','table_cell_slots','state_contracts','image_usage'):
                    if field in result['bindings']:result['bindings'][field]=[x for x in result['bindings'][field] if x['page']==args.page]
    elif args.command=='resolve':
        routes=read(ROOT/'references/source-routes.json')['routes']
        result=next((r for r in routes if r['index']==args.video_index),{'index':args.video_index,'available':False,'reason':'This verified subset has no callable module for the requested source'})
    elif args.command=='doctor':result=doctor()
    else:result=assemble(read(args.plan),args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.command=='doctor' and not result['success']:raise SystemExit(1)

if __name__=='__main__':main()
