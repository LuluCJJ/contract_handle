from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "作业规范与摘要风险一页图.png"
W, H = 1600, 900
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"

BG = "#FFFFFF"
INK = "#162033"
TEXT = "#2E3B4B"
MUTED = "#6B7280"
BLUE = "#1D5FA7"
BLUE_DARK = "#173F73"
BLUE_PALE = "#EEF5FC"
GREEN = "#18794E"
GREEN_PALE = "#ECFDF3"
ORANGE = "#B76A00"
ORANGE_PALE = "#FFF7E6"
RED = "#B42318"
RED_PALE = "#FEF3F2"
GRAY = "#F5F7FA"
LINE = "#D7DEE8"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def wrap(draw, text, fnt, max_width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            trial = cur + ch
            if draw.textlength(trial, font=fnt) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def text(draw, xy, value, size=24, fill=TEXT, bold=False, max_width=None, gap=6):
    x, y = xy
    fnt = font(size, bold)
    if max_width is None:
        draw.text((x, y), value, font=fnt, fill=fill)
        return draw.textbbox((x, y), value, font=fnt)[3]
    for line in wrap(draw, value, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += size + gap
    return y


def box(draw, rect, fill=BG, outline=LINE, width=2, radius=18):
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, x1, y1, x2, y2, color=BLUE):
    draw.line((x1, y1, x2, y2), fill=color, width=4)
    draw.polygon([(x2, y2), (x2 - 15, y2 - 8), (x2 - 15, y2 + 8)], fill=color)


def chip(draw, x, y, label, fill, color):
    fnt = font(18, True)
    w = int(draw.textlength(label, font=fnt)) + 28
    draw.rounded_rectangle((x, y, x + w, y + 34), radius=17, fill=fill, outline=LINE, width=1)
    text(draw, (x + 14, y + 5), label, 18, color, True)
    return w


def card(draw, x, y, w, h, title, body, color, fill):
    box(draw, (x, y, x + w, y + h), fill=fill, outline=color, width=2, radius=18)
    text(draw, (x + 22, y + 18), title, 25, color, True, w - 44)
    text(draw, (x + 22, y + 60), body, 20, TEXT, False, w - 44, gap=8)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle((0, 0, W, 12), fill=BLUE_DARK)

text(d, (64, 38), "作业规范与摘要风险：不是让 AI 找茬，而是让材料可被正确办理", 39, INK, True, 1480)
text(d, (66, 96), "面向银行网银权限申请/变更/注销材料：先结构化事实，再做有限风险判断，最后给出原文依据和审核建议。", 23, MUTED, False, 1440)

# Left pipeline
box(d, (56, 148, 1544, 286), fill=GRAY, outline=LINE, radius=22)
steps = [
    ("1 文档解析", "表格/正文/OCR"),
    ("2 事实抽取", "人/账户/权限/介质"),
    ("3 单文档摘要", "这份文件说了什么"),
    ("4 风险 Playbook", "按业务规则有限判断"),
    ("5 证据回看", "原文片段+审核建议"),
]
x = 86
for i, (title, sub) in enumerate(steps):
    box(d, (x, 176, x + 235, 258), fill=BG, outline=BLUE if i < 3 else ORANGE, radius=16)
    text(d, (x + 18, 190), title, 23, BLUE_DARK if i < 3 else ORANGE, True)
    text(d, (x + 18, 224), sub, 18, MUTED, False)
    if i < len(steps) - 1:
        arrow(d, x + 244, 217, x + 285, 217)
    x += 286

# Three risk layers
text(d, (64, 322), "三类可和业务确认的摘要风险", 30, INK, True)
card(
    d,
    64,
    374,
    455,
    255,
    "A. 填写规范风险",
    "关注材料是否填得完整、格式合理、没有前后矛盾。\n例：必填为空、日期/证件号异常、勾选注销但正文写新增、限额缺币种。",
    BLUE,
    BLUE_PALE,
)
card(
    d,
    572,
    374,
    455,
    255,
    "B. 多文档一致性风险",
    "关注一套材料内部是否讲的是同一件事。\n例：公司/法人/账号不一致、主表开通但附件撤销、两名操作员只上传一张证件。",
    ORANGE,
    ORANGE_PALE,
)
card(
    d,
    1080,
    374,
    455,
    255,
    "C. 业务实质风险",
    "关注材料是否可能让银行误办、错办或超范围办理。\n例：制单员申请支付+授权、注销未说明介质回收、授权书写全部事项。",
    RED,
    RED_PALE,
)

# Bottom output
box(d, (64, 674, 1536, 820), fill=BG, outline=LINE, radius=22)
text(d, (92, 700), "输出给审核审批人的不是技术项，而是可处理事项", 29, INK, True)
cx = 92
cx += chip(d, cx, 754, "风险类型", BLUE_PALE, BLUE_DARK) + 14
cx += chip(d, cx, 754, "业务解释", GREEN_PALE, GREEN) + 14
cx += chip(d, cx, 754, "原文依据", ORANGE_PALE, ORANGE) + 14
cx += chip(d, cx, 754, "建议动作", RED_PALE, RED) + 14
text(
    d,
    (780, 744),
    "示例：电子流为查询权限，摘要发现“查询、转账”和“全部事项” → 提示权限可能超出本次业务，需要审核人确认。",
    22,
    TEXT,
    False,
    700,
)

text(d, (64, 850), "架构口径：LLM 负责抽取与摘要，规则/Playbook 负责稳定判断；所有风险必须带证据，人保留最终判断。", 21, MUTED, False, 1460)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(OUT)
