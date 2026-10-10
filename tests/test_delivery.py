# -*- coding: utf-8 -*-
import sys,json,shutil,unittest,zipfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/vocabulary-lesson/scripts'))
from deliver_course import export,check
import test_audio_tool

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        fixture=test_audio_tool.AudioChecks();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.assemble(); f=fixture.fixture
        self.root=f.root;self.base=f.root;self.bp=f.batch;self.batch=f.record
        self.batch.update(batchId='synthetic-delivery-test',skillVersion='0.5')
        g=self.batch['groups'][0]
        g.update(status='preview_ready',scriptVersion=1,audioVersion=1,
            scriptPath=str(f.path.relative_to(self.base)),audioPath='groups/g01/audio-v1/narration.wav',
            timingPath='groups/g01/audio-v1/timing.json',compositionPath='composition.html',previewPath='preview/index.html')
        # Synthetic fixture is built on every run; no private course files or paid audio.
        (self.base/'composition.html').write_text('<!doctype html><meta charset="utf-8"><div>测试</div>')
        self.save();self.out=self.root/'delivery.zip'
        node=shutil.which('node')
        if not node: raise RuntimeError('Delivery tests require Node.js 22+')
        subprocess.run([node,str(ROOT/'skills/vocabulary-lesson/scripts/package_course.mjs'),
            '--script',str(f.path),'--timing',str(fixture.out/'timing.json'),
            '--html',str(self.base/'composition.html'),'--timeline','test',
            '--content-height','920','--out',str(self.base/'preview')],check=True,capture_output=True)
    def save(self):self.bp.write_text(json.dumps(self.batch,ensure_ascii=False))
    def test_export_integrity_and_scope(self):
        (self.base/'preview/.env').write_text('FAKE_SECRET_NOT_FOR_EXPORT')
        self.batch['groups'].append({'localId':'waiting','title':'未确认组','status':'awaiting_confirmation'});self.save()
        result=export(self.bp,self.out)
        self.assertEqual(len(result['courses']),1);self.assertEqual(result['notIncluded'][0]['localId'],'waiting')
        self.assertEqual(check(self.out)['courses'][0]['scriptVersion'],1)
        with zipfile.ZipFile(self.out) as z:
            self.assertNotIn('courses/g01/.env',z.namelist());self.assertIn('materials/g01/composition.html',z.namelist())
    def test_subject_v2_delivery(self):
        self.batch['lessonType']='grammar'
        self.batch['groups'][0].update(sourceItemId='item-1',sourceHash='a'*64)
        self.save()
        result=export(self.bp,self.out)
        self.assertEqual(result['version'],2)
        self.assertEqual(result['courses'][0]['sourceItemId'],'item-1')
        self.assertNotIn('words',result['courses'][0])
        self.assertEqual(check(self.out)['courses'][0]['lessonType'],'grammar')
    def test_subject_missing_source_rejected(self):
        self.batch['lessonType']='text';self.save()
        with self.assertRaisesRegex(ValueError,'sourceHash'):export(self.bp,self.out)
    def test_pending_group_cannot_export(self):
        self.batch['groups'][0]['status']='awaiting_confirmation';self.save()
        with self.assertRaisesRegex(ValueError,'尚未完成'):export(self.bp,self.out,['g01'])
        self.assertFalse(self.out.exists())
    def test_stale_composition_rejected(self):
        p=self.base/self.batch['groups'][0]['compositionPath'];p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'重新打包'):export(self.bp,self.out)
    def test_embedded_registration_mismatch_rejected(self):
        p=self.base/'preview/index.html';s=p.read_text();s=s.replace('"duration":1.1','"duration":2.1',1);self.assertNotEqual(s,p.read_text());p.write_text(s)
        with self.assertRaisesRegex(ValueError,'注册数据'):export(self.bp,self.out)
    def test_no_overwrite_and_corruption_detected(self):
        export(self.bp,self.out)
        with self.assertRaisesRegex(ValueError,'已存在'):export(self.bp,self.out)
        damaged=self.root/'damaged.zip'
        with zipfile.ZipFile(self.out) as src,zipfile.ZipFile(damaged,'w') as dst:
            for n in src.namelist():dst.writestr(n,b'changed' if n=='courses/g01/lesson-player.js' else src.read(n))
        with self.assertRaisesRegex(ValueError,'不完整'):check(damaged)
    def test_path_escape_rejected(self):
        outside=self.root/'outside.json';outside.write_text('{}')
        self.batch['groups'][0]['scriptPath']='../outside.json';self.save()
        with self.assertRaisesRegex(ValueError,'超出目录'):export(self.bp,self.out)

if __name__=='__main__':unittest.main()
