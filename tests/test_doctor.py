import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('doctor', ROOT/'scripts/doctor.py')
doctor=importlib.util.module_from_spec(spec);spec.loader.exec_module(doctor)

class DoctorTests(unittest.TestCase):
    def test_missing_runtime_is_not_reported_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=doctor.inspect(ROOT/'skills/vocabulary-lesson',Path(tmp),[])
            self.assertFalse(result['filesAndRuntimeOk'])
            self.assertTrue(next(c for c in result['checks'] if c['name']=='skill-files')['ok'])
            self.assertEqual(result['tts'],'not_configured')
            self.assertEqual(result['browser'],'not_tested')

    def test_provider_is_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); provider=root/'provider.mjs'
            provider.write_text('throw new Error("do not run during installation")')
            result=doctor.inspect(ROOT/'skills/vocabulary-lesson',root,[],provider)
            self.assertEqual(result['tts'],'module_found_not_tested')

if __name__=='__main__':unittest.main()
