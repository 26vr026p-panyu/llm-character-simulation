# LLM Interactive Character Simulation

[English](README.md) | [日本語](README_ja.md)

一个将 LLM 生成叙事与确定性游戏状态控制、阶段推进、local fallback 和会话内记忆结合起来的互动角色关系模拟原型。

## 项目简介

这是 **PAN YU** 使用 Python / Gradio 开发的大学生活题材角色关系模拟原型，探索生成式角色表达如何与明确的游戏规则协作。玩家可以选择系统推荐的行动，也可以自由输入。

**Python 管理好感度、警戒、阶段推进和结局；LLM 负责叙事与行动建议。** 亲密行为另由 Python 进行随机概率判定，因此整个游戏过程并非完全确定性。

项目尝试在明确的状态与推进规则约束下，构建轻量的角色代理交互模式。它不是完整的自主 AI Agent，没有 tool calling、planner/executor 或外部工具集成。Unity 集成仍属于未来方向。

## 工程亮点

- **职责分离：** Python 控制数值状态与流程推进，LLM 负责叙事表达。
- **阶段约束：** stage-aware prompt 与行动候选过滤共同减少过早跳跃的剧情。
- **失败处理：** JSON 解析、输出检查和 local fallback，让生成失败时仍可继续交互。
- **可恢复的会话状态：** 通过快照复制实现一次性撤销。
- **运行安全：** HTML escaping 与项目内的密钥读取，减少不必要的信息暴露。

## 演示 / 截图

以下截图来自当前公开版，使用虚构的玩家姓名。

**1. 初始设置**

![场景设置](docs/screenshots/setup.jpg)

**2. Local fallback 交互**

![本地回退交互与好感度变化](docs/screenshots/interaction.jpg)

**3. 真实 DeepSeek 生成**

![DeepSeek 生成的叙事与行动候选](docs/screenshots/live-interaction.jpg)

## 系统架构——LLM 与确定性游戏逻辑的职责分离

```text
玩家行动 → Gradio 会话 → Python 关键词规则
                              ↓
                  好感度 / 警戒 / 亲密行为概率判定
                              ↓
                       Python 阶段更新
                              ↓
       状态 + 历史 + 事件记忆 → DeepSeek 叙事与行动候选
                              ↓       （或 local fallback）
                 JSON 解析 + 叙事检查 + 候选规范化
                              ↓
                 记忆 / 统计更新 → 转义后的 HTML UI
                              ↓
                    Python 选择结局并显示固定结局文本
```

**设计原则：LLM 可以生成叙事与行动建议，但不能直接改写好感度、警戒、推进阶段或结局状态。**

| 职责 | `app.py` 中的实现 |
| --- | --- |
| 解释行动并计分 | 日文关键词判断；`calculate_love_change` |
| 判定亲密行为成败 | `judge_romance_success`；Python 根据限定范围内的概率进行随机判定 |
| 控制推进与结局 | `advance_stage`、`is_end_stage`、`make_ending_story` |
| 生成角色叙事 | `make_system_prompt`、`call_ai`；`deepseek-chat` |
| 检查模型输出 | `clean_json_text`、类型检查、`is_bad_story_text`、`normalize_choices` |
| 维护会话状态 | `gr.State`、`make_snapshot`、`undo` |

LLM 接收的是已经计算好的状态。生成文本会影响基于关键词提取的事件记忆。prompt 要求返回的 `special_action` JSON 字段目前没有使用。JSON 格式通过 prompt 约定，并非 API 服务端强制执行的 schema 输出。

## 功能

### LLM 交互

- 生成日文叙事和三个与当前情境相关的行动候选，并支持玩家自由输入。
- 提供四个预设开场场景或自定义开场主题，使用一个固定的角色设定。
- 生成时参考当前阶段、会话内历史和事件记忆；最多保留八条记忆，界面显示其中四条。

### 游戏状态系统

- 好感度、警戒与关系恢复、五个推进阶段、五种结束状态。
- 亲密行为概率判定，以及基于快照的一次性撤销。
- 好感度显示开关、关系变化提示和行动统计。

### 可靠性

- Key 缺失或生成失败时使用 local fallback。
- JSON 解析、叙事验证和行动候选规范化。
- HTML escaping 与项目内的密钥读取。

## 关键工程设计

- **先执行规则，再生成叙事：** 关键词计分与 Python 亲密行为判定先更新状态，随后才将上下文交给模型。结局选择和固定结局文本也由 Python 提供。
- **约束生成输出：** stage-aware prompt 描述当前阶段，JSON 解析、类型与叙事检查、候选规范化负责排除或替换不合适的输出。这些检查不等于服务端 JSON schema 强制约束。
- **失败后保持可玩：** API 调用或解析失败时，使用本地文本和默认候选继续交互，不改变计分规则。
- **恢复会话状态：** 在 Gradio session state 的基础上，快照复制事件记忆和嵌套统计数据，支持一次性撤销。
- **显示与配置安全：** 自定义 HTML 对文本进行转义；服务仅在本地启动；dotenv 只读取 `app.py` 旁的文件；通用错误日志不输出异常细节。

## 游戏流程

设置 → 第一次共同活动 → 第二次共同活动 → 日常交谈 → 两人相处 → 关系确认 → 结果。

Python 根据是否完成自我介绍、回合数和好感度控制阶段转换及结局条件。警戒影响互动与关系恢复；LLM 通过叙事和行动候选表达更新后的状态。

<details>
<summary>详细推进规则</summary>

推进依赖自我介绍状态、回合数和好感度；失败可能使故事提前结束。最终阶段在第 38 回合结算，满足条件时可从第 34 回合起提前进入 Good Ending。如果玩家始终没有自我介绍，则可能一直停留在第一阶段。

</details>

## 技术栈

Python、Gradio、python-dotenv、OpenAI Python SDK，以及 **DeepSeek API**（`deepseek-chat`）。

OpenAI Python SDK 仅作为 API 兼容客户端使用，没有调用 OpenAI 托管的模型，也没有使用 Gemini。

## 安装与运行

`requirements.txt` 固定了开发机器上实际验证过的直接依赖版本。验证环境为 Python 3.14；本次公开版没有验证其他 Python 版本。

在仓库目录中打开 Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# 可选：编辑本地 .env，填写 DEEPSEEK_API_KEY。
python app.py
```

如果无法运行激活脚本，可以直接使用 `.\.venv\Scripts\python.exe` 执行 pip 和 `app.py`。Windows 命令提示符中的激活命令为 `.venv\Scripts\activate.bat`。

打开终端显示的本地地址，通常为 [http://127.0.0.1:7860](http://127.0.0.1:7860)。按 Ctrl+C 停止服务。运行不依赖外部素材或原始开发目录。

没有 `.env` 或进程环境中的 Key 时，UI 和规则仍可通过 local fallback 运行，但文本较简单、重复，行动候选使用默认内容。实时叙事生成需要有效的 DeepSeek Key、网络连接和可用 API 额度。Key 无效或 API 报错也会触发回退，因此界面能运行不代表 API 调用成功。

快速体验时，可以选择 `課題発表`，开始后输入 `丁寧に自己紹介する`。开启 `好感度を表示する` 查看变化，再尝试行动候选或一次性撤销。

## 环境变量

```dotenv
DEEPSEEK_API_KEY=
```

这是唯一的应用专用配置变量。进程环境变量优先于 `app.py` 旁可选的 `.env` 文件。不要提交真实 Key。启用 API 后，玩家姓名、场景、行动、故事历史和事件记忆会发送给 DeepSeek；演示时应使用虚构信息。

## 项目结构

```text
app.py                       # 规则、prompt、本地回退和 UI
requirements.txt             # 固定版本的直接依赖
docs/screenshots/            # 使用匿名数据的公开版截图
.env.example                 # 空的密钥配置模板
.gitignore
README.md / README_ja.md / README_zh-CN.md
PORTFOLIO_RELEASE_REPORT.md   # 公开准备检查与现有局限
```

## 限制与未来方向

行动计分使用子字符串匹配，可能误判否定句和细微语义。亲密行为带有随机判定，因此整个运行过程并非完全确定性。prompt 约束与基础过滤无法保证叙事始终一致。历史会持续增长，目前没有 token budget 控制；记忆不会跨会话持久保存。撤销恢复游戏状态，但不会恢复随机数生成器状态或原先生成的精确候选。结果中的性格标签是基于规则的趣味总结，不是心理测评。

未来方向包括限制历史长度、增强输出验证、增加场景，以及接入 Unity 角色表现层。目前没有实现动画、语音、数据库或持久记忆。

## License / Assets

本公开版暂不授予使用许可，需由作者进一步确认代码与 prompt 的权属。未打包第三方角色立绘、背景、音乐或字体文件；依赖库仍遵循各自的许可证。
