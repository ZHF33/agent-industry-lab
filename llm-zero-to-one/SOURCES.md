# 参考课程拆解与原创编排

核查日期：2026-10-20。实际阅读范围为三仓库README、大纲、LLM Universe站点导航及C1/C2选读；并非通读全部Notebook、视频或外链。站点首页为动态加载，使用其仓库docs目录核对同源内容。

## 参考资料分别贡献什么

| 参考 | 提取的教学方向（概括） | 我们如何使用 |
| --- | --- | --- |
| [LLM Universe在线站点](https://datawhalechina.github.io/llm-universe/#/) / [源码仓库](https://github.com/datawhalechina/llm-universe) | 从应用入门，串联模型接口、知识资料、检索问答和改进 | 用作应用主线参考；先补零基础Python，再重写成自己的业务案例 |
| [LLM Course](https://github.com/mlabonne/llm-course) | 基础知识、模型构建与应用工程三条路线，配相关实验资源 | 为数学机制、数据、训练与效率提供主题地图；不要求初学者直接跑GPU实验 |
| [LLM Cookbook](https://github.com/datawhalechina/llm-cookbook) | 提示设计、问答系统、框架应用、个人数据、界面和评估实践 | 借鉴先做小任务再组成系统的学习节奏；不复制原文、Notebook或视频脚本 |

四个用户链接实际对应三个资料项目：Universe网站与仓库是同一项目的阅读和源码入口。课程计划是我们的原创教学安排，365天不是任一上游的原课程结构。每单元参考标签表示主题相关，不表示上游提供对应作业或为本课程背书。

## 合并后的能力纲要

先建立任务、资料、模型和工具的基本认识；再补编程和数据契约；随后做检索与知识问答、界面和Agent；最后按需进入训练、效率、评估与综合交付。每阶段有可检查作品，单元包含反例和异常分支，而不是背技术名词。

额外加入的教学设计：零命令行起点、无GPU替代任务、合成数据、人工审核、业务口径、对象权限、错误结果核对、版本记录和作品证据。这些结合本仓库案例编排，不声称均来自上述三门课程。

## 版本与事实核查规则

参考教程里的型号、定价、API、包路径、框架语法和实验平台额度可能变化。到对应实操单元时重新查官方文档，固定适用版本；不按历史代码直接认定接口仍可用。学习计划只规划主题，不承诺某品牌或版本一年不变。读到存在歧义的说法应另查原论文或官方资料，不能因教程收录就原样传播。

第一期额外参考：[Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)，用于说明模型能够在输入中利用任务示例；不把该历史论文的参数规模当作所有大模型的定义。

## 许可与归属

- LLM Cookbook的README声明CC BY-NC-SA 4.0；不能把其中翻译教材或Notebook复制过来就整体改成MIT。本栏目没有搬运其文字、代码、图片或课程视频。
- LLM Course仓库LICENSE为Apache-2.0，原作者及上游实验保留自身许可。本栏目不重分发其代码、路线图图片和Notebook。
- LLM Universe本次只作资料链接、短概括和主题参考；本次未取得可覆盖所有内容的明确许可结论，故不复制其正文、图片或源码。
- 本仓库原创教学解释、练习与示例采用MIT；任何未来实际改编或引用应按对应上游条款独立标注，不能用本声明替代许可核对。链接资料不代表获得商标使用或官方合作身份。

许可核查入口：[Cookbook README](https://github.com/datawhalechina/llm-cookbook#license)、[LLM Course LICENSE](https://github.com/mlabonne/llm-course/blob/main/LICENSE)。
