# SPDX-License-Identifier: AGPL-3.0-only
"""Reuse complete source slide ranges without redesigning native effects.

list/inspect use the local component index; assemble imports complete source
objects, dependencies, timing and media. Nothing is downloaded or executed from
source slides. A successful package is still pending target-software playback.
"""
from pathlib import Path,PurePosixPath
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
import argparse,hashlib,json,posixpath,mimetypes,math,io
from lxml import etree as E

P='{http://schemas.openxmlformats.org/presentationml/2006/main}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
REL='{http://schemas.openxmlformats.org/package/2006/relationships}'
CT='{http://schemas.openxmlformats.org/package/2006/content-types}'
APPROVED={'Noto Sans SC','Noto Serif SC','庞门正道粗书体6.0'}
read=lambda p:json.loads(Path(p).read_text('utf8'))
dump=lambda e:E.tostring(e,xml_declaration=True,encoding='UTF-8',standalone=True)
def parse(b):return E.fromstring(b,E.XMLParser(resolve_entities=False,no_network=True))
def relpath(part):return str(PurePosixPath(part).parent/'_rels'/(PurePosixPath(part).name+'.rels'))
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def ordered(z):
 pres=parse(z.read('ppt/presentation.xml'));rels=parse(z.read('ppt/_rels/presentation.xml.rels'))
 rr={a.get('Id'):a for a in rels};result=[]
 for n in pres.find(P+'sldIdLst'):
  target=rr[n.get(R+'id')].get('Target')
  part=posixpath.normpath(posixpath.join('ppt',target.lstrip('/'))) if not target.startswith('/') else target.lstrip('/')
  assert part in z.namelist(),part
  result.append((deepcopy(n),part))
 return pres,rels,result

def apply_mechanism_parameters(doc,parameters,template_id):
 """Adjust the verified semicircle recipe; keep its masks, timing and direction."""
 if not parameters:return []
 assert template_id=='vid-0314-semicircle-spin','This module has no implemented parameter recipe'
 assert set(parameters)=={'progress_percentages'},'Unsupported mechanism parameter'
 values=parameters['progress_percentages']
 assert isinstance(values,list) and len(values)==3 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=100 for v in values),'Three finite percentages between0 and100 are required'
 objects={s.find('.//'+P+'cNvPr').get('name'):s for s in doc.iter() if s.tag in (P+'sp',P+'grpSp') and s.find('.//'+P+'cNvPr') is not None}
 changes=[]
 for j,(value,source_value) in enumerate(zip(values,[20,50,80])):
  group=objects[f'!!ring-group-{j}'];sid=group.find('.//'+P+'cNvPr').get('id');label=objects[f'!!percent-{j}'];runs=list(label.iter(A+'t'))
  assert ''.join(t.text or '' for t in runs)==f'{source_value}%', 'Change result labels through the linked percentage parameter, not text replacement'
  animations=[a for a in doc.iter(P+'animRot') if a.find('.//'+P+'spTgt').get('spid')==sid]
  assert len(animations)==1 and int(animations[0].get('by'))==source_value*108000,'Native half-ring baseline changed since verification'
  rotation=animations[0];rotation.set('by',str(round(value*180*60000/100)))
  runs[0].text=f'{value:g}%'
  for run in runs[1:]:run.text=''
  changes.append({'group_id':sid,'old_by':source_value*108000,'new_by':int(rotation.get('by')),'source_percentage':source_value,'new_percentage':value,'formula':'180 degrees * percentage /100; clockwise; source delay and duration preserved'})
 return changes
def assemble(plan,output,index):
 assert not output.exists(),'Choose a new output path; source or previous output is never overwritten'
 selections=plan['components'];assert selections
 records={a['template_id']:a for a in index['template_bundles']}
 # An empty shell from the first source preserves its original package defaults.
 first=records[selections[0]['template_id']];src0=Path(first['source'])
 assert digest(src0)==first['sha256'],'Source changed since component indexing'
 with ZipFile(src0) as z:
  data={n:z.read(n) for n in z.namelist()}
  pres,presrels,_=ordered(z)
 ct=parse(data['[Content_Types].xml']);lst=pres.find(P+'sldIdLst');lst.clear()
 for n in list(presrels):
  if n.get('Type','').endswith(('/slide','/slideMaster')):presrels.remove(n)
 pres.find(P+'sldMasterIdLst').clear()
 size=pres.find(P+'sldSz');tw,th=int(size.get('cx')),int(size.get('cy'))
 bindings=[];font_changes=set();timing_checks=[];warnings=[];content_type_repairs=[];relationship_repairs=[];parameter_changes=[];object_media_changes=[];counter=0;id_counter=500
 for ix,sel in enumerate(selections):
  row=records[sel['template_id']];path=Path(row['source']);assert digest(path)==row['sha256'],'Source hash mismatch'
  with ZipFile(path) as z:
   srcpres,_,slides=ordered(z);ss=srcpres.find(P+'sldSz');sw,sh=int(ss.get('cx')),int(ss.get('cy'))
   assert abs(sw/sh-tw/th)<.001,'Mixed aspect ratios require an explicit content decision; no stretch applied'
   scale=tw/sw;pages=sel.get('pages') or list(range(1,len(slides)+1))
   assert pages and len(set(pages))==len(pages) and all(1<=n<=len(slides) for n in pages)
   for group in row.get('non_splittable_page_groups',[]):
    requested=set(pages);required=set(group['pages'])
    assert not requested.intersection(required) or required.issubset(requested),{'shared_element_chain_must_remain_complete':group}
    if requested.intersection(required):
     start=pages.index(group['pages'][0])
     assert pages[start:start+len(group['pages'])]==group['pages'],{'shared_element_chain_order_and_adjacency_required':group}
   for at,page in enumerate(pages):
    component=next(a for a in index['native_components'] if a['template_id']==row['template_id'] and a['page']==page)
    if component['requires_previous_state'] and at>0:
     assert pages[at-1]==page-1,'Keep the original adjacent state chain; select the complete source range'
   selected={slides[n-1][1] for n in pages};mapped={};source_types=parse(z.read('[Content_Types].xml'))
   overrides={n.get('PartName').lstrip('/'):n.get('ContentType') for n in source_types if n.tag==CT+'Override'}
   defaults={n.get('Extension'):n.get('ContentType') for n in source_types if n.tag==CT+'Default'}
   replacements=sel.get('text_replacements',{});seen_text=set();seen_media=set()
   object_edits=sel.get('object_text_replacements',[]);seen_object_edits=set()
   image_edits=sel.get('object_media_replacements',[]);seen_image_edits=set()
   assert len({(edit['page'],str(edit['object_id'])) for edit in image_edits})==len(image_edits),'One image edit per page/object is required'
   selected_page_numbers={slides[n-1][1]:n for n in pages}
   media=sel.get('media_replacements',{})
   def import_part(part):
    nonlocal counter
    if part in mapped:return mapped[part]
    if part.startswith('ppt/slides/') and '/_rels/' not in part:
     assert part in selected,'This range links to an excluded slide. Select the complete linked source bundle.'
     new=f'ppt/slides/component_{ix}_{PurePosixPath(part).name}'
    else:new=f'ppt/components_{ix}/'+part.removeprefix('ppt/')
    mapped[part]=new
    if part in overrides:
     E.SubElement(ct,CT+'Override',PartName='/'+new,ContentType=overrides[part])
    else:
     ext=PurePosixPath(part).suffix.lstrip('.')
     if not any((n.get('Extension') or '').casefold()==ext.casefold() for n in ct):
      content_type=defaults.get(ext) or next((v for k,v in defaults.items() if k.casefold()==ext.casefold()),None)
      if content_type is None:
       content_type=mimetypes.guess_type(part)[0]
       assert content_type is not None,{'missing_source_content_type':part}
       content_type_repairs.append({'source_part':part,'inferred_content_type':content_type})
      E.SubElement(ct,CT+'Default',Extension=ext,ContentType=content_type)
    payload=z.read(part);additional_relationships=[]
    if part in media:
     image=Path(media[part]);assert image.suffix.lower()==PurePosixPath(part).suffix.lower(),'Replacement must retain source media format'
     payload=image.read_bytes();seen_media.add(part)
    if part.endswith('.xml'):
     doc=parse(payload)
     for link in doc.iter(A+'hlinkClick'):
      if link.get(R+'id')=='' and link.get('action')=='ppaction://media':
       del link.attrib[R+'id']
       relationship_repairs.append({'source_part':part,'repair':'Remove empty optional relationship ID from media action; keep action and actual embedded video relationships'})
     before=[E.tostring(n) for n in doc.findall(P+'timing')]
     if part in selected:
      for t in doc.iter(A+'t'):
       if t.text in replacements:seen_text.add(t.text);t.text=replacements[t.text]
      for edit_index,edit in enumerate(object_edits):
       if edit['page']!=selected_page_numbers[part]:continue
       matches=[shape for shape in doc.iter() if shape.tag in (P+'sp',P+'graphicFrame') and shape.find('.//'+P+'cNvPr') is not None and shape.find('.//'+P+'cNvPr').get('id')==str(edit['object_id'])]
       assert len(matches)==1,{'object_binding_not_unique':edit}
       owner=matches[0]
       if 'table_cell' in edit:
        assert owner.tag==P+'graphicFrame',{'table_cell_requires_native_table':edit}
        table=owner.find('.//'+A+'tbl');assert table is not None,{'table_cell_requires_native_table':edit}
        rc=edit['table_cell'];assert len(rc)==2 and all(type(v) is int and v>=0 for v in rc),{'zero_based_table_cell_required':edit}
        table_rows=table.findall(A+'tr');assert rc[0]<len(table_rows),{'table_row_out_of_range':edit}
        cells=table_rows[rc[0]].findall(A+'tc');assert rc[1]<len(cells),{'table_column_out_of_range':edit}
        owner=cells[rc[1]]
       runs=list(owner.iter(A+'t'))
       current=''.join(t.text or '' for t in runs)
       assert current==edit['expected_text'],{'object_text_changed_since_binding':edit,'actual':current}
       assert len(runs)==len(edit['runs']),{'retain_source_run_count':edit,'actual_runs':len(runs)}
       for node,value in zip(runs,edit['runs']):
        node.text=value
        if value and (value[0].isspace() or value[-1].isspace()):node.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
       seen_object_edits.add(edit_index)
      for edit_index,edit in enumerate(image_edits):
       if edit['page']!=selected_page_numbers[part]:continue
       from PIL import Image
       matches=[shape for shape in doc.iter() if shape.tag in (P+'sp',P+'pic') and shape.find('.//'+P+'cNvPr') is not None and shape.find('.//'+P+'cNvPr').get('id')==str(edit['object_id'])]
       assert len(matches)==1,{'image_object_binding_not_unique':edit}
       shape=matches[0];blips=list(shape.iter(A+'blip'));assert len(blips)==1,{'single_embedded_image_required':edit}
       blip=blips[0];old_rid=blip.get(R+'embed');assert old_rid and not blip.get(R+'link'),'External image links are not edited by the native image-slot route'
       original_relations=parse(z.read(relpath(part)));relation=next(r for r in original_relations if r.get('Id')==old_rid)
       assert relation.get('TargetMode')!='External' and relation.get('Type','').endswith('/image'),'Only embedded raster image relationships can be replaced'
       old_target=relation.get('Target');old_part=old_target.lstrip('/') if old_target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),old_target))
       assert old_part==edit['expected_media_part'] and hashlib.sha256(z.read(old_part)).hexdigest()==edit['expected_media_sha256'],{'image_slot_changed_since_binding':edit}
       replacement=Path(edit['path']);new_bytes=replacement.read_bytes()
       with Image.open(io.BytesIO(new_bytes)) as image:new_size=image.size;image_format=image.format;image.verify()
       assert image_format in ('PNG','JPEG'),'The native image-slot route accepts verified PNG/JPEG only'
       with Image.open(io.BytesIO(z.read(old_part))) as image:old_size=image.size
       fit=edit.get('fit','preserve_crop');assert fit in ('preserve_crop','cover')
       if fit=='preserve_crop':assert abs(new_size[0]/new_size[1]-old_size[0]/old_size[1])<.001,'Different image aspect ratio requires an explicit fit:cover decision'
       else:
        xf=shape.find(P+'spPr/'+A+'xfrm');ext=xf.find(A+'ext');frame_ratio=int(ext.get('cx'))/int(ext.get('cy'));image_ratio=new_size[0]/new_size[1]
        crop=blip.getparent().find(A+'srcRect')
        if crop is None:crop=E.Element(A+'srcRect');blip.getparent().insert(list(blip.getparent()).index(blip)+1,crop)
        crop.attrib.clear()
        if image_ratio>frame_ratio:
         inset=round((1-frame_ratio/image_ratio)*50000);crop.set('l',str(inset));crop.set('r',str(inset))
        elif image_ratio<frame_ratio:
         inset=round((1-image_ratio/frame_ratio)*50000);crop.set('t',str(inset));crop.set('b',str(inset))
       suffix='png' if image_format=='PNG' else 'jpeg';media_part=f'ppt/components_{ix}/media/object_slot_{len(object_media_changes)}.{suffix}'
       assert media_part not in data,'Fresh image slot part required';data[media_part]=new_bytes
       if not any((n.get('Extension') or '').casefold()==suffix for n in ct):E.SubElement(ct,CT+'Default',Extension=suffix,ContentType='image/png' if suffix=='png' else 'image/jpeg')
       rid=f'rIdObjectImage{edit_index}'
       assert not any(r.get('Id')==rid for r in original_relations),'Generated image relationship ID collision'
       blip.set(R+'embed',rid);additional_relationships.append({'Id':rid,'Type':R[1:-1]+'/image','Target':posixpath.relpath(media_part,posixpath.dirname(new))})
       object_media_changes.append({'source_page':edit['page'],'object_id':str(edit['object_id']),'source_media_part':old_part,'source_sha256':edit['expected_media_sha256'],'output_media_part':media_part,'replacement_sha256':hashlib.sha256(new_bytes).hexdigest(),'fit':fit,'source_frame_geometry_preserved':True,'other_instances_of_shared_media_preserved':True});seen_image_edits.add(edit_index)
     adjustments=apply_mechanism_parameters(doc,sel.get('mechanism_parameters'),row['template_id']) if part in selected else []
     if adjustments:
      # Verify that the authorized angle changes are the only timing edits.
      restored=deepcopy(doc)
      for adjustment in adjustments:
       angle=next(a for a in restored.iter(P+'animRot') if a.find('.//'+P+'spTgt').get('spid')==adjustment['group_id']);angle.set('by',str(adjustment['old_by']))
      assert before==[E.tostring(t) for t in restored.findall(P+'timing')],'Parameter recipe changed unrelated native timing'
      parameter_changes.append({'source':part,'destination':new,'adjustments':adjustments,'unrelated_timing_preserved':True})
     expected_timing=[E.tostring(t) for t in doc.findall(P+'timing')]
     if abs(scale-1)>1e-9:
      for xf in doc.iter(A+'xfrm'):
       for sub in xf:
        for key in ['x','y','cx','cy']:
         if sub.get(key) is not None:sub.set(key,str(round(int(sub.get(key))*scale)))
      for node in doc.iter():
       for key in ['sz','marL','marR','indent','lIns','rIns','tIns','bIns','blurRad','dist']:
        if node.get(key) is not None:
         try:node.set(key,str(round(int(node.get(key))*scale)))
         except ValueError:pass
       if node.tag==A+'ln' and node.get('w'):node.set('w',str(round(int(node.get('w'))*scale)))
     assert expected_timing==[E.tostring(n) for n in doc.findall(P+'timing')],'Native timing tree changed outside the explicit parameter recipe'
     if before:timing_checks.append({'source':part,'destination':new,'byte_identical':not adjustments,'verified_parameter_changes_only':bool(adjustments)})
     data[new]=dump(doc)
    else:data[new]=payload
    rp=relpath(part)
    if rp in z.namelist():
     rr=parse(z.read(rp))
     for rel in rr:
      if rel.get('TargetMode')=='External':continue
      value=rel.get('Target');target=value.lstrip('/') if value.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),value))
      dest=import_part(target);rel.set('Target',posixpath.relpath(dest,posixpath.dirname(new)))
     for attributes in additional_relationships:E.SubElement(rr,REL+'Relationship',**attributes)
     data[relpath(new)]=dump(rr)
    return new
   for page in pages:
    part=slides[page-1][1];new=import_part(part);counter+=1;id_counter+=1;rid=f'rIdComponentSlide{counter}'
    E.SubElement(presrels,REL+'Relationship',Id=rid,Type=R[1:-1]+'/slide',Target=posixpath.relpath(new,'ppt'))
    entry=deepcopy(slides[page-1][0]);entry.set('id',str(id_counter));entry.set(R+'id',rid);lst.append(entry)
    bindings.append({'output_page':counter,'source_template':row['template_id'],'source_page':page,'source_part':part,'output_part':new})
   assert set(replacements)==seen_text,{'unmatched_text':sorted(set(replacements)-seen_text)}
   assert set(media)==seen_media,{'unmatched_media':sorted(set(media)-seen_media)}
   assert seen_object_edits==set(range(len(object_edits))),{'unmatched_object_edits':sorted(set(range(len(object_edits)))-seen_object_edits)}
   assert seen_image_edits==set(range(len(image_edits))),{'unmatched_image_object_edits':sorted(set(range(len(image_edits)))-seen_image_edits)}
   masterlist=pres.find(P+'sldMasterIdLst')
   for original,new in mapped.items():
    if overrides.get(original)=='application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml':
     rid=f'rIdComponentMaster{ix}_{len(masterlist)}';E.SubElement(presrels,REL+'Relationship',Id=rid,Type=R[1:-1]+'/slideMaster',Target=posixpath.relpath(new,'ppt'))
     E.SubElement(masterlist,P+'sldMasterId',id=str(2147490000+len(masterlist)),attrib={R+'id':rid})
 # Commercial font policy also covers unselected source defaults/themes retained
 # in the shell. Geometry and timing remain unchanged by this necessary swap.
 fmap=plan.get('font_replacements',{});fallback=plan.get('font_fallback','Noto Sans SC');assert fallback in APPROVED
 for name,payload in list(data.items()):
  if not name.endswith('.xml'):continue
  doc=parse(payload);changed=False
  for node in doc.iter():
   family=node.get('typeface')
   if family is not None and family not in APPROVED:
    target=fmap.get(family,fallback);assert target in APPROVED
    node.set('typeface',target);changed=True;font_changes.add((family,target))
  if changed:data[name]=dump(doc)
 # Strip old presentation show/section/custom lists whose slide IDs no longer
 # describe the selected output. Slide content and native effects stay intact.
 for tag in ['custShowLst','sectionLst','showPr']:
  for node in pres.findall(P+tag):pres.remove(node)
 for node in pres.findall(P+'embeddedFontLst'):pres.remove(node)
 for rel in list(presrels):
  if rel.get('Type','').endswith('/font'):presrels.remove(rel)
 # Do not carry unapproved embedded font binaries into newly authored output.
 font_parts={name for name in data if PurePosixPath(name).suffix.lower() in {'.fntdata','.odttf','.ttf','.otf'}}
 for name in font_parts:data.pop(name)
 for node in list(ct):
  if node.get('PartName','').lstrip('/') in font_parts:ct.remove(node)
 # The live presentation tree is serialized after package-wide font cleanup.
 # Apply the same policy here so stale default text styles cannot reintroduce
 # source fonts when this tree replaces the earlier byte payload.
 for node in pres.iter():
  family=node.get('typeface')
  if family is not None and family not in APPROVED:
   target=fmap.get(family,fallback);assert target in APPROVED
   node.set('typeface',target);font_changes.add((family,target))
 data['ppt/presentation.xml']=dump(pres);data['ppt/_rels/presentation.xml.rels']=dump(presrels)
 if 'docProps/app.xml' in data:
  app=parse(data['docProps/app.xml'])
  for node in app.iter():
   if E.QName(node).localname=='Slides':node.text=str(counter)
  data['docProps/app.xml']=dump(app)
 # Keep the dependency closure from the package root. This removes the unused
 # shell slides and duplicated original master/media trees, not user source files.
 keep={'[Content_Types].xml'};pending=[''];visited=set()
 while pending:
  owner=pending.pop()
  if owner in visited:continue
  visited.add(owner)
  if owner:keep.add(owner)
  rp=relpath(owner) if owner else '_rels/.rels'
  if rp not in data:continue
  keep.add(rp)
  for rel in parse(data[rp]):
   if rel.get('TargetMode')=='External':continue
   target=rel.get('Target');resolved=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner),target))
   assert resolved in data,{'owner':owner,'missing':resolved}
   pending.append(resolved)
 data={name:payload for name,payload in data.items() if name in keep}
 for node in list(ct):
  if node.tag==CT+'Override' and node.get('PartName','').lstrip('/') not in data:ct.remove(node)
 data['[Content_Types].xml']=dump(ct)
 # Relationship closure is checked before publishing any new file.
 for part,payload in data.items():
  if not part.endswith('.rels'):continue
  parent=PurePosixPath(part);owner=str(parent.parent.parent/parent.name.removesuffix('.rels')) if part!='_rels/.rels' else ''
  for rel in parse(payload):
   if rel.get('TargetMode')=='External':continue
   target=rel.get('Target');resolved=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner),target))
   assert resolved in data,{'owner':owner,'missing':resolved}
 output.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(output,'w',ZIP_DEFLATED) as z:
  for name,value in data.items():z.writestr(name,value)
 with ZipFile(output) as z:
  assert z.testzip() is None
  assert len(ordered(z)[2])==counter
 receipt={'output':str(output.resolve()),'sha256':digest(output),'slides':counter,'bindings':bindings,'source_timing_checks':timing_checks,'content_type_repairs':content_type_repairs,'relationship_repairs':relationship_repairs,'mechanism_parameter_changes':parameter_changes,'object_media_changes':object_media_changes,
  'font_substitutions':[{'source':a,'production':b} for a,b in sorted(font_changes)],'whole_source_objects_and_media_reused':True,
  'target_software_playback_verified':False,'font_appearance_verified':False,'cross_component_boundaries_verified':False,'user_accepted':False}
 output.with_suffix('.reuse.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8')
 return receipt
