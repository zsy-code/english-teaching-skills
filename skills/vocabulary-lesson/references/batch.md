# 批次、子 agent 与用户确认

## 分工

主会话负责输入副本、任务分配、状态与用户回复；多组时使用当前环境提供的子 agent 工具，按实际可用容量启动，其余排队。工具不可用时说明本轮串行处理，不能把虚构的角色写成已启动的 agent。

对子 agent 提供：本 skill、当前阶段所需参考、共同要求、本组完整输入、实际可读的参考材料、唯一组目录和已有版本。接续脚本时一并提供批次状态文件和对应批准记录。说明它是组内执行者，不再启动子 agent；它只写本组材料，返回材料路径和待澄清问题，不改批次状态，不替用户批准，也不在子会话私下等待用户。缺少关键资料时先返回问题。

主会话及时汇总各组状态和待确认内容，不必等全批完成才能展示先完成的方案。一组等待用户不阻塞其他组。用户询问状态时报告实际工具状态和已保存材料，不编造进度百分比、完成时间或模型名称。

## 保存材料

- input.json：本批输入副本和整理后的任务信息。
- groups/g01/plan-v1.md：每组方案；修改新增版本，保留旧版。
- groups/g01/script-v1.json：联合课程脚本的唯一内容来源；同名 .md 由工具生成用于阅读，不另行手改。记录 scriptVersion、scriptPath、scriptViewPath 和 scriptPlanVersion，明确脚本对应哪个方案。
- batch.json：主会话维护的轻量记录，包含 batchId、skillVersion，以及每组的 localId、sourceGroupId、title、words、status、planVersion、planPath、agentId、pendingQuestions、approval。路径相对批次目录。

status 使用 queued、planning、awaiting_input、awaiting_confirmation、approved、scripting、script_ready、voicing、audio_ready、animating、preview_ready、delivered、paused、failed。新记录的版本号用正整数；读取旧记录时兼容 v1 这样的写法。approval 默认 null；确认时保存用户的明确回复、对应方案版本和时间。pendingQuestions 中每项带本组稳定的问题编号、问题内容和是否阻塞当前阶段。不要保存密钥。

状态记录表示本次工作已知事实，不是 Web 同步接口。主会话展示的表格至少有：组别、状态、方案版本与链接、需要用户处理的事项。

## 接收用户回复

用户可以按组回复，也可以批量确认已展示且无歧义的方案。不能对尚未展示的方案作批量推断；“确认”指向不明时只澄清指向。

修改意见传回对应 agent；不可恢复时，新的执行者先读取该组输入和版本材料。教学范围或方案修改后新增版本、清空该组旧批准，并提交用户确认；旧批准可留在历史记录中，不能移用。未受影响的组保留状态。

只润色措辞、细分镜头、调整布局和动作实现，且保留已确认的教学内容、核心场景、主要推进顺序与互动安排时，在新脚本版本中修改，保留方案批准。改变上述内容须先修订方案并重新确认，不能借脚本细化自动授权。方案变化后旧脚本保留为历史材料，不能仍当作最新可用脚本；当前脚本字段清空或移入 scriptHistory。失败、暂停或未通过核对时不能记录 script_ready。

暂停某组时尝试用实际工具停止其工作，核实后记录 paused；无法中断就说明仍在执行，不宣称已暂停。恢复时从已有材料继续。当前轮中已提出的问题应保持可见，用户可以一次回复多个组；等待人类回复时结束当前轮，不占用工具反复轮询。

已确认组的流程中，已确认组进入 scripting，脚本完成并核对后标为 script_ready，随后 voicing，配音文件与时间核对完成后标为 audio_ready；未确认组继续等待。记录 audioVersion、audioPath、timingPath、audioScriptSha256 和 listeningStatus（pending 或 reviewed，附实际试听范围）。配音失败或暂停保留目录及完成条数；确认重试时从该目录接续。脚本变更后旧音频移入历史，不能仍标为当前可用。audio_ready 后进入 animating；画面、声音和互动接通并完成实际播放检查，才标 preview_ready，并保存 compositionPath、previewPath、verificationPath。preview_ready 表示可供观看，不代替用户的验收。有任务连接时按 services.md 上报进度；尚未实现后台常驻、跨会话锁或 Web 回复路由。

成品交付见 [本地成品交付](delivery.md)。delivered 仅表示本地 ZIP 已生成并独立验证，不代表上传成功或用户验收；delivery 记录与 previewAcceptance 分开。已交付后修改脚本、音轨或画面时，保留旧交付历史，重回相应制作状态，完成后导出新版本。
