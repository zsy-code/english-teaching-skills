# -*- coding: utf-8 -*-
"""Prepare a verified speech request and assemble real PCM WAV timing. Python stdlib only."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import wave
from script_tool import validate, local_path, require


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def speech_request(script, pronunciation=None):
    rules = pronunciation or {'replacements': []}
    require(isinstance(rules,dict) and set(rules)=={'replacements'} and isinstance(rules['replacements'],list), '朗读设置需要 replacements 数组')
    for rule in rules['replacements']:
        require(isinstance(rule,dict) and set(rule)=={'match','spoken'} and all(isinstance(v,str) and v.strip() for v in rule.values()), '朗读替换需要 match 与 spoken')
    lines=[]
    for b in script['beats']:
        for s in b['speech']:
            spoken=s['text']
            # Single pass: replacements cannot cascade or rewrite inside another English word.
            if rules['replacements']:
                values={r['match']:r['spoken'] for r in rules['replacements']}
                pattern=r'(?<![A-Za-z])(?:'+'|'.join(re.escape(x) for x in sorted(values,key=len,reverse=True))+r')(?![A-Za-z])'
                spoken=re.sub(pattern,lambda m:values[m.group(0)],spoken)
            row=dict(id=s['id'],beatId=b['id'],lang=s['lang'],text=s['text'])
            if spoken!=s['text']:row['spokenText']=spoken
            lines.append(row)
    return lines


def prepare(script_path, batch_path, group, out, pronunciation_path=None):
    script = read(script_path)
    validate(script, batch_path, group, script_path)
    out.mkdir(parents=True, exist_ok=True)
    pronunciation=read(pronunciation_path) if pronunciation_path else None
    request = dict(version=1, scriptSha256=digest(script_path), groupId=group,lines=speech_request(script,pronunciation))
    if pronunciation is not None:request['pronunciation']=pronunciation
    target = out / 'audio-request.json'
    if target.exists():
        require(read(target) == request, '输出目录已有不同脚本的材料，请使用新版本目录')
    save(target, request)
    return request


def pcm(path):
    with wave.open(str(path), 'rb') as wav:
        require(wav.getnchannels() == 1 and wav.getsampwidth() == 2 and wav.getcomptype() == 'NONE',
                '需要单声道 16 位 PCM WAV')
        rate = wav.getframerate()
        require(rate in (16000, 22050, 24000, 44100, 48000), '不支持该采样率')
        count = wav.getnframes()
        data = wav.readframes(count)
        require(count > 0 and len(data) == count * 2, '音频为空或数据不完整')
    return rate, count, data


def assemble(script_path, batch_path, group, out, pause_path=None):
    script = read(script_path)
    validate(script, batch_path, group, script_path)
    request = read(out / 'audio-request.json')
    require(request['scriptSha256'] == digest(script_path), '脚本已变化，请重新生成对应音频')
    expected = speech_request(script,request.get('pronunciation'))
    require(request['lines'] == expected, '配音请求与脚本台词不一致')
    manifest = read(out / 'audio-manifest.json')
    require(manifest.get('status') == 'complete' and manifest.get('requestSha256') == digest(out/'audio-request.json'),
            '配音未完成或来源已变化')
    records = manifest['lines']
    require([r['id'] for r in records] == [r['id'] for r in expected], '音频缺句、重复或顺序不一致')
    pauses = read(pause_path) if pause_path else {}
    require(isinstance(pauses, dict) and set(pauses) <= {'zhMs','enMs','beatMs','afterSpeechMs'}, '停顿设置含有未知字段')
    settings = {'zhMs':150, 'enMs':250, 'beatMs':350, 'afterSpeechMs':{}, **pauses}
    require(isinstance(settings['afterSpeechMs'], dict) and set(settings['afterSpeechMs']) <= {r['id'] for r in expected}, '停顿设置引用未知台词')
    for n in [settings['zhMs'], settings['enMs'], settings['beatMs'], *settings['afterSpeechMs'].values()]:
        require(type(n) in (int,float) and 0 <= n <= 8000, '停顿应为 0–8000 毫秒')
    payloads = []
    rate = None
    for r in records:
        file = local_path(out, r['file'])
        require(digest(file) == r['sha256'], '音频内容已变化：'+r['id'])
        this_rate, count, audio = pcm(file)
        rate = rate or this_rate
        require(this_rate == rate, '音频采样率不一致，不能直接拼接')
        payloads.append((count, audio))
    count = 0; index = 0; parts = []; scenes = []; captions = []; cues = []; checkpoints = []
    for b in script['beats']:
        start = count
        local = {}
        for i,s in enumerate(b['speech']):
            frames, audio = payloads[index]
            row = dict(id=s['id'], beatId=b['id'], lang=s['lang'], text=s['text'],
                       start=count/rate, end=(count+frames)/rate, file=records[index]['file'], frames=frames)
            parts.append(audio); count += frames
            # A scene boundary replaces the normal gap; it does not add another gap.
            gap = settings['afterSpeechMs'].get(s['id'], settings['beatMs'] if i == len(b['speech'])-1 else settings[s['lang']+'Ms'])
            if b is script['beats'][-1] and i == len(b['speech'])-1:
                gap = settings['afterSpeechMs'].get(s['id'], 0)
            silence = round(gap*rate/1000)
            parts.append(bytes(silence*2)); count += silence
            row.update(pauseAfterMs=gap, holdEnd=count/rate)
            captions.append(row); local[s['id']] = row; index += 1
        for cue in b['visual']['cues']:
            cues.append(dict(beatId=b['id'], speechId=cue['speechId'], at=cue['at'],
                             time=local[cue['speechId']][cue['at']], action=cue['action']))
        scenes.append(dict(id=b['id'], title=b['purpose'], start=start/rate, end=count/rate))
        if b['interaction']:
            checkpoints.append(dict(id='quiz-'+b['id'], beatId=b['id'], time=count/rate,
                                    wait='until_answered', interaction=b['interaction']))
    audio_path = out / 'narration.wav'
    tmp = out / 'narration.tmp.wav'
    with wave.open(str(tmp), 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(b''.join(parts))
    os.replace(tmp, audio_path)
    timing = dict(version=1, scriptSha256=digest(script_path), requestSha256=digest(out/'audio-request.json'),
                  audio='narration.wav', audioSha256=digest(audio_path), sampleRate=rate, totalFrames=count,
                  duration=count/rate, pauses=settings, scenes=scenes, captions=captions,
                  visualCues=cues, interactions=checkpoints,
                  notes='时间来自实际 WAV 采样数。字幕按整条台词计时，无逐字时间。答题等待与反馈不在主音轨。')
    save(out / 'timing.json', timing)
    return timing


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare','assemble']); p.add_argument('--script',type=Path,required=True)
    p.add_argument('--batch',type=Path,required=True); p.add_argument('--group',required=True)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--pauses',type=Path);p.add_argument('--pronunciation',type=Path)
    a=p.parse_args()
    try:
        if a.action=='prepare':
            r=prepare(a.script,a.batch,a.group,a.out,a.pronunciation);print('配音请求已保存：%d 条台词'%len(r['lines']))
        else:
            r=assemble(a.script,a.batch,a.group,a.out,a.pauses);print('真实音频 %.3f 秒，%d 个画面锚点，%d 处互动'%(r['duration'],len(r['visualCues']),len(r['interactions'])))
    except (ValueError, KeyError, OSError, wave.Error, TypeError) as err:
        p.exit(1,'未完成：'+str(err)+'\n')


if __name__=='__main__': main()
