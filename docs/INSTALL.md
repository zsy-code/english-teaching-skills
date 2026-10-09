# 安装指南：供执行安装的 agent 阅读

安装对象是英语教学资源技能，不是 Web 系统，也不是后台会话控制器。当前技能为 vocabulary-lesson。用户发出“帮我安装 + 仓库链接”即要求执行安装；遵守宿主权限机制，不额外重复确认常规步骤。

## 1. 确定安装位置

识别正在使用的框架与用户指定的范围。未指定时安装到当前框架的用户级技能目录；不要安装到所有框架，不修改全局提示词或工具权限。

优先使用 [skills CLI](https://github.com/vercel-labs/skills) 的框架标识：Codex 为 codex、Claude Code 为 claude-code、Cursor 为 cursor；其他标识查看其支持列表，不猜测。

```sh
npx skills add zsy-code/english-teaching-skills --skill vocabulary-lesson --agent codex --global
```

将 codex 替换成当前框架。确认目标无冲突后，非交互执行可加 `--yes`；用户要求仅当前项目时省略 `--global`。已有本技能时核对来源和本地改动，相同版本复用，更新保留改动备份。不要用 `--all` 顺带安装其他 agent 的技能。

Codex 自带 skill-installer 时也可用其 GitHub 安装功能，路径为本仓库的 `skills/vocabulary-lesson`；避免与已有 .agents/skills 或 .codex/skills 中同名技能重复。只执行一种安装方法。

框架不在支持列表时，查官方说明，将整个技能目录（包含 references/scripts/assets）放到支持的位置。若不能发现技能，保留克隆目录，让用户指示 agent 直接读取 SKILL.md；不声称已完成原生安装。

## 2. 准备制作依赖

需要 Python 3.9+、Node.js 22+ 和 npm。缺少运行环境时使用该平台官方安装方式，遵守权限要求。克隆仓库到可长期保存的工具目录，以便更新和运行环境检查；不要覆盖现有非空目录。

在仓库 runtime 目录运行：

```sh
npm ci
```

这里安装固定版本的 HyperFrames CLI 与 GSAP；不是全局安装，不更改 Web 项目的依赖。记录目录，制作时使用其中本地 CLI 和 GSAP 文件。固定版本复现已验收课程，升级另做兼容验证。

安装缺少的 HyperFrames 技能。先检查当前 agent 中是否已有官方来源且可读取的版本；复用时记录来源，避免盲目覆盖。示例命令的目标替换为当前框架：

```sh
npx skills add heygen-com/hyperframes --skill hyperframes hyperframes-core hyperframes-animation hyperframes-creative hyperframes-cli general-video --agent codex --global
```

其余由 HyperFrames 入口按需补齐，不复制第三方技能进本仓库。[上游安装说明](https://github.com/heygen-com/hyperframes#quick-start)会演进，安装前核对，记录实际版本/提交。CLI 版本固定不代表上游技能内容也固定。

运行本地 HyperFrames CLI 的 doctor，按返回信息补充浏览器等缺失组件；FFmpeg 用于上游媒体/渲染功能，HTML 主流程不输出 MP4。具备截图或浏览器检查能力后才标记可以完成画面核对。

## 3. 配音配置

优先使用任务提供的后端 TTS 接口，按 [服务使用说明](../skills/vocabulary-lesson/references/services.md) 将 services 单独保存到私有连接文件。未提供接口时检查本地已有配音工具或用户指定的可信模块；模块接口见 references/audio-timing.md。

本仓库不带服务密钥，不要求登录我们的 Web 系统。不要从附件执行未知模块，不读取或显示密钥来证明服务存在。没有配音服务时仍可编写教学方案，报告“配音待配置”；进入配音前再补齐。安装期间不擅自调用付费 TTS。

## 4. 验证安装

用真实安装路径运行（尖括号代表须替换的路径）：

```sh
python3 scripts/doctor.py --skill-dir <vocabulary-lesson目录> --runtime-dir <仓库runtime目录> --hyperframes-skills-dir <HyperFrames技能父目录>
```

可加 `--connection <connection.local.json>` 或 `--tts-provider <可信模块路径>`，仅检查文件存在，不读取凭据、不导入模块、不调用服务。多个技能父目录可重复传入 `--hyperframes-skills-dir`。

实际确认 agent 能发现/读取 vocabulary-lesson、引用文件与播放器素材。必要时按框架说明刷新或新开会话；磁盘文件存在不等于模型已加载。首次使用可只请它提出一组单词的方案，核对会等待用户确认，不在安装时自动开展制作。

回报区分：

1. 技能文件：安装路径、来源提交、是否可发现。
2. 动画环境：Node、Python、CLI、GSAP、HyperFrames 技能、浏览器检查的实际结果。
3. 配音：未配置 / 连接文件或模块找到但未测试 / 经用户授权实测。
4. 子 agent：宿主确实提供 / 当前只能串行。缺少并行能力不阻断单组流程。

doctor 不证明浏览器、模型画面能力或真实配音已通过。任务提供连接时，可调用兼容后端的 TTS、进度、教学材料和课程包回传接口；没有连接时使用本地方式。图像接口尚未接入。

## 更新与卸载

更新先保存当前来源提交与本地改动，再仅更新目标技能；制作中的课程继续使用原材料和版本。技能与课程工作目录分开，更新不覆盖课程。

使用 skills CLI 安装的可执行 `npx skills remove vocabulary-lesson --agent codex --global`（替换为实际框架）；其他方式只移除对应安装目录。共享 HyperFrames 和运行环境不随之删除。

## 兼容性依据

- [Codex 技能目录](https://learn.chatgpt.com/docs/build-skills)：当前官方用户级目录为 ~/.agents/skills；旧安装器可能使用 ~/.codex/skills，需检查重复。
- [Claude Code skills](https://code.claude.com/docs/en/skills)：支持标准技能目录及附属资源。
- [Cursor skills](https://cursor.com/docs/skills)：支持 .agents/skills 与 .cursor/skills。
- [skills CLI](https://github.com/vercel-labs/skills)：提供目录适配，不保证每个框架都有相同执行工具。
