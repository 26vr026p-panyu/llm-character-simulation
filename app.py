import os
import json
import random
import html
import logging
from pathlib import Path
import gradio as gr
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =========================
# 1. API設定
# =========================

load_dotenv(Path(__file__).resolve().parent / ".env")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

client = None
if OpenAI is not None and DEEPSEEK_API_KEY:
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        timeout=30.0,
        max_retries=0
    )


# =========================
# 2. CSS
# =========================

CUSTOM_CSS = """
.gradio-container {
    max-width: 1180px !important;
    margin: auto !important;
}

.story-card {
    border: 1px solid #ddd;
    border-radius: 12px;
    padding: 14px 16px;
    min-height: 250px;
    max-height: 330px;
    overflow-y: auto;
    background: #ffffff;
    line-height: 1.7;
    font-size: 16px;
}

.side-card {
    border: 1px solid #ddd;
    border-radius: 12px;
    padding: 10px 12px;
    background: #ffffff;
    font-size: 14px;
    line-height: 1.45;
}

.status-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.status-table td {
    padding: 4px 6px;
    border-bottom: 1px solid #eee;
}

.status-table td:first-child {
    color: #666;
    width: 36%;
}

.memory-list {
    margin: 4px 0 0 18px;
    padding: 0;
}

.memory-list li {
    margin-bottom: 4px;
}

.small-note {
    color: #666;
    font-size: 13px;
    line-height: 1.4;
    margin-top: 6px;
}

textarea {
    min-height: 52px !important;
}

.app-title {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: 0.2px;
    margin-bottom: 16px;
}

.notice-card {
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 10px;
    background: #f7f7f7;
    border: 1px solid #ddd;
    font-size: 14px;
    line-height: 1.5;
}

.chapter-card {
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 10px;
    background: #f2f2f2;
    border-left: 5px solid #999;
    font-size: 15px;
    line-height: 1.5;
}

.chapter-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 3px;
}

.relation-change {
    font-weight: 700;
}

.mood-text {
    filter: blur(2px);
    transition: filter 0.2s ease;
    user-select: none;
}

.mood-text:hover {
    filter: blur(0px);
}
"""


# =========================
# 3. 世界観
# =========================

HEROINE_PROFILE = """
名前：白石美咲（しらいし みさき）
学年：大学2年生
性格：
- 真面目で責任感が強い
- 初対面ではかなり距離を取る
- 連絡先交換にはかなり慎重
- 初対面では自分から連絡先を聞かない
- 親しくない相手から急に連絡先を聞かれると距離を取る
- ただし、最初の共同作業が進み「連絡先がないと不便」と判断した場合だけ、自分から作業用の連絡先交換を提案する
- 信頼していない相手から急に距離を詰められるのは苦手
- 中盤以降、心を開くと自分から話題を振ったり、少しだけ踏み込んだことを言う
- 空気を読まない発言や、人前での失言にはかなり傷つく
"""

SCENARIO_PRESETS = {
    "課題発表": "大学の授業で、2人1組の課題発表を行うことになった。",
    "文化祭準備": "大学の文化祭で、2人が同じ企画担当になった。",
    "サークル企画": "新歓イベントの企画で、2人が同じ担当になった。",
    "ゲーム制作": "授業内のミニゲーム制作課題で、2人がチームになった。"
}


def make_system_prompt(scenario_text):
    return f"""
あなたは大学生活を舞台にした、恋愛寄りインタラクティブストーリーのシナリオ生成AIです。

基本設定：
{scenario_text}

ヒロイン設定：
{HEROINE_PROFILE}

重要ルール：
- 日本語で出力する
- 本文は180字以内
- 主調は恋愛よりも「関係が少しずつ変化する大学生活ストーリー」にする
- 最初の共同作業は長く引っ張りすぎない
- ただし、急に打ち上げ・デート・告白・交際成立へ飛ばさない
- 物語は「初回の共同作業 → 二回目の共同作業 → 作業後の雑談 → 二人で過ごす時間 → 関係の確認」の順に自然に進める
- 各段階では、必要に応じて「数日後」「次の作業日」「作業が一段落したあと」などの自然な時間経過や、次に会う理由を一文で補う
- 内部ステージ名やChapter名を本文にそのまま出さない
- 恋愛要素は急に出さず、まずは信頼、会話の自然さ、また会う理由から描写する
- 連絡先の話題はユーザーが連絡先に触れた時だけ扱う。美咲から突然連絡先を提案しない
- 関係が浅い段階での恋愛行動や連絡先交換は失敗しやすい
- 選択肢は「発言」だけでなく「行動」でもよい
- 選択後は確認で止めず、Story内で次の状況まで自然に進める
- 状況が合う場合だけ、1つだけ少し不器用な選択肢を自然に混ぜてもよい
- 露骨な地雷や不自然すぎる選択肢は避ける
- 選択肢に「地雷」「成功率」「高リスク」などのラベルは書かない
- 出力は必ずJSONのみ
- Markdown、コードブロック、説明文は禁止

JSON形式：
{{
  "story": "本文",
  "choices": ["選択肢1", "選択肢2", "選択肢3"],
  "special_action": ""
}}
"""

def make_initial_scene(player_name, scenario_text):
    scenario_text = str(scenario_text)

    if "文化祭" in scenario_text:
        opening = f"""
放課後、文化祭準備の打ち合わせが始まった。

{player_name}は、同じ企画担当になった白石美咲と並んで座ることになった。
彼女は資料を抱えたまま、少し緊張した様子でこちらを見る。

「白石です。よろしくお願いします。
まずは、今日決めることを整理した方がよさそうですね」

まだ、彼女はこちらの名前も性格も知らない。
話し方は丁寧だが、距離はかなりある。
"""

    elif "サークル" in scenario_text or "新歓" in scenario_text:
        opening = f"""
サークルのミーティング後、新歓イベントの担当分けが決まった。

{player_name}は、白石美咲と同じ企画担当になった。
彼女はメモを取りながら、控えめにこちらへ視線を向ける。

「白石です。よろしくお願いします。
イベントの内容、先に確認しておきましょうか」

まだ、彼女はこちらの名前も性格も知らない。
話し方は丁寧だが、必要以上には踏み込んでこない。
"""

    elif "ゲーム" in scenario_text or "制作" in scenario_text:
        opening = f"""
制作チームの担当分けが終わり、短いミーティングが始まった。

{player_name}は、白石美咲と同じチームになった。
彼女はノートPCを開きながら、少し緊張した表情でこちらを見る。

「白石です。よろしくお願いします。
まずは、どこまで作るか決めた方がよさそうですね」

まだ、彼女はこちらの名前も性格も知らない。
会話は事務的で、距離はかなりある。
"""

    elif "サッカー" in scenario_text or "試合" in scenario_text or "マネージャー" in scenario_text:
        opening = f"""
放課後、サッカー部の企画ミーティングが始まった。

{player_name}は、試合分析の担当として白石美咲と組むことになった。
彼女は資料を整理しながら、真面目な表情でこちらを見る。

「白石です。よろしくお願いします。
まずは、分析の目的を決めた方がよさそうですね」

まだ、彼女はこちらの名前も性格も知らない。
話し方は丁寧だが、どこか距離を置いている。
"""

    elif "授業" in scenario_text or "課題" in scenario_text or "発表" in scenario_text:
        opening = f"""
授業の終わり、先生が2人組の担当を発表した。

{player_name}は、隣の席に座っていた白石美咲と組むことになった。
彼女は少し緊張した表情でノートを閉じ、こちらを見る。

「白石です。よろしくお願いします。
まずは、発表の方向性を決めましょうか」

まだ、彼女はこちらの名前も性格も知らない。
話し方は丁寧だが、必要以上には距離を詰めてこない。
"""

    else:
        opening = f"""
ある日の放課後、二人で進める企画の担当が決まった。

{player_name}は、白石美咲と同じ担当になった。
彼女は少し緊張した表情で資料を持ち、こちらを見る。

「白石です。よろしくお願いします。
まずは、今日決めることを整理しましょうか」

まだ、彼女はこちらの名前も性格も知らない。
話し方は丁寧だが、距離はかなりある。
"""

    return f"""
{opening}

今回の最初のイベント：
{scenario_text}
"""


# =========================
# 4. 状態管理
# =========================

STAGE_ORDER = [
    "first_event",
    "celebration",
    "date_1",
    "date_2",
    "ending"
]

STAGE_LABELS = {
    "first_event": "初回の共同作業",
    "celebration": "二回目の共同作業",
    "date_1": "作業後の雑談",
    "date_2": "二人で過ごす時間",
    "ending": "関係の確認",
    "bad_early": "初期段階で距離が開く",
    "bad_distance": "自然消滅",
    "bad_reject": "気持ちのすれ違い",
    "good_end": "Good Ending",
    "normal_end": "Normal Ending"
}


def clamp(value, min_value=-30, max_value=100):
    return max(min_value, min(max_value, value))


def get_stage_label(stage):
    return STAGE_LABELS.get(stage, stage)


def get_chapter_title(stage, scenario_text):
    if stage == "first_event":
        return "Chapter 1：初回の共同作業"
    elif stage == "celebration":
        return "Chapter 2：二回目の共同作業"
    elif stage == "date_1":
        return "Chapter 3：作業後の雑談"
    elif stage == "date_2":
        return "Chapter 4：二人で過ごす時間"
    elif stage == "ending":
        return "Final Chapter：関係の確認"
    elif stage == "good_end":
        return "Good Ending"
    elif stage == "normal_end":
        return "Normal Ending"
    elif stage.startswith("bad"):
        return "Bad Ending"
    return get_stage_label(stage)

def get_chapter_notice(old_stage, new_stage, scenario_text):
    """
    イベント段階が変わった時だけ、章タイトルを表示する。
    ここでは固定会話を書かず、実際の場面描写はLLMに任せる。
    """
    if old_stage == new_stage:
        return ""

    return f"""
<div class="chapter-card">
    <div class="chapter-title">{esc(get_chapter_title(new_stage, scenario_text))}</div>
    <div>物語が少し進みました。</div>
</div>
"""

def get_relationship_notice(old_relationship, new_relationship):
    """
    関係段階が変わった時だけ表示する。
    """
    if old_relationship == new_relationship:
        return ""

    return f"""
<div class="notice-card">
    <div class="relation-change">関係が変化しました</div>
    <div>{esc(old_relationship)} → {esc(new_relationship)}</div>
</div>
"""


def get_love_mood(love, caution):
    """
    具体的な好感度ではなく、プレイヤー視点の曖昧な状態として表示する。
    """
    if caution:
        return "警戒しているように見える"

    if love < 5:
        return "まだかなり距離がある"
    elif love < 18:
        return "少しだけ会話できる"
    elif love < 32:
        return "少し慣れてきたように見える"
    elif love < 48:
        return "会話が自然になってきた"
    elif love < 62:
        return "少し楽しそうに見える"
    elif love < 76:
        return "距離が近くなっている気がする"
    elif love < 88:
        return "こちらを意識しているように見える"
    else:
        return "特別に思っている……かもしれない"


def get_relationship(love, introduced, caution):
    if caution:
        return "警戒されている"

    if not introduced:
        return "初対面・名前も知らない"

    if love < 0:
        return "距離を置かれている"
    elif love < 15:
        return "用事がある相手"
    elif love < 30:
        return "少し話せる相手"
    elif love < 45:
        return "話しやすい相手"
    elif love < 60:
        return "友人に近い相手"
    elif love < 72:
        return "少し気になる相手"
    elif love < 84:
        return "友達以上……？"
    elif love < 93:
        return "恋人未満……？"
    else:
        return "特別な存在"


def get_progress_hint(stage, love, introduced, caution):
    if caution:
        return "失言や距離感を挽回する必要がある"
    if not introduced:
        return "まずは自然に名乗る"
    if stage == "first_event":
        return "共同作業を短く進め、距離を作る"
    if stage == "celebration":
        return "成功後の空気で関係を進める"
    if stage == "date_1":
        return "二人で過ごす空気を見る"
    if stage == "date_2":
        return "相手の気持ちを探る"
    if stage == "ending":
        return "関係をどうするか決める"
    return "状況を見る"


def get_ending_hint(love, turn, stage):
    if stage.startswith("bad"):
        return "Bad End"
    if stage in ["good_end", "normal_end"]:
        return "Result"
    if turn < 8:
        return "序盤"
    if love < 20:
        return "このままだと友人未満"
    elif love < 45:
        return "友人ルート"
    elif love < 70:
        return "可能性あり"
    elif love < 88:
        return "かなり良い雰囲気"
    else:
        return "告白ルート目前"


# =========================
# 5. 行動判定
# =========================

INTRODUCTION_PATTERNS = [
    "自己紹介", "名乗", "名前", "よろしく"
]

POSITIVE_PATTERNS = [
    "丁寧", "相談", "一緒", "手伝", "助け", "尊重", "ありがとう",
    "ごめん", "謝", "確認", "聞く", "得意", "大丈夫",
    "褒める", "真剣", "頑張", "支える", "楽しかった",
    "安心", "嬉しい", "無理しなくていい"
]

NEGATIVE_PATTERNS = [
    "任せる", "適当", "無視", "面倒", "興味ない",
    "全部やって", "勝手に決め", "丸投げ", "強引",
    "返事を迫る", "急かす"
]

ROMANCE_PATTERNS = [
    "好き", "デート", "付き合", "恋人", "一緒に帰",
    "カフェ", "課題以外", "連絡先", "LINE", "会いたい",
    "二人で", "お茶", "また会", "今度会", "特別"
]

BIG_POSITIVE_PATTERNS = [
    "一緒にいると安心",
    "今日一緒にいられて楽しかった",
    "頑張っているところが好き",
    "大切に思っている",
    "これからも会いたい",
    "美咲といると楽しい",
    "真剣に伝える"
]

BIG_NEGATIVE_PATTERNS = [
    "悪口",
    "酒の勢い",
    "酔って",
    "空気を読まず",
    "人前でからかう",
    "笑いもの",
    "白石さんのせい",
    "他の女子と比べる",
    "元カノ"
]

RECOVERY_PATTERNS = [
    "謝る", "ごめん", "反省", "言い過ぎた", "言い訳せず",
    "弁解せず", "ちゃんと向き合う", "誠実に謝る"
]

CONTACT_PATTERNS = [
    "連絡先", "LINE", "DM", "インスタ"
]


def contains_any(text, patterns):
    return any(p in str(text) for p in patterns)


def is_introduction_action(text):
    return contains_any(text, INTRODUCTION_PATTERNS)


def is_positive_action(text):
    return contains_any(text, POSITIVE_PATTERNS)


def is_negative_action(text):
    return contains_any(text, NEGATIVE_PATTERNS)


def is_romance_action(text):
    return contains_any(text, ROMANCE_PATTERNS)


def is_big_positive(text):
    return contains_any(text, BIG_POSITIVE_PATTERNS)


def is_big_negative(text):
    return contains_any(text, BIG_NEGATIVE_PATTERNS)


def is_contact_action(text):
    return contains_any(text, CONTACT_PATTERNS)


def is_recovery_action(text, caution):
    return caution and contains_any(text, RECOVERY_PATTERNS)


def strip_action(text):
    return str(text).strip()


def get_romance_success_rate(love, introduced, stage):
    if not introduced:
        return 0

    if love < 20:
        base = 0
    elif love < 35:
        base = 10
    elif love < 50:
        base = 25
    elif love < 65:
        base = 40
    elif love < 80:
        base = 55
    else:
        base = 75

    if stage == "date_1":
        base += 10
    elif stage == "date_2":
        base += 15
    elif stage == "ending":
        base += 25

    return clamp(base, 0, 90)


def judge_romance_success(action, love, introduced, stage):
    if not is_romance_action(action):
        return None

    rate = get_romance_success_rate(love, introduced, stage)
    return random.randint(1, 100) <= rate


def calculate_love_change(action, love, introduced, stage, romance_success, caution):
    """
    初期は上がりやすい。
    中後期は通常行動では上がりにくい。
    重要イベントだけ大きく動く。
    """

    if is_big_negative(action):
        return -15

    if is_recovery_action(action, caution):
        return 9

    if is_big_positive(action) and stage in ["date_1", "date_2", "ending"]:
        return 12

    if is_contact_action(action) and love < 20:
        return -6

    if is_negative_action(action):
        return -7

    change = 0

    if is_introduction_action(action) and not introduced:
        change += 6

    if is_positive_action(action):
        if love < 30:
            change += 7
        elif love < 55:
            change += 4
        else:
            change += 2

    if stage == "first_event" and ("進める" in action or "作業" in action or "目標" in action):
        change += 4

    if is_romance_action(action):
        if romance_success is True:
            if love < 55:
                change += 5
            else:
                change += 3
        elif romance_success is False:
            if love < 35:
                change -= 8
            else:
                change -= 4

    return clamp(change, -15, 12)


def update_introduced(introduced, action):
    if introduced:
        return True
    return is_introduction_action(action)


# =========================
# 6. ステージ進行
# =========================
def should_heroine_offer_contact(stage, turn, love, introduced, memories):
    """
    以前は自動で連絡先交換を提案していたが、現在は無効化。
    連絡先の話題はユーザーが明示的に触れた時だけ処理する。
    """
    return False

def advance_stage(stage, turn, love, introduced, action):
    """
    Open Campus向けの自然な短編進行。
    コードは段階だけを管理し、実際の場面転換や会話はLLMに任せる。
    """

    if not introduced:
        return "first_event"

    # 第1段階：初回の共同作業
    # 4〜8ターン程度で次回の作業へ進める。
    if stage == "first_event":
        if turn >= 9 and love < 5:
            return "bad_early"
        if turn >= 4 and love >= 16:
            return "celebration"
        if turn >= 7 and love >= 6:
            return "celebration"
        if turn >= 9:
            return "celebration"
        return "first_event"

    # 第2段階：二回目の共同作業
    # ここは成功会ではなく、初回イベントの自然な延長として扱う。
    if stage == "celebration":
        if turn >= 17 and love < 12:
            return "bad_distance"
        if turn >= 10 and love >= 28:
            return "date_1"
        if turn >= 14 and love >= 18:
            return "date_1"
        if turn >= 17:
            return "date_1"
        return "celebration"

    # 第3段階：作業後の雑談
    # 課題の話から少しだけ個人的な会話へ移る。
    if stage == "date_1":
        if turn >= 24 and love < 28:
            return "bad_distance"
        if turn >= 18 and love >= 45:
            return "date_2"
        if turn >= 22 and love >= 32:
            return "date_2"
        if turn >= 24:
            return "date_2"
        return "date_1"

    # 第4段階：二人で過ごす時間
    # 正式なデートに限定せず、自然に一緒にいる時間として扱う。
    if stage == "date_2":
        if turn >= 31 and love < 45:
            return "bad_distance"
        if turn >= 26 and love >= 62:
            return "ending"
        if turn >= 30 and love >= 48:
            return "ending"
        if turn >= 32:
            return "ending"
        return "date_2"

    # 最終段階：関係の確認
    # すぐ告白・交際成立にせず、数ターン余韻を残す。
    if stage == "ending":
        if "断る" in action or "友達で" in action or "拒否" in action:
            return "bad_reject"

        if turn >= 38:
            if love >= 78:
                return "good_end"
            elif love >= 58:
                return "normal_end"
            else:
                return "bad_distance"

        # 十分に関係ができており、終盤で明確に気持ちを伝えた場合だけ早めにGoodへ。
        if love >= 86 and turn >= 34 and ("好き" in action or "大切" in action or "これからも" in action or "また会" in action):
            return "good_end"

        return "ending"

    return stage

def is_end_stage(stage):
    return stage in ["bad_early", "bad_distance", "bad_reject", "good_end", "normal_end"]


# =========================
# 7. 記憶・統計
# =========================

def add_memory(memories, memory):
    if memory and memory not in memories:
        memories.append(memory)


def update_memories(memories, action, story, love_change, stage, caution):
    if memories is None:
        memories = []

    text = action + " " + story

    if is_introduction_action(action):
        add_memory(memories, "2人は自己紹介をした。")

    # 連絡先は、ユーザーが話題にした場合だけ記憶する。
    if is_contact_action(action):
        if love_change < 0:
            add_memory(memories, "美咲は急な連絡先交換に少し距離を取った。")
        elif "交換" in story or "連絡先" in story or "LINE" in story:
            add_memory(memories, "作業用の連絡先について話した。")

    if stage == "first_event":
        add_memory(memories, "初回の共同作業を進めた。")

    if stage == "celebration":
        add_memory(memories, "二回目の共同作業で前回の続きを進めた。")

    if stage == "date_1":
        add_memory(memories, "作業後に少し雑談する時間ができた。")

    if stage == "date_2":
        add_memory(memories, "二人で過ごす時間が少し自然になってきた。")

    if stage == "ending":
        add_memory(memories, "課題後の関係について意識する段階になった。")

    if is_big_negative(action):
        add_memory(memories, "美咲は主人公の言葉に傷ついた。")
        add_memory(memories, "空気が悪くなった。")

    if is_recovery_action(action, caution):
        add_memory(memories, "主人公は失言を挽回しようとした。")

    if love_change >= 10:
        add_memory(memories, "美咲はかなり心を動かされた。")
    elif love_change >= 5:
        add_memory(memories, "美咲は少し心を開いた。")
    elif love_change <= -10:
        add_memory(memories, "美咲は強く距離を取った。")
    elif love_change <= -5:
        add_memory(memories, "美咲は少し警戒した。")

    return memories[-8:]

def format_memories(memories):
    if not memories:
        return ["まだ重要な記憶はありません。"]
    return memories[-4:]


def create_initial_stats():
    return {
        "stage_delta": {
            "first_event": 0,
            "celebration": 0,
            "date_1": 0,
            "date_2": 0,
            "ending": 0
        },
        "positive": 0,
        "negative": 0,
        "romance": 0,
        "recovery": 0,
        "custom": 0,
        "undo_used": False
    }


def update_stats(stats, stage, action, love_change, source, recovered):
    if stats is None:
        stats = create_initial_stats()

    if stage in stats["stage_delta"]:
        stats["stage_delta"][stage] += love_change

    if love_change > 0:
        stats["positive"] += 1
    elif love_change < 0:
        stats["negative"] += 1

    if is_romance_action(action):
        stats["romance"] += 1

    if recovered:
        stats["recovery"] += 1

    if source == "custom":
        stats["custom"] += 1

    return stats


def get_personality_analysis(stats):
    positive = stats.get("positive", 0)
    negative = stats.get("negative", 0)
    romance = stats.get("romance", 0)
    recovery = stats.get("recovery", 0)
    custom = stats.get("custom", 0)

    if recovery >= 1 and positive >= negative:
        mbti = "ENFJ型"
        desc = "失敗しても関係を修復しようとする、対人調整型の主人公。"
    elif romance >= 4 and positive >= negative:
        mbti = "ENFP型"
        desc = "感情表現が多く、勢いで距離を縮める主人公。"
    elif custom >= 5:
        mbti = "INTJ型"
        desc = "選択肢に頼らず、自分の方針で進める戦略型の主人公。"
    elif negative > positive:
        mbti = "ESTP型・暴走気味"
        desc = "行動力はあるが、空気を読み損ねやすい主人公。"
    else:
        mbti = "ISFJ型"
        desc = "慎重に相手を気遣いながら進める安定型の主人公。"

    return mbti, desc


# =========================
# 8. 選択肢
# =========================

def shuffled_three(base, risk=None):
    items = base[:]

    if risk and random.random() < 0.45:
        replace_idx = random.randint(0, 2)
        items[replace_idx] = risk

    random.shuffle(items)
    return items[:3]


def get_default_choices(stage, love, introduced, scenario_text, caution):
    """
    APIが使えない時だけ使う汎用fallback。
    通常の選択肢生成はLLMに任せるため、ここでは固定イベント感を出さない。
    """
    if caution:
        return [
            "誠実に謝る",
            "言い訳せずに自分の言葉を訂正する",
            "少し落ち着いて相手の反応を見る"
        ]

    if not introduced:
        return [
            "自然に自己紹介する",
            "今日やることを一緒に確認する",
            "相手の考えを聞く"
        ]

    if stage == "ending":
        return [
            "課題が終わってもまた話せたら嬉しいと伝える",
            "相手の気持ちを急かさずに聞く",
            "今日まで一緒に進められてよかったと伝える"
        ]

    return [
        "今の流れに合わせて作業を進める",
        "相手の反応を見ながら話を続ける",
        "少しだけ個人的な話題を出してみる"
    ]

def choice_matches_stage(choice, stage, introduced):
    if introduced and ("自己紹介" in choice or "名前を伝える" in choice):
        return False

    # 序盤で急に恋愛イベントへ飛ぶ選択肢は除外する。
    if stage in ["first_event", "celebration"]:
        if "告白" in choice or "付き合" in choice or "デート" in choice:
            return False

    # 終盤以外で交際確定のような選択肢は除外する。
    if stage != "ending" and ("付き合" in choice or "恋人" in choice):
        return False

    return True

def normalize_choices(choices, stage, love, introduced, scenario_text, caution):
    defaults = get_default_choices(stage, love, introduced, scenario_text, caution)

    cleaned = []

    if isinstance(choices, list):
        for c in choices:
            c = strip_action(c)
            if not c:
                continue
            if not choice_matches_stage(c, stage, introduced):
                continue
            if c not in cleaned:
                cleaned.append(c)

    for d in defaults:
        if len(cleaned) >= 3:
            break
        if d not in cleaned:
            cleaned.append(d)

    while len(cleaned) < 3:
        c = random.choice(defaults)
        if c not in cleaned:
            cleaned.append(c)

    # LLMが生成した自然な順番をなるべく保つ。
    return cleaned[:3]

# =========================
# 9. LLM
# =========================

def clean_json_text(text):
    if not text:
        return ""

    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text.strip()


def is_bad_story_text(story):
    if not story:
        return True

    bad_words = ['"story"', '"choices"', "{", "}", "[", "]", "JSON", "```"]
    return any(w in story for w in bad_words)


def local_story(action, love, introduced, player_name, stage, scenario_text, romance_success, caution):
    """
    APIが使えない時の最小fallback。
    通常の場面転換・選択肢はLLMに任せるため、ここでは固定イベント感を弱める。
    """
    if is_big_negative(action):
        story = "その一言で、美咲の表情が止まった。笑って流せる空気ではなくなり、彼女は静かに視線を落とす。"
        return story, get_default_choices(stage, love, introduced, scenario_text, True)

    if is_recovery_action(action, caution):
        story = "あなたが言い訳せずに謝ると、美咲は少しだけ表情を緩めた。「……ちゃんと謝ってくれるなら、少し安心しました」"
        return story, get_default_choices(stage, love, introduced, scenario_text, False)

    if is_contact_action(action) and love < 20:
        story = "美咲は少し戸惑ったように目を伏せた。「すみません、まだ会ったばかりなので……。必要なことは、次に会った時に確認すれば大丈夫だと思います」"
        return story, ["急かしてしまったことを謝る", "次に会った時に確認しようと言う", "共同作業の話に戻す"]

    if is_contact_action(action) and love < 55:
        story = "美咲は少し考えてからうなずいた。「個人的なものではなく、作業連絡用なら……大丈夫です」"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if is_contact_action(action):
        story = "美咲は少し照れたように視線をそらした。「作業の連絡もありますし……交換しておきましょうか」"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if romance_success is True:
        story = "美咲は少し驚いたあと、照れたように笑った。「……そう言ってもらえるのは、少し嬉しいです」"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if romance_success is False:
        story = "美咲は困ったように笑った。「嫌というわけではないんですけど……今はまだ、少し早いかなって」"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if is_introduction_action(action):
        story = f"{player_name}が名乗ると、美咲は少しだけ表情を和らげた。「白石美咲です。改めてよろしくお願いします」"
        return story, get_default_choices(stage, love, True, scenario_text, caution)

    if stage == "first_event":
        story = "二人は今できることを確認しながら、少しずつ作業を進めた。美咲の反応はまだ控えめだが、会話は続いている。"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if stage == "celebration":
        story = "別の日、二人は前回の続きを進めるためにもう一度集まった。前より少しだけ、会話の空気は自然になっている。"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if stage == "date_1":
        story = "作業が一段落し、二人は少しだけ雑談する時間ができた。課題の話だけではなく、普段の話も少し混ざり始める。"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if stage == "date_2":
        story = "何度か一緒に過ごすうちに、二人の距離は少しずつ変わってきた。美咲の声も、以前より柔らかい。"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    if stage == "ending":
        if love >= 70:
            story = "課題が終わりに近づく中、美咲は少し迷ったようにこちらを見る。「これが終わったら、こうして話す理由もなくなるんですね」"
        else:
            story = "課題が終わりに近づき、二人の関係も一区切りを迎えようとしていた。美咲は丁寧だが、少し距離を残している。"
        return story, get_default_choices(stage, love, introduced, scenario_text, caution)

    return "美咲は少し考えたあと、静かにうなずいた。二人の距離は、少しずつ変わっている。", get_default_choices(stage, love, introduced, scenario_text, caution)

def call_ai(history, memories, action, love, new_love, introduced, new_introduced, player_name, old_stage, stage, scenario_text, romance_success, caution, stage_changed):
    if client is None:
        return None

    memory_text = "\n".join([f"- {m}" for m in memories]) if memories else "まだ重要な記憶はありません。"

    romance_result = "なし"
    if romance_success is True:
        romance_result = "親密な行動は成功"
    elif romance_success is False:
        romance_result = "親密な行動は失敗"

    stage_change_text = "今回、物語の段階が少し進んだ。" if stage_changed else "今回、物語の段階は大きく変わっていない。"

    stage_instruction = f"""
現在の内部ステージ：{get_stage_label(stage)}
直前の内部ステージ：{get_stage_label(old_stage)}
物語段階の変化：{stage_change_text}

段階に関する注意：
- 内部ステージ名やChapter名を本文にそのまま出さない
- 段階が進んだ場合でも、急に打ち上げ・デート・告白・交際成立へ飛ばさない
- 段階が進んだ場合は、「数日後」「次の作業日」「作業が一段落したあと」など、自然な時間経過や次に会う理由を一文だけ入れる
- 現在のユーザー行動から自然につながる展開を書く
- 固定イベントではなく、現在の関係性と記憶に合わせて場面を作る
- 選択肢も現在の場面に合う自然な行動にする
- 連絡先の話題はユーザーが明示した時だけ扱う。ユーザーが触れていない場合、美咲から突然連絡先を出さない
"""

    prompt = f"""
主人公の名前：{player_name}
初期テーマ：{scenario_text}
自己紹介済み：{new_introduced}
行動前の好感度：{love}
行動後の好感度：{new_love}
行動前の関係：{get_relationship(love, introduced, caution)}
行動後の関係：{get_relationship(new_love, new_introduced, caution)}
親密行動の判定：{romance_result}

{stage_instruction}

重要な記憶：
{memory_text}

これまでの物語：
{history}

ユーザーの行動：
{action}

次の展開と選択肢を3つ生成してください。
選択後に確認で止めず、次の状況まで自然に進めてください。
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": make_system_prompt(scenario_text)},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85
        )

        text = response.choices[0].message.content
        text = clean_json_text(text)
        data = json.loads(text)

        if not isinstance(data, dict):
            return None

        story = data.get("story", "")
        choices = data.get("choices", [])

        if not isinstance(story, str) or is_bad_story_text(story):
            return None

        return story, choices

    except Exception:
        logging.getLogger(__name__).warning("LLM unavailable or invalid response; using local fallback.")
        return None

# =========================
# 10. 表示
# =========================

def esc(text):
    return html.escape(str(text))


def format_story_html(story, relation_notice="", chapter_notice=""):
    return f"""
{chapter_notice}
{relation_notice}
<div class="story-card">
    <h3 style="margin-top:0;">Story</h3>
    <div>{esc(story).replace(chr(10), "<br>")}</div>
</div>
"""



def format_status_html(love, love_change, turn, introduced, stage, show_love, caution):
    relationship = get_relationship(love, introduced, caution)
    progress = get_progress_hint(stage, love, introduced, caution)
    ending = get_ending_hint(love, turn, stage)
    mood = get_love_mood(love, caution)

    sign = "+" if love_change > 0 else ""

    love_row = ""
    if show_love:
        love_row = f"<tr><td>好感度</td><td><b>{love}</b> / 100 ({sign}{love_change})</td></tr>"

    return f"""
<div class="side-card">
    <h3 style="margin:0 0 6px 0;">Status</h3>
    <table class="status-table">
        <tr><td>美咲の様子</td><td><span class="mood-text">{esc(mood)}</span></td></tr>
        {love_row}
        <tr><td>関係</td><td>{esc(relationship)}</td></tr>
        <tr><td>イベント</td><td>{esc(get_stage_label(stage))}</td></tr>
        <tr><td>ターン</td><td>{turn}</td></tr>
        <tr><td>方針</td><td>{esc(progress)}</td></tr>
        <tr><td>傾向</td><td>{esc(ending)}</td></tr>
    </table>
    <div class="small-note">※ 好感度はチェックを入れると具体的な数値で表示されます。</div>
</div>
"""



def format_memory_html(memories):
    items = format_memories(memories)
    li_html = "".join([f"<li>{esc(m)}</li>" for m in items])

    return f"""
<div class="side-card">
    <h3 style="margin:0 0 6px 0;">Memory</h3>
    <ul class="memory-list">
        {li_html}
    </ul>
</div>
"""


def format_result_html(story, love, stats, turn):
    mbti, desc = get_personality_analysis(stats)
    stage_delta = stats.get("stage_delta", {})
    undo_text = "使用した" if stats.get("undo_used") else "使用しなかった"

    rows = ""
    for k, v in stage_delta.items():
        label = get_stage_label(k)
        sign = "+" if v > 0 else ""
        rows += f"<tr><td>{esc(label)}</td><td>{sign}{v}</td></tr>"

    return f"""
<div class="story-card">
    <h3 style="margin-top:0;">Ending</h3>
    <div>{esc(story).replace(chr(10), "<br>")}</div>
    <hr>
    <h3>Result</h3>
    <table class="status-table">
        <tr><td>最終好感度</td><td><b>{love}</b> / 100</td></tr>
        <tr><td>ターン数</td><td>{turn}</td></tr>
        <tr><td>悔棋</td><td>{undo_text}</td></tr>
        {rows}
    </table>
    <h3>主人公性格分析</h3>
    <p><b>{esc(mbti)}</b></p>
    <p>{esc(desc)}</p>
</div>
"""


def refresh_status(love, love_change, turn, introduced, stage, show_love, caution):
    return format_status_html(love, love_change, turn, introduced, stage, show_love, caution)


# =========================
# 11. 進行
# =========================

def make_snapshot(history, love, love_change, memories, turn, introduced, stage, scenario_text, stats, caution):
    return {
        "history": history,
        "love": love,
        "love_change": love_change,
        "memories": list(memories),
        "turn": turn,
        "introduced": introduced,
        "stage": stage,
        "scenario_text": scenario_text,
        "stats": json.loads(json.dumps(stats)),
        "caution": caution
    }


def start_game(player_name, preset, custom_scenario):
    player_name = str(player_name).strip() or "主人公"

    custom_scenario = str(custom_scenario).strip()
    if custom_scenario:
        scenario_text = custom_scenario
    else:
        scenario_text = SCENARIO_PRESETS.get(preset, SCENARIO_PRESETS["課題発表"])

    love = 0
    love_change = 0
    turn = 1
    introduced = False
    stage = "first_event"
    memories = []
    stats = create_initial_stats()
    caution = False
    show_love = False
    undo_used = False
    prev_state = None

    history = make_initial_scene(player_name, scenario_text)
    choices = get_default_choices(stage, love, introduced, scenario_text, caution)

    initial_chapter_notice = f"""
<div class="chapter-card">
    <div class="chapter-title">{esc(get_chapter_title(stage, scenario_text))}</div>
    <div>{esc(scenario_text)}</div>
</div>
"""

    return (
        format_story_html(history, chapter_notice=initial_chapter_notice),
        format_status_html(love, love_change, turn, introduced, stage, show_love, caution),
        format_memory_html(memories),
        history,
        love,
        love_change,
        memories,
        turn,
        introduced,
        stage,
        scenario_text,
        stats,
        caution,
        prev_state,
        undo_used,
        player_name,
        gr.update(value=choices[0]),
        gr.update(value=choices[1]),
        gr.update(value=choices[2]),
        gr.update(visible=False),
        "",
        gr.update(value=False),
        gr.update(visible=False),
        gr.update(visible=True)
    )


def proceed(action, history, love, love_change_state, memories, turn, introduced, stage, scenario_text, stats, caution, prev_state, undo_used, player_name, show_love, source):
    action = strip_action(action) or "少し考える"

    old_relationship = get_relationship(love, introduced, caution)
    old_stage = stage

    snapshot = make_snapshot(history, love, love_change_state, memories, turn, introduced, stage, scenario_text, stats, caution)

    romance_success = judge_romance_success(action, love, introduced, stage)
    love_change = calculate_love_change(action, love, introduced, stage, romance_success, caution)
    new_love = clamp(love + love_change)
    new_introduced = update_introduced(introduced, action)

    recovered = is_recovery_action(action, caution)
    new_caution = caution

    if is_big_negative(action) or love_change <= -10:
        new_caution = True

    if recovered:
        new_caution = False

    next_turn = turn + 1
    next_stage = advance_stage(stage, next_turn, new_love, new_introduced, action)
    stage_changed = old_stage != next_stage

    new_relationship = get_relationship(new_love, new_introduced, new_caution)
    relation_notice = get_relationship_notice(old_relationship, new_relationship)
    chapter_notice = get_chapter_notice(old_stage, next_stage, scenario_text)

    ai_result = call_ai(
        history,
        memories,
        action,
        love,
        new_love,
        introduced,
        new_introduced,
        player_name,
        old_stage,
        next_stage,
        scenario_text,
        romance_success,
        new_caution,
        stage_changed
    )

    if ai_result is None:
        story, choices = local_story(action, love, new_introduced, player_name, next_stage, scenario_text, romance_success, new_caution)
    else:
        story, choices = ai_result

    new_memories = update_memories(memories, action, story, love_change, next_stage, new_caution)
    new_stats = update_stats(stats, stage, action, love_change, source, recovered)

    if is_end_stage(next_stage):
        final_story = make_ending_story(next_stage, new_love, player_name)
        story_html = format_result_html(final_story, new_love, new_stats, next_turn)
        return (
            story_html,
            format_status_html(new_love, love_change, next_turn, new_introduced, next_stage, True, new_caution),
            format_memory_html(new_memories),
            history,
            new_love,
            love_change,
            new_memories,
            next_turn,
            new_introduced,
            next_stage,
            scenario_text,
            new_stats,
            new_caution,
            snapshot,
            undo_used,
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=(not undo_used and turn > 1)),
            ""
        )

    choices = normalize_choices(choices, next_stage, new_love, new_introduced, scenario_text, new_caution)

    new_history = history + f"""

{player_name}の行動：
{action}

結果：
{story}
"""

    return (
        format_story_html(story, relation_notice=relation_notice, chapter_notice=chapter_notice),
        format_status_html(new_love, love_change, next_turn, new_introduced, next_stage, show_love, new_caution),
        format_memory_html(new_memories),
        new_history,
        new_love,
        love_change,
        new_memories,
        next_turn,
        new_introduced,
        next_stage,
        scenario_text,
        new_stats,
        new_caution,
        snapshot,
        undo_used,
        gr.update(value=choices[0], visible=True),
        gr.update(value=choices[1], visible=True),
        gr.update(value=choices[2], visible=True),
        gr.update(visible=(not undo_used and turn > 1)),
        ""
    )

def make_ending_story(stage, love, player_name):
    if stage == "bad_early":
        return "最初の共同作業で距離感をうまく作れず、美咲は必要最低限のやり取りだけで進めようとした。関係は深まらないまま、早い段階で閉じてしまった。"

    if stage == "bad_distance":
        return "何度か一緒に過ごす機会はあったが、関係は思ったほど近づかなかった。美咲は最後まで礼儀正しかったが、課題が終わると自然に連絡は途切れていった。"

    if stage == "bad_reject":
        return "美咲は少しだけ踏み込もうとしたが、主人公の返事は曖昧だった。彼女は小さく笑って、それ以上は何も求めなかった。"

    if love >= 78:
        return f"課題が終わったあと、美咲は少し迷ってから言った。「{player_name}さんとなら、課題がなくてもまた話してみたいです」二人の関係は、ここからゆっくり続いていく。"

    if love >= 58:
        return "課題は終わったが、二人の会話は自然に続いた。恋人とはまだ言えない。でも、また会う理由はもう課題だけではなかった。"

    return "課題は無事に終わった。美咲とは普通に話せるようになったが、二人の距離は最後まで少しだけ残った。"

def undo(prev_state, undo_used, show_love, player_name):
    if undo_used or not prev_state:
        return tuple(gr.update() for _ in range(20))

    prev_state["stats"]["undo_used"] = True

    choices = get_default_choices(
        prev_state["stage"],
        prev_state["love"],
        prev_state["introduced"],
        prev_state["scenario_text"],
        prev_state["caution"]
    )

    chapter_notice = f"""
<div class="chapter-card">
    <div class="chapter-title">{esc(get_chapter_title(prev_state["stage"], prev_state["scenario_text"]))}</div>
    <div>{esc(get_stage_label(prev_state["stage"]))} に戻りました。</div>
</div>
"""

    return (
        format_story_html(
            "一度だけ時間を巻き戻した。さっきの選択の前に戻った。",
            chapter_notice=chapter_notice
        ),
        format_status_html(prev_state["love"], prev_state["love_change"], prev_state["turn"], prev_state["introduced"], prev_state["stage"], show_love, prev_state["caution"]),
        format_memory_html(prev_state["memories"]),
        prev_state["history"],
        prev_state["love"],
        prev_state["love_change"],
        prev_state["memories"],
        prev_state["turn"],
        prev_state["introduced"],
        prev_state["stage"],
        prev_state["scenario_text"],
        prev_state["stats"],
        prev_state["caution"],
        None,
        True,
        gr.update(value=choices[0], visible=True),
        gr.update(value=choices[1], visible=True),
        gr.update(value=choices[2], visible=True),
        gr.update(visible=False),
        ""
    )



def restart_game(player_name, preset, custom_scenario):
    return start_game(player_name, preset, custom_scenario)


# =========================
# 12. UI
# =========================

with gr.Blocks(title="LLM Interactive Character Simulation") as demo:
    with gr.Group(visible=True) as setup_group:
        gr.HTML('<div class="app-title">LLM Interactive Character Simulation</div>')

        player_name_input = gr.Textbox(
            label="主人公の名前",
            value="山田"
        )

        preset_input = gr.Dropdown(
            label="最初のイベント",
            choices=list(SCENARIO_PRESETS.keys()),
            value="課題発表"
        )

        custom_scenario_input = gr.Textbox(
            label="自分で最初のイベントを入力する",
            placeholder="例：文化祭の喫茶店企画、サッカー部のマネージャー企画など",
            lines=2
        )

        start_btn = gr.Button("開始する", variant="primary")

    with gr.Group(visible=False) as game_group:
        with gr.Row():
            with gr.Column(scale=7):
                story_box = gr.HTML()

            with gr.Column(scale=4):
                status_box = gr.HTML()
                memory_box = gr.HTML()
                show_love_checkbox = gr.Checkbox(
                    label="好感度を表示する",
                    value=False
                )

        custom_input = gr.Textbox(
            label="自由行動入力",
            placeholder="例：静かに作業を進める / 素直に謝る / 今日楽しかったと伝える",
            lines=2
        )

        submit_btn = gr.Button("自由行動で進める", variant="primary")

        with gr.Accordion("おすすめ行動を見る", open=False):
            with gr.Row():
                btn1 = gr.Button("選択肢1")
                btn2 = gr.Button("選択肢2")
                btn3 = gr.Button("選択肢3")

        with gr.Row():
            undo_btn = gr.Button("一度だけ戻る", visible=False)
            reset_btn = gr.Button("最初から始める")

    history_state = gr.State("")
    love_state = gr.State(0)
    love_change_state = gr.State(0)
    memory_state = gr.State([])
    turn_state = gr.State(1)
    introduced_state = gr.State(False)
    stage_state = gr.State("first_event")
    scenario_state = gr.State("")
    stats_state = gr.State(create_initial_stats())
    caution_state = gr.State(False)
    prev_state = gr.State(None)
    undo_used_state = gr.State(False)
    player_name_state = gr.State("山田")

    start_outputs = [
        story_box,
        status_box,
        memory_box,
        history_state,
        love_state,
        love_change_state,
        memory_state,
        turn_state,
        introduced_state,
        stage_state,
        scenario_state,
        stats_state,
        caution_state,
        prev_state,
        undo_used_state,
        player_name_state,
        btn1,
        btn2,
        btn3,
        undo_btn,
        custom_input,
        show_love_checkbox,
        setup_group,
        game_group
    ]

    common_inputs = [
        history_state,
        love_state,
        love_change_state,
        memory_state,
        turn_state,
        introduced_state,
        stage_state,
        scenario_state,
        stats_state,
        caution_state,
        prev_state,
        undo_used_state,
        player_name_state,
        show_love_checkbox
    ]

    common_outputs = [
        story_box,
        status_box,
        memory_box,
        history_state,
        love_state,
        love_change_state,
        memory_state,
        turn_state,
        introduced_state,
        stage_state,
        scenario_state,
        stats_state,
        caution_state,
        prev_state,
        undo_used_state,
        btn1,
        btn2,
        btn3,
        undo_btn,
        custom_input
    ]

    start_btn.click(
        start_game,
        inputs=[player_name_input, preset_input, custom_scenario_input],
        outputs=start_outputs
    )

    submit_btn.click(
        lambda action, history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love:
        proceed(action, history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, "custom"),
        inputs=[custom_input] + common_inputs,
        outputs=common_outputs
    )

    btn1.click(
        lambda history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, action:
        proceed(action, history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, "choice"),
        inputs=common_inputs + [btn1],
        outputs=common_outputs
    )

    btn2.click(
        lambda history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, action:
        proceed(action, history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, "choice"),
        inputs=common_inputs + [btn2],
        outputs=common_outputs
    )

    btn3.click(
        lambda history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, action:
        proceed(action, history, love, love_delta, memories, turn, introduced, stage, scenario, stats, caution, prev, undo_used, player_name, show_love, "choice"),
        inputs=common_inputs + [btn3],
        outputs=common_outputs
    )

    show_love_checkbox.change(
        refresh_status,
        inputs=[
            love_state,
            love_change_state,
            turn_state,
            introduced_state,
            stage_state,
            show_love_checkbox,
            caution_state
        ],
        outputs=[status_box]
    )

    undo_btn.click(
        undo,
        inputs=[prev_state, undo_used_state, show_love_checkbox, player_name_state],
        outputs=common_outputs
    )

    reset_btn.click(
        restart_game,
        inputs=[player_name_state, preset_input, custom_scenario_input],
        outputs=start_outputs
    )


if __name__ == "__main__":
    demo.launch(css=CUSTOM_CSS, server_name="127.0.0.1", share=False)