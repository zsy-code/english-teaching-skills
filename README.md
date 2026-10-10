# 英语教学资源 Skills

让 AI agent 从词汇和教学想法出发，制作带配音、动画和互动练习的 HTML 课程。

## 给 agent 一句话即可开始安装

> 帮我安装英语教学资源 Skills：https://github.com/zsy-code/english-teaching-skills

**收到上述请求的 agent：请先阅读 [安装指南](docs/INSTALL.md)，识别当前框架，安装技能和所需依赖，再报告实际可用的能力。安装不会启动课程制作。**

也可使用标准技能安装工具（以 Codex 为例）：

```sh
npx skills add zsy-code/english-teaching-skills --skill vocabulary-lesson --agent codex --global
```

Claude Code 使用 `--agent claude-code`，Cursor 使用 `--agent cursor`。其他框架由安装 agent 按指南适配。以上命令只安装本仓库技能文件；动画依赖和配音配置另见安装指南。

课程制作有两个确认点：先确认教学方案，再确认完整逐句脚本（含画面与互动设计）。第二次确认后才开始配音、素材与动画制作，连续执行到成品交付。

## 当前技能

| 技能 | 能做什么 | 状态 |
| --- | --- | --- |
| [vocabulary-lesson](skills/vocabulary-lesson/SKILL.md) | 从一组或多组词汇制作互动 HTML 教学课程 | 已实现方案、制作、ZIP 交付与可选 Web 同步 |

长难句、语法、课文等技能后续加入同一仓库，目前不提供空占位技能。

## 安装后怎么使用

直接告诉 agent：

> 使用词汇教学技能，为初一学生讲解 see、look、watch。我希望通过同一段校园故事让学生理解区别。先给我教学目标和讲解方案。

也支持附上 Web 系统导出的任务文件。用户只提供需求；教学流程由 skill 维护。

```text
读取词汇与要求 → 教学目标、整课走向、主要场景和基础台词 → 用户确认
→ 沿已确认方案细化逐句台词、动画、素材与互动 → 配音
→ HyperFrames 动画 → 固定播放器 → 验证并交付 ZIP
```

默认中文讲解、英文朗读、白底双色图解、1920 × 1200。当前固定播放器仅支持 1920 × 1200；其他尺寸可在方案中保留，但制作前需要适配播放器。方案阶段不估算时长。页面根据内容设计，字幕与播放控件复用固定组件。

## 适用范围

- 采用标准 SKILL.md，面向支持文件读写、命令执行的 agent。没有技能发现功能的框架可直接读取文件，但不称为已原生安装。
- 单组可串行制作；多组在宿主具备子 agent 工具时并行，不绑定某个模型或工具名称。
- 当前完整教学试跑在 Codex 中完成。安装目录兼容不等于已在所有框架验证相同制作质量。
- HyperFrames、浏览器和可信配音模块是制作依赖。缺少时明确报告，不能把无声文件当作配音成功。
- 当前交付本地 HTML 课程包。支持任务接口提供的 TTS、进度、教学材料同步和课程包上传，复用同一任务 key。静态插画优先使用 agent 框架内的图片生成能力，可与 SVG/HTML 动画组合；框架不支持时才使用已配置且有接口说明的图像服务，配套后端图像端点尚未实现。没有连接时不追问上传配置。

## 仓库结构

```text
skills/vocabulary-lesson/  教学流程、工具、固定播放器
docs/INSTALL.md           给安装 agent 的完整步骤
scripts/doctor.py          本地环境检查，不读取密钥、不调用付费服务
runtime/package.json      已验证的动画工具版本
tests/                    不依赖历史课程的自动检查
```

本仓库不包含课程成品、本机服务配置、密钥或第三方技能副本。第三方依赖从其官方来源安装并遵循各自许可。

运行自动检查：`python3 -m unittest discover -s tests -v`，需要 Python 3.9+ 和 Node.js 22+。

安装方式参考：[跨框架 skills CLI](https://github.com/vercel-labs/skills)、[HyperFrames](https://github.com/heygen-com/hyperframes)。
