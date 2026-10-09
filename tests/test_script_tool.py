# -*- coding: utf-8 -*-
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TOOL=Path(__file__).resolve().parents[1]/'skills/vocabulary-lesson/scripts/script_tool.py'
spec=importlib.util.spec_from_file_location('script_tool',TOOL)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


class ScriptChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.group=self.root/'groups/g01'; self.group.mkdir(parents=True)
        self.plan=self.group/'plan-v1.md'; self.plan.write_text('已确认的教学方案')
        self.batch=self.root/'batch.json'; self.path=self.group/'script-v1.json'
        self.record={'groups':[{'localId':'g01','planPath':'groups/g01/plan-v1.md','planVersion':'v1','status':'approved','approval':{'planVersion':'v1'}}]}
        self.save_batch()
        self.script={'schemaVersion':'0.2','groupId':'g01','version':1,'planVersion':1,
          'planSha256':hashlib.sha256(self.plan.read_bytes()).hexdigest(),'title':'例课','videoSize':{'width':1920,'height':1200},'visualDirection':'用同一情境展示变化。',
          'beats':[{'id':'b01','purpose':'理解变化','speech':[{'id':'s01','lang':'zh','text':'看看变化。'},{'id':'s02','lang':'en','text':'Look.'}],
          'visual':{'layout':'文字靠近对象。','initialState':'对象未变化。','cues':[{'speechId':'s01','at':'start','action':'对象由展开变为合起。'}],'handoff':'保留对象，进入选择题。'},
          'interaction':{'type':'choice','prompt':'哪个符合变化？','options':[{'id':'a','text':'合起'},{'id':'b','text':'展开'}],'answerId':'a','feedback':{'correct':'对，刚刚合起。','incorrect':'请看两边合拢，答案是合起。'}}}],
          'coverage':[{'point':'解释变化','speechIds':['s01']}],'reservedReadAlong':[{'afterBeatId':'b01','text':'Look.'}]}

    def save_batch(self):self.batch.write_text(json.dumps(self.record))
    def check(self):return mod.validate(self.script,self.batch,'g01',self.path)
    def test_valid_legacy_approval_and_render(self):
        self.check(); view=mod.render(self.script)
        self.assertIn('看看变化。',view); self.assertIn('Look.',view)
        self.assertLess(view.index('作答后才显示'),view.index('对，刚刚合起。'))
        self.assertIn('不启用等待或录音',view)
    def test_unconfirmed_group_does_not_borrow_approval(self):
        self.record['groups'].append({'localId':'g02','status':'approved','approval':{'planVersion':1}})
        self.record['groups'][0]['approval']=None; self.record['groups'][0]['status']='awaiting_confirmation'; self.save_batch()
        with self.assertRaisesRegex(ValueError,'尚未批准'):self.check()
    def test_updated_plan_version_blocks_old_approval(self):
        self.record['groups'][0]['planVersion']=2;self.save_batch()
        with self.assertRaisesRegex(ValueError,'版本'):self.check()
    def test_changed_plan_content_blocks_stale_script(self):
        self.plan.write_text('已修改的方案')
        with self.assertRaisesRegex(ValueError,'摘要'):self.check()
    def test_paused_group_cannot_finalize_script(self):
        self.record['groups'][0]['status']='paused';self.save_batch()
        with self.assertRaisesRegex(ValueError,'暂停'):self.check()
    def test_wrong_group_output_directory_rejected(self):
        with self.assertRaisesRegex(ValueError,'所在目录'):mod.validate(self.script,self.batch,'g01',self.root/'other/script.json')
    def test_broken_cue_and_coverage_references(self):
        self.script['beats'][0]['visual']['cues'][0]['speechId']='missing'
        with self.assertRaisesRegex(ValueError,'当前片段'):self.check()
        self.script['beats'][0]['visual']['cues']=[];self.script['coverage'][0]['speechIds']=['missing']
        with self.assertRaisesRegex(ValueError,'不存在的台词'):self.check()
    def test_duplicate_speech_ids_rejected(self):
        self.script['beats'][0]['speech'][1]['id']='s01'
        with self.assertRaisesRegex(ValueError,'台词编号重复'):self.check()
    def test_answer_requires_existing_option(self):
        self.script['beats'][0]['interaction']['answerId']='c'
        with self.assertRaisesRegex(ValueError,'答案'):self.check()
    def test_read_along_not_active_interaction(self):
        self.script['beats'][0]['interaction']['type']='read_along'
        with self.assertRaisesRegex(ValueError,'预留'):self.check()
    def test_no_fake_timestamps(self):
        self.script['beats'][0]['duration']=5
        with self.assertRaisesRegex(ValueError,'未约定'):self.check()
    def test_invalid_canvas_rejected(self):
        self.script['videoSize']['width']=True
        with self.assertRaisesRegex(ValueError,'正整数'):self.check()


if __name__=='__main__':unittest.main()
