# 第二章：Spatial Agent 总体架构设计

## 2.1 Spatial Agent 在 GeoAI 平台中的定位

在传统 GIS 系统中，空间分析流程通常由专业人员手动完成。用户提出需求后，需要 GIS 工程师根据业务目标选择合适的数据、配置分析参数，并调用对应空间算法。例如，在商业选址任务中，用户希望寻找“适合建设大型商业综合体的区域”，GIS 工程师需要自行判断应该使用人口密度分析、道路可达性分析、POI 竞争分析、土地适宜性评价等多个空间模型，并通过权重叠加得到最终结果。

这种模式的问题在于，GIS 能力高度依赖专业经验，普通用户无法直接使用复杂空间分析工具。

Spatial Agent 的核心作用，就是在 GIS 引擎和用户之间增加一个智能决策层，使系统能够理解用户的空间需求，并自动完成从需求解析、分析规划、工具调用到结果解释的全过程。

因此，Spatial Agent 并不是一个简单的聊天机器人，而是一个具备空间推理能力的智能任务调度系统。

整体流程可以表示为：

```
用户空间需求
↓
Spatial Agent
↓
任务理解与分析规划
↓
调用 GIS Tool
↓
空间计算引擎执行
↓
生成结构化空间结果
↓
地图可视化 + 智能报告
```

其中：

- LLM 负责理解自然语言需求和规划任务；
- MCP 或 Function Calling 负责连接外部 GIS 工具；
- Python 空间服务负责执行具体空间计算；
- PostGIS 负责空间数据查询；
- Cesium 负责空间结果展示。

---



# 2.2 为什么需要 Spatial Agent，而不是直接调用 LLM

很多初期 AI + GIS 项目容易设计成：

```
用户输入问题
↓
LLM
↓
生成文字回答
```

这种方式无法解决真正的空间分析问题。

原因在于，LLM 本身并不具备：

- 空间拓扑计算能力；
- 坐标计算能力；
- 路径规划能力；
- 空间数据库查询能力；
- 遥感影像分析能力。

例如用户输入：

> “帮我分析上海浦东新区适合建设新能源充电站的位置。”

LLM 可以理解“新能源充电站”和“浦东新区”，但是无法直接计算：

- 距离主干道路网是否足够近；
- 周边人口覆盖范围；
- 当前充电站密度；
- 土地利用类型；
- 服务半径覆盖情况。

这些必须由 GIS 工具完成。

因此 Spatial Agent 的设计原则是：

> LLM 负责理解和规划，GIS 工具负责计算和验证。

二者职责分离。

对应架构：

```
                 用户
                  |
          Natural Language Input
                  |
                 LLM
                  |
          Task Planning Layer
                  |
        ---------------------
        |                   |
   Spatial Tools       Data Tools
        |                   |
  空间分析算法          数据查询
        |
   PostGIS / GeoPandas
        |
   Analysis Result

```

---



# 2.3 Spatial Agent 核心组成结构

Spatial Agent 主要由五个模块组成：

1. 意图理解模块（Intent Understanding）
2. 空间任务规划模块（Spatial Planning）
3. 工具调用模块（Tool Calling / MCP）
4. 空间结果解释模块（Result Reasoning）
5. 多模态输出模块（Spatial Response）

---



# 2.3.1 意图理解模块（Intent Understanding）



## 能力概述

意图理解模块负责将用户自然语言转换为结构化空间任务。

用户表达通常是非结构化的，例如：

> “帮我看看南京江北新区哪里适合开一家大型超市。”

对于 GIS 系统而言，需要转换成明确参数：

```json
{
  "task": "location_selection",
  "region": "南京江北新区",
  "industry": "大型超市",
  "criteria": ["population_density", "road_accessibility", "competitor_density", "land_use"]
}
```

这个过程类似自然语言理解中的信息抽取。

---



## 技术实现

主要依赖：

- 大语言模型（LLM）
- Prompt Engineering
- Structured Output
- Function Calling

例如定义空间任务 Schema：

```json
{
"name":"location_analysis",
"description":"根据用户需求执行区域选址分析",
"parameters":{"location":"分析区域","business_type":"业务类型","weights":"分析指标权重"}
}
```

LLM 根据用户输入自动生成符合 Schema 的结构化参数。

---



## 实现原理

LLM 并不是直接计算空间结果，而是完成：

自然语言：

```
找适合开咖啡店的位置
```

转换：

```
location_selection
↓
需求条件：人口密度高、道路便利、商业竞争适中、距离地铁近
```

随后进入空间任务规划阶段。

---



# 2.3.2 空间任务规划模块（Spatial Planning）



## 能力概述

空间任务规划模块负责根据用户目标拆解分析步骤。

例如：

用户：

> “分析某区域未来商业价值。”

系统不能直接执行一个算法，因为商业价值不是单一指标，而是多个空间因素综合评价。

Agent 需要拆解为：

```
商业价值分析
↓
人口分析
↓
交通分析
↓
商业竞争分析
↓
土地条件分析
↓
综合评价模型
```

---



## 技术实现

采用 Agent Planning 模式。

常见实现方式：

- ReAct Agent
- LangGraph Workflow
- OpenAI Agents SDK

其中 ReAct 思想：Reasoning + Acting。

即：模型先推理“这个任务需要哪些数据？”然后执行“调用哪些工具？”

---

例如：

用户：

> “分析区域 A 是否适合建设物流中心。”

Agent 推理：

```
物流中心需要：
1. 靠近高速公路
2. 土地面积较大
3. 避免居民密集区
4. 运输路径成本低
```

因此生成任务：

```json
[
{"tool":"road_distance_analysis"},
{"tool":"land_use_analysis"},
{"tool":"population_risk_analysis"},
{"tool":"cost_distance_analysis"}
]
```

---



# 2.3.3 GIS Tool 调用模块（MCP / Function Calling）



## 能力概述

这是 Spatial Agent 与 GIS 引擎连接的核心。

Agent 本身不会执行空间计算，而是调用已经封装好的 GIS 工具。

例如：

Agent：

```
调用 buffer_analysis
```

GIS 服务：

```
执行缓冲区计算，返回 GeoJSON
```

---



## MCP 在系统中的作用

MCP（Model Context Protocol）的作用类似：“统一定义 AI 与外部工具通信协议”。
在本项目中：GIS 能力被封装为 Tool。

例如，Buffer 工具：

```json
{
"name":"buffer_analysis",
"description":"计算空间对象指定距离范围",
"parameters":{"geometry":"目标空间对象", "distance":"缓冲距离"}
}
```

Agent 调用：

```json
{
"tool":"buffer_analysis",
"arguments":{"distance":500}
}
```

后端执行：

```python
buffer_result = geometry.buffer(500)
```

返回：

```json
{
"type":"FeatureCollection",
"features":[...]
}
```

---



# 2.3.4 空间工具体系设计

Spatial Agent 不应该直接调用底层函数，而应该暴露业务级 Tool。

例如：

错误设计：

```
call ST_Buffer()
```

因为 LLM 不理解数据库函数。

正确设计：

```
calculate_service_area()
↓
内部调用：
PostGIS ST_Buffer()
GeoPandas buffer()
Shapely geometry.buffer()
```

---

核心 Tool 可以设计如下：


| Tool                 | 功能     | 底层实现                       |
| -------------------- | ------ | -------------------------- |
| buffer_analysis      | 范围覆盖分析 | Shapely buffer / ST_Buffer |
| distance_analysis    | 距离计算   | PostGIS ST_Distance        |
| route_analysis       | 路径规划   | OSMnx + NetworkX           |
| overlay_analysis     | 空间叠加   | GeoPandas overlay          |
| density_analysis     | 空间密度分析 | PySAL                      |
| suitability_analysis | 综合评价   | Weighted Overlay           |


---



# 2.4 Spatial Agent 一次完整调用流程

例子：

> “帮我分析北京某区域适合建设新能源汽车充电站的位置。”



## 第一步：用户输入需求

React 前端发送：

```json
{"query":"分析北京某区域适合建设新能源汽车充电站的位置"}
```

---



## 第二步：LLM 解析任务

生成：

```json
{
"task":"site_selection",
"industry":"charging_station",
"region":"北京",
"criteria":["traffic", "population", "existing_station"]
}
```

---



## 第三步：Agent 规划工具链

确定调用：

```
查询道路数据
↓
计算交通可达性
↓
查询人口网格
↓
计算服务覆盖范围
↓
分析已有充电站竞争
↓
综合评分
```

---



## 第四步：调用 GIS Tool

例如调用：

```json
{"tool":"suitability_analysis"}
```

后端执行：

```
PostGIS查询数据
↓
GeoPandas处理空间数据
↓
Shapely计算几何关系
↓
生成评分栅格

```

---



## 第五步：返回空间结果

返回：

```json
{
"rank":[{"area":"区域A", "score":92}]
}
```

同时返回：

GeoJSON：

```json
{
"type":"Polygon",
"coordinates":[]
}
```

---



## 第六步：Cesium展示

前端加载 GeoJSON：

```javascript
Cesium.GeoJsonDataSource.load()
```

展示：
高价值区域：红色
低价值区域：蓝色

---



## 第七步：LLM生成报告

输入结构化结果：

```json
{
"score":92,
"advantages":["距离主干道近", "人口覆盖高"]

}
```

输出自然语言分析报告。

---



# 2.5 Spatial Agent 与传统 GIS 工作流的区别

传统 GIS：

```
专家
↓
选择工具
↓
配置参数
↓
运行模型
↓
解释结果

```

Spatial Agent：

```
用户
↓
自然语言
↓
AI理解需求
↓
自动选择模型
↓
调用工具
↓
解释结果
```

最大的变化是：GIS 能力从“工具化”变成“服务化”。

---



# 2.6 Spatial Agent 后续扩展方向



## 1. 多 Agent 协作

未来可以拆分：

```
空间分析 Agent：负责GIS计算
数据 Agent：负责寻找数据
报告 Agent：负责生成文档
可视化 Agent：负责地图表达
```

---



## 2. 空间知识库

引入 RAG：

存储：

- 城市规划规范；
- 土地政策；
- 行业规则；
- 历史分析案例。

例如：

用户：

> “哪里适合建设养老社区？”

Agent 不仅分析空间数据，还结合：

- 老龄人口比例；
- 城市规划政策；
- 医疗资源分布。

---



## 3. 自动生成 GIS 模型

更高级的方向：

用户：

> “分析洪水风险区域。”

Agent 自动创建：

```
DEM数据
↓
坡度分析
↓
河流距离分析
↓
降雨数据融合
↓
风险评价模型
```

形成自动化空间建模能力。

---



# 2.7 本章总结

Spatial Agent 是整个 GeoAI 平台的智能核心，它不替代 GIS 算法，而是负责连接用户需求与 GIS 能力。

其核心架构可以总结为：

```
自然语言输入
↓
LLM理解空间任务
↓
Agent规划分析流程
↓
MCP调用GIS Tool
↓
空间计算服务执行
↓
结构化空间结果
↓
Cesium三维展示
↓
LLM生成决策报告
```

通过 Spatial Agent，传统 GIS 中需要专业人员手动完成的空间分析流程，被转化为用户可直接调用的智能空间能力。