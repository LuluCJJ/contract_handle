from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "后端两层四块检查逻辑一页图.png"
W, H = 1600, 900
BG = "#FFFFFF"
INK = "#17212F"
TEXT = "#2E3B4B"
MUTED = "#667180"
BLUE = "#1D5FA7"
BLUE_DARK = "#174C86"
BLUE_PALE = "#EEF5FC"
GRAY_PALE = "#F5F7FA"
LINE = "#CDD6E0"
ORANGE = "#C57918"
GREEN = "#227C55"
RED = "#B83A3A"
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


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


def draw_text(draw, xy, text, size=24, fill=TEXT, bold=False, max_width=None, gap=6):
    x, y = xy
    fnt = font(size, bold)
    if max_width is None:
        draw.text((x, y), text, font=fnt, fill=fill)
        return draw.textbbox((x, y), text, font=fnt)[3]
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += size + gap
    return y


def rect(draw, box, fill=BG, outline=LINE, width=2):
    draw.rectangle(box, fill=fill, outline=outline, width=width)


def arrow(draw, x1, y1, x2, y2, color=BLUE):
    draw.line((x1, y1, x2, y2), fill=color, width=4)
    if x2 >= x1:
        draw.polygon([(x2, y2), (x2 - 15, y2 - 8), (x2 - 15, y2 + 8)], fill=color)
    else:
        draw.polygon([(x2, y2), (x2 + 15, y2 - 8), (x2 + 15, y2 + 8)], fill=color)


def chip(draw, x, y, text, fill, color):
    w = int(draw.textlength(text, font=font(18, True))) + 28
    rect(draw, (x, y, x + w, y + 34), fill=fill, outline=LINE, width=1)
    draw_text(draw, (x + 14, y + 6), text, 18, color, True)
    return w


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle((0, 0, W, 12), fill=BLUE_DARK)

draw_text(d, (70, 42), "后端检查逻辑：从单一语义检查升级为两层四块能力", 41, INK, True, 1460)
d.rectangle((70, 108, 150, 114), fill=BLUE)
draw_text(
    d,
    (70, 132),
    "核心判断：先区分事实来源，再决定检查方式；电子流已有信息重在提取与比对，电子流没有的信息重在 SOP 与风险提示。",
    24,
    TEXT,
    True,
    1430,
)
d.line((70, 180, 1530, 180), fill=LINE, width=2)

steps = [
    ("输入材料", "电子流 / 申请表 / 附件 / 证件"),
    ("解析抽取", "文档解析、OCR、结构化要素抽取"),
    ("分层检查", "按事实来源进入两层四块"),
    ("业务报告", "绿灯通过 / 审核人确认 / 发现不一致"),
]
x = 85
for i, (title, body) in enumerate(steps):
    rect(d, (x, 220, x + 315, 320), fill=BLUE_PALE if i == 2 else BG)
    draw_text(d, (x + 20, 242), title, 24, BLUE, True)
    draw_text(d, (x + 20, 280), body, 18, TEXT, False, 265)
    if i < len(steps) - 1:
        arrow(d, x + 325, 270, x + 380, 270)
    x += 380

rect(d, (85, 370, 760, 695), fill="#FBFCFE", outline=BLUE, width=3)
rect(d, (840, 370, 1515, 695), fill="#FBFCFE", outline=ORANGE, width=3)
draw_text(d, (115, 395), "第一层：电子流已有，文档也应承载", 27, BLUE, True)
draw_text(d, (870, 395), "第二层：电子流没有，但文档需要关注", 27, ORANGE, True)


def block(draw, x, y, title, body, color, tag):
    rect(draw, (x, y, x + 610, y + 105), fill=BG, outline=LINE, width=2)
    draw_text(draw, (x + 20, y + 18), title, 24, color, True)
    draw_text(draw, (x + 20, y + 54), body, 18, TEXT, False, 450, 4)
    chip(draw, x + 470, y + 18, tag, BLUE_PALE if color != RED else "#FDECEC", color)


block(
    d,
    115,
    455,
    "A1 精确一致类",
    "账号、姓名、证件号、公司信用代码、介质编号等。AI/OCR 负责提取，代码负责标准化和硬比对。",
    GREEN,
    "代码硬比对",
)
block(
    d,
    115,
    575,
    "A2 语义转换类",
    "开通/注销/权限范围/介质动作等。不是纯映射，而是配置优先、规则约束、AI 兜底。",
    BLUE,
    "语义归一",
)
block(
    d,
    870,
    455,
    "B1 SOP 作业规范类",
    "基于业务经验、错题本和银行模板要求，检查必填项、场景规范、材料完整性。",
    ORANGE,
    "SOP 检查",
)
block(
    d,
    870,
    575,
    "B2 风险条款/关键词类",
    "扫描全权限、所有账户、不限额、长期有效、空白介质、无需注销等敏感表述。",
    RED,
    "风险提示",
)

rect(d, (130, 720, 1470, 790), fill=GRAY_PALE, outline=LINE, width=2)
draw_text(d, (160, 740), "A2 生效机制：", 23, ORANGE, True)
segments = [
    ("业务配置类", "同义词、模板字段、枚举归一", GREEN),
    ("规则 / Prompt 类", "判断口径、风险等级、人工确认标准", BLUE),
    ("工程版本类", "新结构、新算法、跨文档推理、原文定位", RED),
]
x = 320
for i, (title, sub, color) in enumerate(segments):
    draw_text(d, (x, 733), title, 22, color, True)
    draw_text(d, (x, 763), sub, 17, TEXT, False, 300)
    if i < len(segments) - 1:
        arrow(d, x + 310, 756, x + 365, 756, MUTED)
    x += 390

base_y = 822
d.rectangle((70, base_y - 8, 78, base_y + 54), fill=ORANGE)
draw_text(d, (96, base_y), "关键结论：", 25, ORANGE, True)
draw_text(
    d,
    (228, base_y),
    "后端不是让一个大模型包办检查，而是把精确比对、语义归一、SOP 规范和风险条款分开治理，明确业务、产品和技术发力点。",
    24,
    TEXT,
    True,
    1260,
    5,
)
draw_text(d, (70, 872), "Contract Handle AI Pre-audit | 后端两层四块检查逻辑", 16, "#8A96A3")

img.save(OUT)
print(OUT)
