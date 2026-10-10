# -*- coding: utf-8 -*-
"""Check a joint lesson script and render its human-readable view. No network/media."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def obj(value, keys, label, optional=()):
    require(isinstance(value, dict), label + ' 应为对象')
    require(set(keys) <= set(value), label + ' 缺少字段：' + ', '.join(sorted(set(keys)-set(value))))
    require(set(value) <= set(keys) | set(optional), label + ' 含有未约定的字段')


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ' 应为非空文本')


def ident(value, label):
    text(value, label)
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', value)), label + ' 应使用字母、数字、下划线或连字符')


def number(value, label):
    require(type(value) is int and value > 0, label + ' 应为正整数')


def array(value, label, nonempty=False):
    require(isinstance(value, list) and (not nonempty or len(value)>0), label + ' 应为' + ('非空' if nonempty else '') + '数组')


def version(value):
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str) and re.fullmatch(r'v?[1-9][0-9]*', value):
        return int(value.removeprefix('v'))
    raise ValueError('方案版本无效')


def local_path(base, value):
    text(value, '相对路径')
    require(not Path(value).is_absolute(), '记录中的路径必须相对批次目录')
    p = (base / value).resolve()
    require(p.is_relative_to(base.resolve()), '路径超出批次目录')
    return p


def validate(data, batch_path, group_id, script_path):
    obj(data, ['schemaVersion','groupId','version','planVersion','planSha256','title','videoSize','visualDirection','beats','coverage'], 'script', ['reservedReadAlong'])
    require(data['schemaVersion']=='0.2', 'schemaVersion 应为 0.2')
    require(data['groupId']==group_id, '脚本组编号与执行组不一致')
    number(data['version'], '脚本版本'); number(data['planVersion'], '方案版本')
    text(data['title'], '标题'); text(data['visualDirection'], '整体画面组织')
    obj(data['videoSize'], ['width','height'], 'videoSize')
    for k,v in data['videoSize'].items(): number(v, '尺寸 '+k)
    batch = json.loads(batch_path.read_text(encoding='utf-8'))
    groups = [g for g in batch.get('groups',[]) if g.get('localId')==group_id]
    require(len(groups)==1, '批次中找不到唯一的执行组')
    group = groups[0]
    approval = group.get('approval')
    require(group.get('status') in ['approved','scripting','awaiting_confirmation','script_ready','voicing','audio_ready','animating','preview_ready','delivered'] and isinstance(approval,dict), '该组尚未批准或当前已暂停/失效')
    require(version(approval.get('planVersion'))==version(group.get('planVersion'))==data['planVersion'], '批准版本与当前方案或脚本不一致')
    plan = local_path(batch_path.parent, group.get('planPath'))
    require(script_path.resolve().parent==plan.parent, '脚本必须保存在该组方案所在目录')
    require(hashlib.sha256(plan.read_bytes()).hexdigest()==data['planSha256'], '方案内容已变化，脚本引用的摘要不匹配')
    array(data['beats'], 'beats', True)
    beat_ids=set(); speech_ids=set()
    for beat in data['beats']:
        obj(beat,['id','purpose','speech','visual','interaction'],'beat')
        ident(beat['id'],'片段编号'); text(beat['purpose'],'片段目的')
        require(beat['id'] not in beat_ids,'片段编号重复'); beat_ids.add(beat['id'])
        array(beat['speech'],'speech',True)
        local_speech=set()
        for line in beat['speech']:
            obj(line,['id','lang','text'],'speech')
            ident(line['id'],'台词编号'); text(line['text'],'台词')
            require(line['lang'] in ['zh','en'],'台词语言应为 zh/en')
            require(line['id'] not in speech_ids,'台词编号重复')
            speech_ids.add(line['id']); local_speech.add(line['id'])
        visual=beat['visual']
        obj(visual,['layout','initialState','cues','handoff'],'visual')
        for key in ['layout','initialState','handoff']: text(visual[key],key)
        array(visual['cues'],'cues')
        for cue in visual['cues']:
            obj(cue,['speechId','at','action'],'cue')
            require(cue['speechId'] in local_speech,'画面变化引用的台词不在当前片段')
            require(cue['at'] in ['start','end'],'画面锚点应为 start/end')
            text(cue['action'],'画面变化')
        q=beat['interaction']
        if q is not None:
            obj(q,['type','prompt','options','answerId','feedback'],'interaction')
            require(q['type']=='choice','本版活动题目仅支持 choice；跟读应放入预留清单')
            text(q['prompt'],'题目'); array(q['options'],'options',True)
            require(len(q['options'])>=2,'选择题至少需要两个选项')
            option_ids=set(); option_texts=set()
            for option in q['options']:
                obj(option,['id','text'],'option'); ident(option['id'],'选项编号'); text(option['text'],'选项文本')
                require(option['id'] not in option_ids,'选项编号重复')
                require(option['text'].strip() not in option_texts,'选项文本重复')
                option_ids.add(option['id']); option_texts.add(option['text'].strip())
            require(q['answerId'] in option_ids,'答案未指向现有选项')
            obj(q['feedback'],['correct','incorrect'],'feedback')
            for k,v in q['feedback'].items():text(v,'反馈 '+k)
    array(data['coverage'],'coverage',True)
    for item in data['coverage']:
        obj(item,['point','speechIds'],'coverage item'); text(item['point'],'教学点')
        array(item['speechIds'],'speechIds',True)
        require(all(i in speech_ids for i in item['speechIds']),'教学点引用了不存在的台词')
    array(data.get('reservedReadAlong',[]),'reservedReadAlong')
    for item in data.get('reservedReadAlong',[]):
        obj(item,['afterBeatId','text'],'reservedReadAlong item')
        require(item['afterBeatId'] in beat_ids,'跟读预留位置不存在')
        text(item['text'],'跟读预留文本')
    return data


def render(data):
    out=['# '+data['title'], '', f"课程脚本 v{data['version']} · 对应教学方案 v{data['planVersion']}", '', '## 整体画面思路', '', data['visualDirection'], '']
    for n,b in enumerate(data['beats'],1):
        out += [f"## {n}. {b['purpose']}", '', '**画面组织**：'+b['visual']['layout'], '', '**刚进入时**：'+b['visual']['initialState'], '']
        for s in b['speech']:
            out += [('**英文朗读**：' if s['lang']=='en' else '**中文讲解**：')+s['text'], '']
            for c in b['visual']['cues']:
                if c['speechId']==s['id']:
                    out += ['画面（'+('这句开始时' if c['at']=='start' else '这句结束时')+'）：'+c['action'], '']
        q=b['interaction']
        if q:
            out += ['**本段讲完后互动**：'+q['prompt'], '']
            out += [f"- {o['id']}：{o['text']}" for o in q['options']]
            out += ['', '**作答后才显示**', '', '答案：'+q['answerId'], '', '答对反馈：'+q['feedback']['correct'], '', '答错反馈：'+q['feedback']['incorrect'], '']
        out += ['**衔接**：'+b['visual']['handoff'], '']
    if data.get('reservedReadAlong'):
        out += ['## 跟读入口预留（不启用等待或录音）', '']
        out += ['- '+item['afterBeatId']+' 后：'+item['text'] for item in data['reservedReadAlong']]
        out += ['']
    out += ['<details><summary>教学点与台词对应（供制作核对）</summary>', '']
    out += ['- '+item['point']+' → '+', '.join(item['speechIds']) for item in data['coverage']]
    return '\n'.join(out+['','</details>',''])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script',type=Path); parser.add_argument('--batch',required=True,type=Path); parser.add_argument('--group',required=True)
    args=parser.parse_args()
    try:
        data=json.loads(args.script.read_text(encoding='utf-8'))
        validate(data,args.batch,args.group,args.script)
        output=args.script.with_suffix('.md')
        output.write_text(render(data),encoding='utf-8')
    except (ValueError,OSError,TypeError,KeyError) as e:
        parser.exit(1,'未通过：'+str(e)+'\n')
    print('结构与方案引用检查通过；阅读版：'+str(output))
    print('此检查不验证教学语义、画面美感或真实播放效果。')


if __name__=='__main__':main()
