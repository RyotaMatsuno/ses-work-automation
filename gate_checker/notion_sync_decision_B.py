#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notion SES Wiki 縺ｫ隲也せB遒ｺ螳壹ｒ霑ｽ險・""
import sys, os, requests, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# .env隱ｭ縺ｿ霎ｼ縺ｿ
from dotenv import load_dotenv
load_dotenv("C:/Users/ma_py/OneDrive/繝・せ繧ｯ繝医ャ繝・ses_work/config/.env")

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
WIKI_BLOCK_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def heading(text, level=2):
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }

def para(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }

def bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }

children = [
    heading("2026-06-16 隲也せB遒ｺ螳・ Cursor邨ｱ蜷域姶逡･ = 譯・(迴ｾ迥ｶ邯ｭ謖・", 2),
    para("縲占レ譎ｯ縲大燕繝√Ε繝・ヨ縺ｧ縺ｯ縲擦ursor Free Plan + API繧ｭ繝ｼ逶ｴ謖ｿ縺励上ｒ蜑肴署縺ｫ譯・/B/C繧呈ｯ碑ｼ・＠縺ｦ縺・◆縲よ悽譌･Cursor險ｭ螳啅I縺ｮ繧ｹ繧ｯ繧ｷ繝ｧ縺ｧ蜑肴署縺悟ｴｩ繧後◆縺溘ａ縲∝・隧穂ｾ｡繧貞ｮ滓命縲・),
    heading("蛻､譏弱＠縺滉ｺ句ｮ・繧ｹ繧ｯ繧ｷ繝ｧ螳滓ｸｬ)", 3),
    bullet("Current Plan: Pro $20/mo (繝ｪ繧ｻ繝・ヨ譌･ 7/9)"),
    bullet("Included in Pro 蜷ｫ譛画棧豸郁ｲｻ邇・ Total 6% (7譌･邨碁℃譎らせ)縲らｷ壼ｽ｢謠帷ｮ励〒譛域忰 ~26% 豸郁ｲｻ隕玖ｾｼ縺ｿ縲・4% 菴呵｣輔≠繧・),
    bullet("蜀・ｨｳ: 8% Auto / 0% API used 竊・Anthropic Key ON 縺縺悟ｮ滄圀縺ｫ縺ｯAPI邨檎罰縺ｮ隱ｲ驥代ぞ繝ｭ"),
    bullet("On-Demand Spending: Disabled (雜・℃譎り・蜍戊ｪｲ驥前FF縲ゅΜ繧ｹ繧ｯ驕ｮ譁ｭ貂医∩)"),
    bullet("UPGRADE AVAILABLE: Pro+ $60/mo (3蛟肴棧)縺瑚｡ｨ遉ｺ縺輔ｌ繧九′迴ｾ迥ｶ縺ｧ縺ｯ荳崎ｦ・),
    heading("蛻､譁ｭ", 3),
    para("譯・ (Cursor Pro $20/譛・邯咏ｶ・ 縺ｧ遒ｺ螳壹よ怦繧ｳ繧ｹ繝亥崋螳・$20縲、PI隱ｲ驥代↑縺励・),
    bullet("譯・ (Sonnet 4.6 + gpt-5.3-codex 菴ｵ逕ｨ): codex蠕馴㍼蛻・′荵励ｋ縺溘ａ蠅鈴｡阪ら樟迥ｶ縺ｧ譫菴吶▲縺ｦ繧九・縺ｧ荳崎ｦ・),
    bullet("譯・ (Cursor Pro 隗｣邏・+ 蜈ｨGPT API): Pro $20 蜷ｫ譛画棧繧呈昏縺ｦ繧区錐縲ゆｸ崎ｦ・),
    heading("莉倬囂繧｢繧ｯ繧ｷ繝ｧ繝ｳ", 3),
    bullet("謗ｨ螂ｨ(莉ｻ諢・: Cursor險ｭ螳壹・ Anthropic API Key 繧・OFF 縺ｫ縺吶ｋ縲ら樟迥ｶ0%縺ｪ縺ｮ縺ｧ讖溯・蠖ｱ髻ｿ繧ｼ繝ｭ縲１ro雜・℃譎ゅ・閾ｪ蜍柊PI隱ｲ驥代Μ繧ｹ繧ｯ繧呈賜髯､縺励＾n-Demand Disabled 縺ｨ莠碁㍾髦ｲ蠕｡縺ｫ"),
    bullet("Pro+/Ultra 繧｢繝・・繧ｰ繝ｬ繝ｼ繝・ 荳崎ｦ・),
    bullet("View All Models 縺ｧ gpt-5.3-codex 謗｢縺・ 荳崎ｦ・邨ｱ蜷郁・菴薙＠縺ｪ縺・◆繧・"),
    heading("蜑阪メ繝｣繝・ヨ遒ｺ螳壻ｺ矩・∈縺ｮ蠖ｱ髻ｿ", 3),
    para("隲也せA/C/D 縺ｯ gate_checker邉ｻ(OpenAI API逶ｴ謗･蜻ｼ蜃ｺ)縺ｧ縺ゅｊ Cursor 縺ｨ縺ｯ迢ｬ遶狗ｳｻ邨ｱ縲よ悽譌･縺ｮ隲也せB螟画峩縺ｫ繧医ｋ蠖ｱ髻ｿ縺ｪ縺励ょ燕繝√Ε繝・ヨ遒ｺ螳壹・螳溯｣・ｨ育判(繝輔ぉ繝ｼ繧ｺ蛻･繝｢繝・Ν蜑ｲ謖ｯ繝ｻDAILY_CALL_LIMIT谿ｵ髫主､繝ｻ莠梧ｬ｡螢∵遠縺｡蛻・屬繧｢繝励Ο繝ｼ繝√・螳牙・陬・ｽｮ4縺､繝ｭ繝ｼ繝峨・繝・・)縺ｯ縺昴・縺ｾ縺ｾ騾ｲ陦悟庄閭ｽ縲・),
    heading("螢∵遠縺｡螳滓命譛臥┌", 3),
    para("螢∵遠縺｡荳崎ｦ√→蛻､譁ｭ縲ら炊逕ｱ: 繧ｹ繧ｯ繧ｷ繝ｧ螳滓ｸｬ蛟､縺ｧ謨ｰ蟄励′荳諢上↓豎ｺ縺ｾ繧翫∵耳隲紋ｽ吝慍縺後↑縺・豸郁ｲｻ邇・%, API 0%, On-Demand Disabled)縲ゅず繝ｧ繝悶ぜ縺ｮ蜿､縺・衍隴・Free Plan蜑肴署)縺悟ｴｩ繧後◆迸ｬ髢薙↓ Cursor 蜈ｬ蠑・pricing 縺ｨ譚ｾ驥散I縺ｧ蜀阪・繝ｼ繧ｹ繝ｩ繧､繝ｳ蛹匁ｸ医∩縲・),
    heading("memory譖ｴ譁ｰ", 3),
    para("memory #18 縺ｨ縺励※ Pro $20/譛医・遒ｺ螳壽ュ蝣ｱ繧定ｨ倬鹸貂医∩縲ょ燕縺ｮFree Plan陦ｨ險倥・蜿､縺・ュ蝣ｱ謇ｱ縺・・),
]

# Notion 繝悶Ο繝・け霑ｽ蜉 (1蝗槭・繝ｪ繧ｯ繧ｨ繧ｹ繝医・100繝悶Ο繝・け荳企剞縺ｪ縺ｮ縺ｧ蛻・牡荳崎ｦ・
resp = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_BLOCK_ID}/children",
    headers=headers,
    json={"children": children},
    timeout=30,
)

if resp.status_code == 200:
    data = resp.json()
    print(f"笨・Notion SES Wiki 霑ｽ險俶・蜉・)
    print(f"   霑ｽ蜉繝悶Ο繝・け謨ｰ: {len(data.get('results', []))}")
else:
    print(f"笶・Notion API error: {resp.status_code}")
    print(resp.text[:1000])
