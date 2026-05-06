# Resolver / MECE 归档决策

在 Ingest、Compile 或任何需要新建/更新 wiki 页面的操作前，先用 resolver 决定目标页面。目标是减少重复页、错放目录、source/concept/entity 混用，以及同名页面静默误合并。

## 决策顺序

1. 读取 `scripts/canonical_map.json`。如果缺失，先运行 `scripts/build-canonical-map.py` 或扫描 frontmatter 构建临时 map。
2. 解析候选身份：
   - `slug`
   - source logical path
   - alias
   - title
   - basename
3. 判断页面 kind。
4. 决定 update / create / split / merge / ask。

不要在多候选无法消歧时任选一个页面。写入 `wiki/QUESTIONS.md` 并在回复中说明需要确认。

## Kind 定义

| kind | 放什么 | 不放什么 |
|---|---|---|
| `source` | 单一原始来源文档的摘要页 | 领域实体、长期概念、跨来源综合判断 |
| `concept` | 流程、机制、模式、方法、技术链路、业务规则 | 具体服务、脚本、配置文件、单一来源文档 |
| `entity` | 系统、服务、模块、工具、脚本、配置文件、代码文件、人物、组织、项目 | 流程、机制、模式、综合分析 |
| `synthesis` | 跨多个来源或多个概念的综合判断、对比、架构视图 | 单一来源摘要、单个实体档案 |

特殊页面 `overview`、`log`、`questions`、`templates` 不参与普通归档。

## 新建或更新决策

### Source 页

- 每个 source 页对应一个原始来源文档。
- source logical path 命中已有 source 页时，更新原 source 页。
- source 页记录摘要、关键概念、关键实体、相关链接。
- source 页不进入领域关系图，不写 `part_of`、`depends_on`、`calls`、`implements`、`defines` 等领域关系字段。

### Concept 页

进入 `concepts/` 的内容：
- 流程：部署流程、数据构造流程、排查流程。
- 机制：网关白名单机制、鉴权机制、调度机制。
- 模式：策略模式、语料驱动意图识别。
- 技术链路：DGS 数据同步、NMS 服务接口调用。
- 业务规则：工单字段规则、告警合并规则。

不要把具体服务、脚本、配置文件放入 `concepts/`。

### Entity 页

进入 `entities/` 的内容：
- 系统或产品：OSS-NMS、OSS-Workflow。
- 服务或模块：OSSGateway、OSS-Inspect、OSSAlarm。
- 工具和依赖：Nacos、ScheduleK、OkHttp。
- 脚本和文件：workstation_check.ps1、NMSInterface.json、menuRegister.json、nms_client.py。
- 人物、组织、项目、论文。

不要把流程、机制、模式放入 `entities/`。

### Synthesis 页

进入 `synthesis/` 的触发条件：
- 3 个以上来源共同涉及同一主题。
- 多个 concept/entity 需要合并成一条长期有价值的判断链。
- 查询产生了可复用的跨来源综合答案。
- 需要比较、取舍、架构总览、演化总结。

不要用 synthesis 承载单个来源摘要。

## 冲突处理

| 情况 | 动作 |
|---|---|
| slug 精确命中 | 更新该页 |
| source path 命中 | 更新对应 source 页 |
| alias 单一命中 | 更新该页，并考虑补充 alias |
| title 单一命中且 kind 符合任务意图 | 更新该页 |
| title 多命中但 kind 不同 | 按任务意图消歧：来源追溯选 source；概念解释选 concept；具体对象选 entity |
| title/alias 多命中且无法消歧 | 写入 `QUESTIONS.md`，不要任选 |
| 新事实同时影响多个已有页 | 更新多个已有页，不为每个来源另起重复概念页 |
| 概念过大且内部有稳定子主题 | 保留总页，必要时拆子页并互链 |
| 两页明显重复 | 不立即删除；记录 merge 建议，保留 canonical 页 |

## MECE 反例

- `NMS 部署流程` 是 concept，不是 entity。
- `OSSGateway` 是 entity，不是 concept。
- `NMSInterface.json` 是 entity，不是 concept。
- `DGS 模块深度分析` 是 source，不是 concept。
- `业务拨测` 是 concept；`OSS-Inspect` 是 entity。
- `NMS 微服务架构` 是 concept；`OSS-NMS` 是 entity。
- 同名 source 和 concept 不合并，例如 `sources/nms-deploy` 与 `concepts/nms-deploy` 可以同 title，但必须不同 slug。

## 写入规则

- 新页面必须有 `kind`、`slug`、`title`、`aliases`、`sources`。
- `slug` 必须等于相对 `wiki/` 的路径去掉 `.md`。
- 页面链接优先使用 canonical link：`[[concepts/business-probe|业务拨测]]`。
- 关系字段只写领域页之间的关系，不让 source 页进入领域关系图。
- 如果 resolver 无法确定，优先记录问题，不要制造低置信度结构。
