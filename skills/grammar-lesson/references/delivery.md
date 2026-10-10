# 成品交付与回传

输入是 preview_ready 的课程和当前批次记录。交付一个 ZIP：每组有独立课程入口，批次首页集中列出已交付课程；同时保存当前教学方案、讲解稿、时间表和已内联资源的动画源码。有任务连接时可回传到 Web；没有连接则只交付本地文件。

## 导出

```sh
python3 <skill>/scripts/deliver_course.py export --batch <批次>/batch.json --out <交付目录>/<批次>-v1.zip
python3 <skill>/scripts/deliver_course.py check <交付目录>/<批次>-v1.zip
```

默认只导出 preview_ready 或 delivered 的组；使用重复的 `--group <编号>` 可明确选择。其余组列入清单的 notIncluded，保留原状态；明确选择尚未完成的组时报错，不用空页面冒充成功。现有 ZIP 不覆盖，修订用新文件名。

导出前核对当前批准方案、脚本版本、音轨、章节、字幕、题目位置、动画源码和实际页面注册数据，避免把旧预览当作新产物。只收集指定成品和教学材料，不打包整个工作目录。包内不包含模型/配音服务配置、密钥、历史版本、逐句配音缓存或制作日志。

`delivery.json` 格式为 english-teaching-delivery，version 为 2；包含来源 batchId、制作 skillVersion、exporterVersion、各课程的来源条目与版本、入口、时长、尺寸、互动数，以及文件大小和 SHA-256 清单。Web 使用相同格式接收。Web 任务必须保留原 batchId，并设置 batch.lessonType；每条课程记录 sourceItemId（原始 item.id）与 sourceHash（沿用输入）。文件校验用于发现损坏或版本混用，不是安全签名或教学质量证明。

## 独立验证

将 ZIP 解压到独立目录，运行包内的 preview_server.py，打开首页并进入课程，检查音频定位、画面、题目暂停与继续。需 Python 3.9+ 和现代浏览器；不依赖原 Web 系统、原制作目录或模型服务。不要将双击 HTML 文件作为通过标准。多组应逐组进入并核对入口，不因一组通过就标全批通过。

本包用于播放和查看当前材料。时间表保留原台词编号和拆句音频引用，拆句缓存未随包提供；课程播放使用 courses 里的整轨配音。若后续要重做配音或重新组装时间，需另行提供原始工作材料或再运行配音阶段。

## 记录与展示

独立验证完成后为已导出的组保存 delivery：archivePath（相对批次目录）、archiveSha256、entry、formatVersion 和 checked。状态记为 delivered，仅表示本地文件已交付；上传成功前仍为 false。用户对成片的认可另记 previewAcceptance，并关联准确的脚本和动画摘要，不推断为其他版本或组的验收。没有用户要求的暂停点，不增加新的强制审批。

给用户一个下载入口、一个解压后样例入口，以及必要的使用说明。未完成组继续显示各自问题。保留可接续制作的原目录；将 ZIP 验证通过与平台已接收严格区分。

## 上传到系统

连接存在、upload 能力可用且任务要求平台交付时，在独立验证后执行：

```sh
node <skill>/scripts/service-client.mjs upload --connection <private>/connection.local.json --data <交付目录>/<批次>-v1.zip
```

POST /delivery 使用 application/octet-stream；同一 ZIP 重试不会重复入库。只上传已完成组即可，其他组继续制作。收到 received:true 后，保存 receipt（接收的 course id、version、archiveHash、receivedAt）到本地批次的 platformReceipt，不改变原 ZIP；没有回执不能声称平台收到。

上传失败保留 ZIP、说明原因，提供用户手动回传入口；不重做成片。Web 中选择对应批次的“手动回传 ZIP”使用相同校验。不同批次的包不能混传。用户验收与平台接收分开记录，不能将自检或上传成功当作用户验收。
