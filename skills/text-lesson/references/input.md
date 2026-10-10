# 任务输入

接受自然语言或任务附件。当前专项为 text，一条 items 对应一门课程。读取 id、title、content、translation、context、scope、userNotes、source、sourceHash，以及公共 audience、userNotes、videoSize、references。不增删或改写原文；辅助例句与原文分开。只询问影响当前方案的缺失内容。

services 单独存为目录外的 connection.local.json（chmod 600），input.json 移除 services 和 skillFiles。不要将 key 写入材料、报告或成品。按 services.md 读取能力和参考附件；没有连接跳过同步。

batch.json 使用 batchId（保留原值）、skillVersion: "text-lesson@1.1"、lessonType: "text"、groups。groups 是生产工具的内部课程列表，不是词汇分组；每条 localId 使用 g01 等安全编号，sourceItemId 为原始 item.id，sourceHash 原样保留，title 为课程标题，其他状态字段按 batch.md。接口 groupId 传 sourceItemId，脚本 groupId 传 localId，不需要伪造 words。

本地自然语言任务没有 sourceHash 时，对原始条目的 UTF-8 JSON 计算 SHA-256 并记录；平台输入必须原样沿用 sourceHash，不自行重算。尺寸默认 1920 × 1200。

每题为单选、提交后答对或答错反馈，不支持逐空作答或录音评分。不要因为有互动组件就机械增加练习。
