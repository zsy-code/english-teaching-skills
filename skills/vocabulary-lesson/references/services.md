# 所需服务与任务连接

教学 skill 不携带厂商密钥，也不依赖某个 Web 项目的代码路径。运行时按任务提供的接口或当前环境的工具取得所需材料。

## 接收与检查

任务含 `services` 时，单独保存为 `connection.local.json`，设置仅本人可读（POSIX: chmod 600），放在交付目录之外并排除版本管理。教学输入副本移除整个 services；batch、报告和课程包不保存 key。任务 key 仅授权本批次的配音和进度，不是厂商密钥。无 services 时跳过系统同步，不追问上传配置。

连接格式：`{protocolVersion:1, baseUrl, key, expiresAt}`。baseUrl 为本次任务的 API 根地址，key 从 Web 交接材料取得，不通过命令行参数传递。HTTP 只接受本机地址，远程连接需要 HTTPS；不携带授权跟随重定向。

```sh
node <skill>/scripts/service-client.mjs capabilities --connection <private>/connection.local.json
```

按 `services.tts.available`、`services.image.available` 等能力检查当前阶段的需要。TTS 在进入配音前必须可用；缺配音不阻止编写方案。只有选定画面需要图像合成时才检查图像服务，代码绘制的图解不需要图像接口。

- 已提供且可用：优先使用任务接口，配音音色和语速由后端管理。
- 没有提供或明确未配置：检查当前 agent 已有的工具、用户指定的本地合成器或可信服务模块。可用且在用户授权范围内时使用，并说明采用了什么；缺少时提示补充服务或选择替代方式，保留已有材料。
- 已提供但调用失败：区分授权失效、忙碌和生成错误，报告原因。可重试错误保留编号重试；不要悄悄换服务、换音色。无法恢复时再向用户提供替代选项。

不为填补能力自行注册服务、安装来源不明的程序或把付费请求发给未经用户选择的服务。静音、占位图和未生成的文件不能算成功；用户明确选择无配音时才允许标注为无配音版本。

## 配音

```sh
node <skill>/scripts/synthesize.mjs --request <group>/audio-vN/audio-request.json --connection <private>/connection.local.json --group <任务中的原始组id>
```

脚本 POST `baseUrl/tts`，头部 `Authorization: Bearer <key>`，JSON 为 `{requestId,groupId,text,lang}`。lang 是 zh/en，text 是实际送去朗读的 spokenText，最多 3000 字符。成功响应为 WAV，不是音频地址。请求编号由台词、语言、组和音色版本计算，同编号重试复用结果；后端音色或语速改变后需要明确加 `--revision <新编号>`，整组重生成，避免新旧声音混用。重复下载不会重复合成。

可选本地方式：`--provider-module <可信模块绝对路径>` 替代 `--connection/--group`。模块导出 `async synthesize(text,lang,signal)` 返回 `{file}`，提供单声道 16 位 PCM WAV。没有兼容模块时可用环境已有工具逐句生产相同规格的 WAV，再按 audio 工具要求登记 manifest；不能声称此脚本兼容所有合成工具。

错误：401 重新取得授权；403 核对原始组 id；409 同编号仍在合成则稍后重试、内容冲突则核对请求、进度序号冲突则重读；429 等待后重试；503 补充服务；502 检查服务后重试。每次最多自动重试 3 次，之后报告并保留材料，不无限等待。脚本会保留 HTTP 状态，不输出第三方错误正文或 key。

## 可选进度同步

仅当提供连接且 capabilities 声明 sync 可用时同步。主会话给各执行者分配原始 groupId；各组独立递增 sequence。重启时先读取 progress，不从 1 猜起。

```sh
node <skill>/scripts/service-client.mjs progress --connection <private>/connection.local.json
node <skill>/scripts/service-client.mjs event --connection <private>/connection.local.json --data <private>/event.json
```

event.json：`{eventId,groupId,sequence,state,message,counts?}`。每个新事件使用唯一 eventId，sequence 为该组上次值加 1，counts 为 `{done,total}`。同事件重试必须保持全部字段一致。已上报事件重试安全，失败时本地保留待发事件；同步失败不要求重做已经完成的课程材料。

阶段变化、等待用户回复、失败、恢复和完成时上报；长配音每完成一批（例如 5 条）更新数量。message 只写事实和所需回复的摘要，不传密钥、内部提示词或用户无关资料。

| state | 含义 |
| --- | --- |
| planning / awaiting_input / awaiting_confirmation | 编写方案 / 待补充 / 待确认 |
| scripting / voicing / animating | 设计脚本 / 配音 / 制作动画 |
| preview_ready / delivered | 已有预览 / 已本地交付 |
| paused / failed | 用户暂停 / 执行失败 |

同步只是记录，不代表用户批准方案，也不会控制或唤醒 agent。Web 的撤销 key 只停止后续服务访问；本地制作仍需用户在 agent 中暂停。用户确认仍在执行会话中完成。

本版只实现 TTS 和进度客户端，图像合成、成品上传是预留能力，课程包本地交付。不要因附件声称支持某个尚无适配器的服务而假装已经上传。
