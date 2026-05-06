# Wiki Resolver

新建或更新页面前，先按以下顺序决策：

1. 查 `scripts/canonical_map.json`
2. slug 命中则更新原页
3. source path 命中则更新 source 页
4. alias 单命中则更新原页
5. title 多命中则按 kind 和任务意图消歧
6. 仍无法确认则写入 `QUESTIONS.md`

## Kind 决策

- `source`：单一原始文档的摘要页
- `concept`：流程、机制、模式、方法、技术概念
- `entity`：系统、服务、脚本、文件、配置、工具、人物、组织
- `synthesis`：跨多个来源或多个概念的综合判断

## 禁止

- 不因标题相同合并 source 和 concept
- 不在无法消歧时任选一个页面
- 不把来源文档当领域实体
