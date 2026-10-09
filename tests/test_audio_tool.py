# -*- coding: utf-8 -*-
import copy
import json
from pathlib import Path
import sys
import unittest
import wave
import test_script_tool

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/vocabulary-lesson/scripts'))
import audio_tool as audio


class AudioChecks(unittest.TestCase):
    def setUp(self):
        self.fixture=test_script_tool.ScriptChecks();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        second=copy.deepcopy(f.script['beats'][0]);second['id']='b02';second['interaction']=None
        second['speech']=[dict(id='s03',lang='zh',text='收束。')]
        second['visual']['cues']=[dict(speechId='s03',at='end',action='结束。')]
        f.script['beats'].append(second)
        f.path.write_text(json.dumps(f.script))
        self.out=f.group/'audio-v1'
        request=audio.prepare(f.path,f.batch,'g01',self.out)
        (self.out/'clips').mkdir()
        rows=[]
        for i,line in enumerate(request['lines']):
            p=self.out/'clips'/(line['id']+'.wav')
            self.write_wav(p,24000,2400*(i+1))
            rows.append(dict(id=line['id'],file='clips/'+p.name,sha256=audio.digest(p)))
        self.manifest=dict(status='complete',requestSha256=audio.digest(self.out/'audio-request.json'),lines=rows)
        self.save_manifest()

    def write_wav(self,path,rate,frames):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(b'\x10\x00'*frames)

    def save_manifest(self):audio.save(self.out/'audio-manifest.json',self.manifest)
    def assemble(self,pauses=None):
        f=self.fixture;return audio.assemble(f.path,f.batch,'g01',self.out,pauses)

    def test_sample_timing_nonstacked_gaps_and_no_answer_audio(self):
        result=self.assemble()
        self.assertAlmostEqual(result['duration'],1.1)
        self.assertAlmostEqual(result['captions'][1]['start'],.25)
        self.assertAlmostEqual(result['scenes'][1]['start'],.8)
        self.assertAlmostEqual(result['interactions'][0]['time'],.8)
        self.assertEqual(len(result['captions']),3)
        self.assertAlmostEqual(result['visualCues'][-1]['time'],1.1)
        rate,count,_=audio.pcm(self.out/'narration.wav')
        self.assertEqual(result['totalFrames'],count);self.assertEqual(rate,24000)
        self.assertNotIn('答案', ''.join(c['text'] for c in result['captions']))

    def test_stale_script_rejected_and_new_prepare_keeps_old_version(self):
        f=self.fixture;f.script['beats'][0]['speech'][0]['text']='改过的内容。';f.path.write_text(json.dumps(f.script))
        with self.assertRaisesRegex(ValueError,'脚本已变化'):self.assemble()
        with self.assertRaisesRegex(ValueError,'新版本目录'):audio.prepare(f.path,f.batch,'g01',self.out)

    def test_missing_audio_rejected(self):
        self.manifest['lines'].pop();self.save_manifest()
        with self.assertRaisesRegex(ValueError,'缺句'):self.assemble()

    def test_corrupt_audio_rejected(self):
        (self.out/'clips/s01.wav').write_bytes(b'broken')
        with self.assertRaisesRegex(ValueError,'内容已变化'):self.assemble()

    def test_mixed_sample_rates_rejected(self):
        p=self.out/'clips/s02.wav';self.write_wav(p,16000,1600)
        self.manifest['lines'][1]['sha256']=audio.digest(p);self.save_manifest()
        with self.assertRaisesRegex(ValueError,'采样率不一致'):self.assemble()

    def test_pending_or_paused_batch_cannot_start_paid_work(self):
        f=self.fixture;f.record['groups'][0]['status']='paused';f.save_batch()
        with self.assertRaisesRegex(ValueError,'暂停'):audio.prepare(f.path,f.batch,'g01',self.out)

    def test_custom_observation_pause_moves_later_cues(self):
        file=self.out/'pauses.json';audio.save(file,dict(afterSpeechMs={'s02':1000}))
        result=self.assemble(file)
        self.assertAlmostEqual(result['scenes'][1]['start'],1.45)
        self.assertAlmostEqual(result['visualCues'][-1]['time'],1.75)

    def test_pronunciation_keeps_display_and_whole_words(self):
        source={'beats':[{'id':'b','speech':[{'id':'s','lang':'zh','text':'un- 和 unhappy，还有 -ness。'}]}]}
        rules={'replacements':[{'match':'un-','spoken':'U N'},{'match':'-ness','spoken':'N E S S'}]}
        row=audio.speech_request(source,rules)[0]
        self.assertEqual(row['text'],'un- 和 unhappy，还有 -ness。')
        self.assertEqual(row['spokenText'],'U N 和 unhappy，还有 N E S S。')
        self.assertNotIn('spokenText',audio.speech_request(source)[0])


if __name__=='__main__':unittest.main()
