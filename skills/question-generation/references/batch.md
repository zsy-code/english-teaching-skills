# 批次与确认记录

主会话维护 input.json、papers/<档位>-vN.json 和 batch.json。试卷确认前按档位组织；回传试卷后，用返回的 questionItems 建立工作目录：选择、填空每题一组；阅读同篇小题合为一组，保留全部来源编号与摘要。阅读使用整篇项的 sourceItemId/sourceHash，保留 questionIds。

每题记录 localId、sourceItemId、sourceHash、title、status、planVersion、planPath、scriptVersion、scriptPath、scriptViewPath、scriptPlanVersion、approval、paperApproval、scriptApproval。路径相对批次目录。approval 包含 planVersion、planSha256、userReply、confirmedAt；scriptApproval 包含 scriptVersion、planVersion、scriptSha256、userReply、confirmedAt；paperApproval 保留试卷版本、摘要、用户回复和时间。

pendingStage=plan/paper/script 分别对应三次确认。只认可用户对已展示当前版本的明确确认；支持逐档或批量确认。改变试题答案后更新纸卷版本、受影响脚本和确认记录，不能沿用旧题的视频关联。

用户要求并行或环境允许且已授权时，可按档位或题目分给子 agent。子 agent 返回文件与问题给主会话，不替用户批准；主会话集中呈现已完成材料和待确认事项。状态 running 不证明有进展，报告实际保存文件与工具结果。

脚本通过 script_tool.py 检查并确认后进入 voicing。audio_ready 记录 audioVersion、audioPath、timingPath、audioScriptSha256、listeningStatus；动画接入后记 compositionPath、previewPath、verificationPath。实际播放检查后为 preview_ready，导出并独立验证后为 delivered；是否上传成功另看回执。
