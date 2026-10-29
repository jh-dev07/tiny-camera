#!/usr/bin/env python3
"""Download actual publicly accessible resources referenced by this discussion.
Run with Python 3.9+ on an internet-connected computer.
"""
import csv, pathlib, urllib.request, urllib.parse, zipfile, io, re, time, json
ROOT=pathlib.Path(__file__).resolve().parent
DEST=ROOT/'downloaded'; DEST.mkdir(exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 CameraResearchArchive/1.0'}
def fetch(url):
 req=urllib.request.Request(url,headers=HEADERS)
 with urllib.request.urlopen(req,timeout=45) as r:return r.read(),r.headers.get('Content-Type','')
def slug(s):return re.sub(r'[^A-Za-z0-9._-]+','_',s)[:125]
rows=list(csv.DictReader(open(ROOT/'RESOURCE_INDEX.csv',encoding='utf-8-sig')))
log=[];seen=set()
for n,row in enumerate(rows,1):
 url=row['URL']; kind=row['Resource type']; parsed=urllib.parse.urlparse(url)
 if parsed.netloc.lower()=='github.com':
  parts=parsed.path.strip('/').split('/')
  if len(parts)<2:continue
  repo=(parts[0],parts[1]);key=repo
  if key in seen:continue
  seen.add(key)
  url='https://github.com/%s/%s/archive/refs/heads/master.zip'%repo
  kind='GitHub repository snapshot'
  # Try master, then main
  urls=[url,url.replace('/master.zip','/main.zip')]
 else:urls=[url]
 success=False;err=''
 for candidate in urls:
  try:
   data,ct=fetch(candidate)
   if data[:15].lstrip().lower().startswith(b'<!doctype html') and ('pdf' in kind.lower() or 'github' in kind.lower()):raise ValueError('HTML returned instead of resource')
   suffix='.zip' if 'GitHub' in kind else ('.pdf' if data[:4]==b'%PDF' else pathlib.Path(parsed.path).suffix or '.html')
   name=slug((('-'.join(repo)) if 'GitHub' in kind else parsed.netloc+'_'+pathlib.Path(parsed.path).stem)) + suffix
   path=DEST/name;path.write_bytes(data)
   log.append({'source':row['URL'],'download_url':candidate,'local':str(path.relative_to(ROOT)),'bytes':len(data),'status':'downloaded'})
   print('OK ',name,len(data));success=True;break
  except Exception as e:err=str(e)
 if not success:
  log.append({'source':row['URL'],'download_url':url,'local':'','bytes':0,'status':'FAILED: '+err});print('FAIL',row['URL'],err)
# Convert first-page images from downloaded PDFs into PNGs when PyMuPDF is installed
try:
 import fitz
 pngdir=DEST/'pdf_preview_png';pngdir.mkdir(exist_ok=True)
 for pdf in DEST.glob('*.pdf'):
  try:
   doc=fitz.open(pdf)
   if len(doc):doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(pngdir/(pdf.stem+'.png'))
  except Exception as e:print('PNG conversion failed',pdf,e)
except ImportError:print('Optional PNG extraction: pip install pymupdf')
(ROOT/'DOWNLOAD_RESULTS.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
with zipfile.ZipFile(ROOT/'camera_resources_downloaded.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in ROOT.rglob('*'):
  if p.is_file() and p.name!='camera_resources_downloaded.zip':z.write(p,p.relative_to(ROOT))
print('Created',ROOT/'camera_resources_downloaded.zip')
