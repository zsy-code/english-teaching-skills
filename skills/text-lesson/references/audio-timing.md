# 配音与实测时间

输入是当前组已确认方案、已获用户确认的逐句联合脚本和批次记录。本阶段生成真实音频与时间表，供下一阶段动画使用。使用用户选定的现有配音服务；厂商配置由后端或可信本地模块读取；任务接口使用独立连接文件，不将凭据写入教学材料、日志或交付包。

## 执行

本工具使用 Python 3.9+ 和 Node.js 22+。先按 [所需服务与任务连接](services.md) 检查并选择服务。默认调用任务提供的后端 TTS；未提供时可使用已配置的可信本地服务。不得依赖某个 Web 项目的固定路径。输出须为单声道 16 位 PCM WAV。

先读取脚本中的实际台词。中文中的英文词、词缀和字母拼读要作为试听重点；发现发音问题时保留原稿，记录具体台词，再调整对应朗读输入并重生成，不静默改变教学内容。纯英文条目使用英文语言参数，混合讲解沿用所配置的中英兼容音色。

显示文字与朗读输入分开保存。正文和字幕保持原拼写；遇到需要拼读的词缀、缩写或符号，在本组 `pronunciation.json` 中记录 `replacements`，每项为 `match` 与 `spoken`。逐项根据本课语境决定读法，不使用全局词缀替换表，不把整词拆成字母。prepare 加 `--pronunciation <文件>` 会生成单独的 spokenText；TTS 读取 spokenText，字幕继续读取 text。替换后按新音频实测时长重新组装，不沿用旧时间表。规则须经本课材料核对，读音替换不能改变讲解含义。

1. 运行 `audio_tool.py prepare`，核对方案批准、当前脚本批准及文件摘要和脚本结构，写 `audio-request.json`。
2. 运行 `synthesize.mjs`，逐句调用已有服务，写音频与 `audio-manifest.json`。实时报告已完成条数。失败或暂停保留已有材料，不用静音或估计时长冒充配音成功；重试使用同一请求，任务请求编号复用已完成音频；改变音色时按 services.md 更新 revision。变更脚本使用新音频版本目录。
3. 运行 `audio_tool.py assemble`，读取 WAV 的真实采样数，生成 `narration.wav` 和 `timing.json`。画面 start/end 锚点解析为对应台词的真实开始/结束时间；不按字数均分时间。

```sh
python3 <skill>/scripts/audio_tool.py prepare --script <group>/script-vN.json --batch <batch>/batch.json --group <id> --out <group>/audio-vN
node <skill>/scripts/synthesize.mjs --request <group>/audio-vN/audio-request.json --connection <private>/connection.local.json --group <任务中的原始组id>
python3 <skill>/scripts/audio_tool.py assemble --script <group>/script-vN.json --batch <batch>/batch.json --group <id> --out <group>/audio-vN
```

时间表以秒为单位，包括整课实测时长、各片段范围、逐条台词、画面变化与题目暂停点。服务未提供逐字时间时，字幕沿用整条台词的真实音频窗口，不声称逐字对齐；需要更细同步时补充对齐数据后再进入动画。

默认句间附加短停顿：中文 150ms、英文 250ms、片段交接 350ms；片段交接替代句间停顿，不叠加。末句默认不追加静音。通过 `--pauses <json>` 调整，字段为 zhMs、enMs、beatMs 及 afterSpeechMs（台词编号到毫秒），不改变音频语速。仅为真实观察需要增加停留，不给每句话都加长间隔；试听时同时考虑服务自身已有的停顿。

题目登记在对应片段末尾，学生作答耗时不计入固定音轨。题干中已写入 speech 的引导正常朗读；作答反馈不混入主音轨，跟读入口仍仅预留。音频试听页须在题目处暂停，不能把整段音频连播误当成包含答题的课程。

## 交付与核对

核对源脚本未变化、每条台词均有对应音频、音频完整且采样率一致、合并长度与时间表一致、画面锚点正确、主音轨未包含题目答案。试听开场、英文单词与例句、混合语言和词缀解释、片段交接；明确记录实际听过的部分。若没有可靠听音能力，交付试听材料并标注待人工试听，不把文件校验写成发音合格。

主会话保存音频目录、脚本摘要、时间表与检查结果；完成文件和时间核对后记为 audio_ready，单独记录 listeningStatus。audio_ready 仅表示配音材料可用，不表示教学动画或最终课程通过验收。完成后继续 [动画制作与播放器](animation.md)。生产流程成熟后可连续执行，本次分阶段开发不新增永久审批关卡。
