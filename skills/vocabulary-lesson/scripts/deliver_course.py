# -*- coding: utf-8 -*-
"""Export a versioned local course ZIP from current batch records; no uploads."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from html import escape
from script_tool import validate, render

SKILL = Path(__file__).resolve().parents[1]

def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def require(ok, message):
    if not ok: raise ValueError(message)
def local(base, name):
    require(isinstance(name,str) and name and not Path(name).is_absolute(), '材料必须使用相对路径')
    p=(base/name).resolve()
    require(p.is_relative_to(base.resolve()) and p.is_file(), '材料缺失或超出目录：'+name)
    return p

def export(batch_file, out, selected=None):
    batch_file=batch_file.resolve();base=batch_file.parent;batch=read(batch_file)
    require(not out.exists(), '交付文件已存在，请使用新的版本文件名')
    groups=batch['groups'];ids=[g['localId'] for g in groups]
    require(len(ids)==len(set(ids)), '组编号重复')
    require(all(re.fullmatch(r'[A-Za-z0-9_-]+',i) for i in ids), '组编号不适合作为目录')
    chosen=set(selected) if selected else {g['localId'] for g in groups if g['status'] in ('preview_ready','delivered')}
    require(chosen and chosen<=set(ids), '没有可交付的组，或指定组不存在')
    files={};courses=[];remaining=[]
    for g in groups:
        gid=g['localId']
        if gid not in chosen:
            remaining.append({k:g.get(k) for k in ('localId','title','status')});continue
        require(g['status'] in ('preview_ready','delivered'), '组尚未完成预览检查：'+gid)
        sp=local(base,g['scriptPath']);script=read(sp)
        validate(script,batch_file,gid,sp)
        require(script['version']==g['scriptVersion'], '当前脚本版本与记录不一致')
        timing=read(local(base,g['timingPath']))
        comp=local(base,g['compositionPath']);index=local(base,g['previewPath']);preview=index.parent
        build=read(local(preview,'build.json'));course=read(local(preview,'player-registration.json'))
        audio=local(preview,course['audio']).read_bytes();player=local(preview,'lesson-player.js').read_bytes()
        require(build['scriptSha256']==timing['scriptSha256']==sha(sp.read_bytes()), '脚本与配音/打包版本不一致')
        require(build['audioSha256']==timing['audioSha256']==sha(audio), '交付配音与时间表不一致')
        require(sha(local(base,g['audioPath']).read_bytes())==sha(audio), '批次当前配音与预览不同')
        require(build['compositionSha256']==sha(comp.read_bytes()) and build['playerSha256']==sha(player), '画面或播放器变化后尚未重新打包')
        require(course['canvas']==script['videoSize'] and course['id']==gid and abs(course['duration']-timing['duration'])<1e-6, '播放注册信息与当前脚本/时间不一致')
        require(course['segments']==timing['scenes'] and course['captions']==timing['captions'], '注册的章节或字幕已过期')
        require([(q['id'],q['time']) for q in course['interactions']]==[(q['id'],q['time']) for q in timing['interactions']], '注册的题目位置已过期')
        match=re.search(r'<script id="course-registration" type="application/json">(.*?)</script>',index.read_text(),re.S)
        require(match is not None, '预览页缺少注册数据')
        embedded=json.loads(match[1]);require(embedded['course']==course, '页面中的注册数据与独立记录不同')
        prefix='courses/'+gid+'/'
        for name in ['index.html','lesson-player.js','player-registration.json','build.json',course['audio']]:
            files[prefix+name]=local(preview,name).read_bytes()
        material='materials/'+gid+'/'
        files[material+'plan.md']=local(base,g['planPath']).read_bytes()
        files[material+'script.json']=sp.read_bytes()
        files[material+'script.md']=render(script).encode()
        files[material+'timing.json']=json.dumps(timing,ensure_ascii=False,indent=2).encode()
        # The actual delivered composition is self-contained, including its GSAP dependency.
        files[material+'composition.html']=embedded['compositionHtml'].encode()
        courses.append(dict(id=gid,sourceGroupId=g.get('sourceGroupId'),title=script['title'],words=g.get('words',[]),
            entry=prefix+'index.html',materials=material,planVersion=g['planVersion'],scriptVersion=g['scriptVersion'],
            audioVersion=g['audioVersion'],duration=course['duration'],canvas=course['canvas'],
            interactionCount=len(course['interactions']),scriptSha256=build['scriptSha256'],
            sampleAccepted=bool(g.get('previewAcceptance') and g['previewAcceptance'].get('scriptSha256')==build['scriptSha256'] and g['previewAcceptance'].get('compositionSha256')==build['compositionSha256'])))
    cards=''.join('<li><a href="'+c['entry']+'">'+escape(c['title'])+'</a><p>'+str(round(c['duration'],1))+' 秒 · '+str(c['interactionCount'])+' 道互动题</p><a href="'+c['materials']+'script.md">讲解稿</a></li>' for c in courses)
    files['index.html']=('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>课程交付包</title><style>body{max-width:880px;margin:70px auto;padding:0 25px;font:18px/1.8 Arial,sans-serif;color:#233e5b;background:#f5f6f3}h1{font-size:38px}ul{padding:0;list-style:none}li{background:white;border:1px solid #dde4e8;border-radius:14px;margin:20px 0;padding:26px}a{color:#235fa8}li>a:first-child{font-size:24px;font-weight:bold}small{color:#627887}</style><h1>课程交付包</h1><p>点击课程开始播放。课程、声音和播放器均在这个文件夹内。</p><ul>'''+cards+'''</ul><small>请通过包内预览服务打开。仅本地交付，尚未上传平台。</small></html>''').encode()
    files['preview_server.py']=(SKILL/'scripts/preview_server.py').read_bytes()
    files['使用说明.txt']=('课程交付包\n\n解压后，将整个文件夹交给 Codex，告诉它：“请运行这个文件夹内的 preview_server.py，并打开课程首页。”\n\n也可在终端进入解压目录，运行：\npython3 preview_server.py . --port 4177\n然后访问 http://127.0.0.1:4177/ 。端口占用时换一个端口。需要 Python 3.9 或以上；播放器需要现代浏览器。\n\n不要只拷贝 index.html；需要保留整个目录。课程播放无需模型或配音服务，也不需要原制作项目。\n\ncourses：可播放的课程；materials：教学方案、讲解稿、时间表和已内联资源的动画源码。delivery.json：课程清单、来源版本与文件校验信息。\n\n本包未包含服务密钥、系统配置或历史版本。后续系统导入接口尚未实现，此包当前不等于平台已接收。\n').encode()
    manifest=dict(format='english-teaching-delivery',version=1,exporterVersion='0.5',batchId=batch['batchId'],skillVersion=batch['skillVersion'],
        deliveryMode='local_zip',uploaded=False,courses=courses,notIncluded=remaining,
        files=[dict(path=n,bytes=len(v),sha256=sha(v)) for n,v in sorted(files.items())])
    files['delivery.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as target:
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for n,v in sorted(files.items()): z.writestr(n,v)
    check(out)
    return manifest

def check(archive):
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();require(len(names)==len(set(names)), '压缩包内文件名重复')
        for n in names:
            p=PurePosixPath(n)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in n, '压缩包内存在非法路径')
        m=json.loads(z.read('delivery.json'))
        require(m['format']=='english-teaching-delivery' and m['version']==1, '不支持该交付格式')
        require(set(names)=={x['path'] for x in m['files']}|{'delivery.json'}, '文件清单与压缩包不同')
        for f in m['files']:
            data=z.read(f['path']);require(len(data)==f['bytes'] and sha(data)==f['sha256'], '交付文件不完整：'+f['path'])
        for c in m['courses']:require(c['entry'] in names, '课程入口缺失')
        return m

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    ex=sub.add_parser('export');ex.add_argument('--batch',type=Path,required=True);ex.add_argument('--out',type=Path,required=True);ex.add_argument('--group',action='append')
    ch=sub.add_parser('check');ch.add_argument('archive',type=Path)
    a=p.parse_args()
    try:
        m=export(a.batch,a.out,a.group) if a.action=='export' else check(a.archive)
        print(json.dumps(dict(batchId=m['batchId'],courses=len(m['courses']),notIncluded=m['notIncluded']),ensure_ascii=False))
    except (ValueError,KeyError,OSError,zipfile.BadZipFile) as e:p.exit(1,'未完成：'+str(e)+'\n')
if __name__=='__main__':main()
