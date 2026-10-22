# Portfolio Release Report

检查日期：2026-10-15（日本时间）。本报告记录本地公开副本的整理与验证，没有上传 GitHub。

## 交付位置与项目定位

公开目录：`ai_story_demo_github/`，与原 `ai_story_demo/` 并列。报告所在目录就是独立公开仓库根目录；为避免公开个人电脑路径，这里不记录盘符和用户目录。

正式项目名：**LLM Interactive Character Simulation**。
建议 Repository 名：**llm-character-simulation**。

实际玩法为日语大学生活角色关系模拟：4个初始主题及自定义主题、固定角色、自由输入和3个推荐行动、好感度与警戒、5个进程阶段、5种结束状态、短期事件记忆、一次撤销、结局统计。原企划中的多角色、Unity、语音等构想未包装成已实现功能。

LLM使用DeepSeek的deepseek-chat，通过OpenAI Python SDK请求生成叙事和行动候选。Python先进行关键词判定、亲密行动随机成败、好感度及阶段更新，再把结果交给模型。结局选择及结局文本由Python控制。生成文本会影响事件记忆的关键词提取，所以并非所有叙事相关数据都与LLM无关。

技术栈：Python 3.14、Gradio 6.26.0、OpenAI SDK 3.7.0、python-dotenv 1.2.3、HTML/CSS。SDK连接DeepSeek，并未使用OpenAI模型或Gemini。

## 三语文档重点

README.md为英文主文档，README_ja.md为对应日文版，README_zh-CN.md为对应简体中文版。三个README均包含介绍、演示、功能、实际执行顺序图、代码职责映射、流程、技术栈、工程要点、Windows安装与启动、环境变量、目录结构、限制及版权说明。

突出数值规则与LLM表现层的分工、阶段约束、JSON解析与候选过滤、回退、会话状态与快照、HTML转义。没有声称严格JSON Schema、LLM语义评分、持久记忆、Unity实现或心理测评。

## 原项目检查与排除清单

原目录共13个文件：两个Python源码、六个企划/说明文本、四张PNG、一个.env。未发现隐藏Git目录、依赖文件、README、原.gitignore、归档包、Notebook、日志、缓存、第三方字体或音乐文件。源码的剧情与规则均内嵌，不需要旁边TXT或PNG运行。

公开版仅从app.py复制运行逻辑，其余原文件均未复制：

| 原文件 | 处理原因 |
| --- | --- |
| .env | 包含非空、真实格式的DeepSeek凭据；实际API验证可用，绝不复制 |
| app - 副本.py | 历史重复版本，与现行阶段和提示词不同 |
| 恋爱企划.txt | 内部企划、个人姓名和时间安排；部分功能是构想 |
| 冒险rpg企划.txt、后宫.txt、思春期.txt、职场模拟企划.txt | 其他方向的未实现企划 |
| 新建文本文档.txt | 内部演示说明，由三个README替代 |
| 初番.png、kissした.png | 含个人姓名，且有过时玩法/状态 |
| 好感度down.png | 与现行规则/界面不同的开发截图 |
| スタート.png | 旧标题；用公开版重新截图替代 |

没有删除或修改原开发文件。整理前后对13个文件逐一进行SHA-256比对，文件集合及哈希全部一致。

## 最小代码修改

- 正式展示标题替换为项目名称。
- dotenv只读取app.py旁边的.env，避免向上搜索误读其他项目配置；环境变量优先。
- 移除异常对象的直接打印，改为不含请求和凭据的通用警告。
- API请求设置30秒超时、不自动重试，失败仍使用原回退逻辑。
- JSON解析增加对象及story字符串类型检查，避免异常类型导致页面失效。
- 增加main入口保护，支持导入验证；只监听本机地址且不生成公开分享链接。
- 将CSS从Blocks构造参数移至launch，以匹配本机已安装的Gradio 6版本。

未重写游戏、未调整数值和平衡、未增添API供应商。原来的少量未用辅助函数及历史内部阶段名保留，避免无关重构。

## Secret、隐私与Git

真实凭据仅发现于原.env。两份源码使用环境变量；初次宽泛匹配命中的api_key变量引用属于误报，复核没有硬编码值。文本扫描覆盖全部源码及TXT，检查了凭据模式、邮件、电话和Windows路径；截图逐张人工视觉检查。企划里的人名及截图里的个人名均通过排除原文件处理。

公开文件进行了凭据正则扫描，以及原密钥字节的精确比对，未发现原密钥、其他匹配凭据、个人邮件或Windows绝对路径。公开版仅有空的.env.example。扫描是此次文件级检查，不代表任何外部备份或过去上传行为已得到证明。

原目录及其父路径不属于Git仓库，无本地提交历史、tracked files或远程配置可查，未发现.env被本地commit的证据。无法据此证明用户从未在其他位置或服务分享过密钥。**若该密钥曾上传远程仓库或公开分享，需要立即rotate该API Key。** 本次未修改密钥。

公开版新建main分支的空Git仓库，没有复制旧.git，没有提交，没有远程地址。`git status`仅列出公开文件，.env不在tracked/staged/untracked中；`git check-ignore`确认.env、.env.local、.venv及Python缓存被忽略，.env.example可见。

## 素材与License

检查到的四张原PNG均为应用界面截图，没有发现外部角色立绘、网络背景、音乐或字体资源。两张包含个人姓名；没有重新发布。公开版docs/screenshots中的三张图片由本次运行产生，使用Player作为虚构姓名，包含设置页、固定回退和在线生成画面，已检查无密钥/个人信息/调试控制台。

代码、角色设定与提示词的原创归属无法仅凭文件证明，故未擅自添加MIT或其他LICENSE。作者确认权利后可再决定代码授权方案；依赖及生成内容的使用条件需分别考虑。

## 安装与运行验证

| 检查 | 结果 |
| --- | --- |
| 在独立公开目录创建全新.venv | 成功，未使用system-site-packages |
| 安装requirements.txt | 成功；使用原机器现有的3个直接依赖版本，未主动升级 |
| pip check | No broken requirements found |
| 无.env、无进程密钥导入 | client为None，成功 |
| python app.py启动与主页 | 成功，浏览器实际打开本机页面 |
| 无密钥一轮核心交互 | 成功：丁寧に自己紹介する，回合1→2，好感度0→12，记忆与选项更新 |
| 一次撤销 | 函数级验证通过，恢复初始状态且标记已使用 |
| 坏JSON/错误story类型/空choices | 模拟响应验证通过，规则与三个行动候选仍可用 |
| 5种结束分支、HTML转义 | 函数级验证通过 |
| 真实API调用 | 成功：HTTP响应成功，call_ai返回有效结果，一轮规则更新通过 |
| 配置密钥后的启动及浏览器交互 | 成功：显示实际生成的剧情与3个新选项，并更新状态 |
| 无原目录运行资源依赖 | app.py只依赖同目录可选.env；没有读取原目录代码/素材 |
| 退出 | 测试服务已停止；另用demo.close验证端口释放及进程正常结束 |
| 原目录完整性 | 全部13个文件哈希不变 |

首次在受限执行环境访问API发生连接错误，正确触发本地回退；允许网络访问后成功。不能将第一次回退误记为API成功。有效凭据只在测试进程内加载，没有写入公开版.env、日志或Git。API测试只发送匿名演示输入。

无.env也能启动和推进规则，但只有简易固定叙事。API在线可用性依赖网络、密钥与余额。成功测试代表本次一轮，不保证所有未来服务请求。没有跑完整人工38回合，也没有进行负载测试或验证所有自由输入语义。

requirements固定的是直接依赖，不是完整跨平台锁文件；本次Windows/Python 3.14安装成功，其他平台和Python版本未验证。本地.venv及运行生成的缓存保留供复验，均被Git忽略，不属于首次提交内容。

## 首次提交建议与待办

建议首次提交仅包含：

- app.py
- requirements.txt
- .env.example
- .gitignore
- README.md
- README_ja.md
- README_zh-CN.md
- PORTFOLIO_RELEASE_REPORT.md
- docs/screenshots/setup.jpg
- docs/screenshots/interaction.jpg
- docs/screenshots/live-interaction.jpg

用户下一步：审阅三语说明及截图，确认代码/提示词权属并决定License；需要自己运行在线模式时，按README在本机配置密钥（当前公开副本没有真实.env）。确认后再自行决定创建GitHub远程和首次commit。2026-10-16已按要求重新拍摄桌面全屏截图，替换三张旧图；当时的英日README改为逐张宽幅展示，当前中文README复用相同截图。

本轮到本地GitHub-ready副本为止，没有登录GitHub、创建远程、提交或push，也没有继续重构游戏。


2026-10-17 文档收尾复核：三个README均已存在，语言切换及本地资源链接有效。通过 `git ls-files --cached --others --exclude-standard` 实际统计，公开文件共11个（不含Git元数据及忽略的本地文件）；`git status --short` 显示9条顶层未跟踪项，其中 `docs/` 汇总三张截图。分支为 `main`，无提交、无暂存项、无远程。首次commit清单已包含 README_zh-CN.md。
