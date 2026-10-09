"""Read-only installation inventory; never imports a TTS module or calls a service."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CORE = ['hyperframes', 'hyperframes-core', 'hyperframes-animation',
        'hyperframes-creative', 'hyperframes-cli', 'general-video']


def inspect(skill, runtime, roots, provider=None):
    checks = []
    def add(name, ok, detail):
        checks.append(dict(name=name, ok=bool(ok), detail=detail))
    add('python', sys.version_info >= (3, 9), sys.version.split()[0])
    node = shutil.which('node')
    version = ''
    if node:
        try:
            version = subprocess.check_output([node, '--version'], timeout=10, text=True).strip()
        except (OSError, subprocess.SubprocessError):
            pass
    m = re.match(r'v(\d+)\.', version)
    add('node', m and int(m[1]) >= 22, version or '未找到可运行的 Node.js')
    add('npm', shutil.which('npm') is not None, '运行环境的包管理器')
    files = ['SKILL.md', 'references/input.md', 'references/teaching-plan.md',
             'references/batch.md', 'references/course-script.md', 'references/audio-timing.md',
             'references/animation.md', 'references/delivery.md', 'scripts/script_tool.py',
             'scripts/audio_tool.py', 'scripts/synthesize.mjs', 'scripts/package_course.mjs',
             'scripts/deliver_course.py', 'scripts/preview_server.py',
             'assets/lesson-player/contract.js', 'assets/lesson-player/runtime.js',
             'assets/lesson-player/shell.html', 'assets/lesson-player/player.css']
    missing = [f for f in files if not (skill / f).is_file()]
    add('skill-files', not missing, missing or str(skill))
    for name, expected in [('hyperframes', '0.8.141'), ('gsap', '3.14.2')]:
        try:
            actual = json.loads((runtime / 'node_modules' / name / 'package.json').read_text())['version']
        except (OSError, ValueError, KeyError):
            actual = '未安装'
        add(name, actual == expected, dict(installed=actual, tested=expected))
    add('hyperframes-cli-file', (runtime / 'node_modules/hyperframes/bin/hyperframes.mjs').is_file(),
        '仅检查 CLI 文件；请另运行 CLI doctor 验证浏览器等依赖')
    for name in CORE:
        found = next((r / name / 'SKILL.md' for r in roots if (r / name / 'SKILL.md').is_file()), None)
        add('skill:' + name, found is not None, str(found) if found else '缺少或未提供正确的技能父目录')
    return dict(filesAndRuntimeOk=all(c['ok'] for c in checks), checks=checks,
                tts='module_found_not_tested' if provider and provider.is_file() else 'not_configured',
                browser='not_tested', agentSkillDiscovery='not_tested', subagents='host_dependent',
                note='这不是完整课程制作验收；不读取密钥、不调用配音、不安装软件。')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skill-dir', type=Path, required=True)
    p.add_argument('--runtime-dir', type=Path, required=True)
    p.add_argument('--hyperframes-skills-dir', type=Path, action='append', default=[])
    p.add_argument('--tts-provider', type=Path)
    a = p.parse_args()
    result = inspect(a.skill_dir, a.runtime_dir, a.hyperframes_skills_dir, a.tts_provider)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['filesAndRuntimeOk'] else 1


if __name__ == '__main__':
    sys.exit(main())
