"""Regenerate the readable guide and a credential-free source ZIP."""
from pathlib import Path
import html
import re
import zipfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'README.md').read_text();parts=[];inside=False
for line in source.splitlines():
    if line.startswith('```'):
        parts.append('</pre>' if inside else '<pre>');inside=not inside;continue
    text=html.escape(line)
    if inside:parts.append(text+'\n');continue
    text=re.sub(r'(https://[^\s<>]+)',r'<a href="\1">\1</a>',text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    level=next((n for n in (3,2,1) if text.startswith('#'*n+' ')),None)
    if level:parts.append(f'<h{level}>'+text[level+1:]+f'</h{level}>')
    elif text:parts.append('<p>'+text+'</p>')
head='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>개발 및 설치 안내 — 기상청 성적표</title><style>body{max-width:800px;margin:35px auto;padding:0 22px;background:#f6f7f2;color:#193c34;font:14px/1.9 system-ui,sans-serif}h1{font-size:29px}h2{margin-top:45px;border-top:1px solid #cdd7c3;padding-top:23px;font-size:21px}h3{font-size:17px}a{color:#41642e;overflow-wrap:anywhere}code,pre{background:#e8ecdf;overflow-wrap:anywhere}pre{padding:15px;white-space:pre-wrap}p{margin:14px 0}</style><a href="./">← 앱으로 돌아가기</a><p><a href="kma-scorecard-source.zip" download>전체 소스 ZIP 다운로드</a></p>'
(ROOT/'dist/guide.html').write_text(head+''.join(parts)+'</html>')
files=[p for directory in ('dist','collector','tests','.github','archive','scripts') for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix not in ('.tmp','.pyc') and p!=ROOT/'dist/kma-scorecard-source.zip']+[ROOT/'README.md',ROOT/'package.json',ROOT/'.gitignore']
with zipfile.ZipFile(ROOT/'dist/kma-scorecard-source.zip','w',zipfile.ZIP_DEFLATED) as out:
    for path in files:out.write(path,str(path.relative_to(ROOT)))
