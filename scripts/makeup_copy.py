# scripts/makeup_copy.py
# 从 DaggerHeart_CN/lib/makeup.py 移植的核心格式化函数
# 用于对 paratranz 译文做后处理

import re


def remove_image_filename(markdown_text):
    """删除 ![](_page_0_Picture_2.jpeg) 格式的图像链接"""
    return re.sub(r'!\[\]\(_page.*?\)', '', markdown_text)


def remove_paratranz_tags(markdown_text):
    """删除 ((++中文)) 和 ((中文)) 类 paratranz 标记"""
    text = re.sub(r'\(\(\+\+[^)]*\)\)', '', markdown_text)
    text = re.sub(r'\(\([^)]*\)\)', '', text)
    return text


def remove_span(markdown_text):
    """删除 <span.*></span> 标签"""
    return re.sub(r'<span.*?></span>', '', markdown_text, flags=re.DOTALL)


def format_resource_phrases_fn(markdown_text):
    """加粗中文资源短语: 获得 1 希望点 → **获得 1 希望点**"""
    verbs = r'恢复|回复|标记|清除|移除|获得|花费|消耗|失去|承受'
    resources = r'(?:生命|希望|压力|恐惧|绝望|恩宠|专注)(?:点)?|护甲(?:槽)?'
    amount = r'\d{1,2}d\d{1,2}|\d{1,2}|[一二三四五六]'

    # 第一遍：修复已拆分加粗的情况
    text = re.sub(rf'({verbs})\s*\*\*\s*({amount})\s*\*\*\s*\*\*\s*({resources})\s*\*\*', r'**\1 \2 \3**', markdown_text)
    text = re.sub(rf'({verbs})\s*\*\*\s*({amount})\s*\*\*\s*({resources})', r'**\1 \2 \3**', text)

    # 第二遍：标准模式
    pattern = rf'\*{{0,2}}\s*({verbs})\s*({amount})\s*(?:点|个)?\s*({resources})\s*\*{{0,2}}'

    def replace_match(match):
        action = match.group(1)
        amount_str = match.group(2)
        resource_core = match.group(3)

        if action == "回复":
            action = "恢复"
        elif action == "移除":
            action = "清除"
        elif action == "消耗":
            action = "花费"

        if resource_core == "绝望":
            resource_core = "恐惧"

        num_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6'}
        amount = num_map.get(amount_str, amount_str)

        if "护甲" in resource_core:
            resource_full = resource_core if resource_core.endswith("槽") else resource_core + "槽"
        elif not resource_core.endswith("点"):
            resource_full = resource_core + "点"
        else:
            resource_full = resource_core

        return f"**{action} {amount} {resource_full}**"

    return re.sub(pattern, replace_match, text)


def add_space_around_italics_fn(markdown_text):
    """中文斜体前后加空格"""
    pattern = r'(?<=[一-龥,.，。])\*{1}[一-龥]{1,5}\*{1}(?=[一-龥,.，。])'
    return re.sub(pattern, lambda m: f" {m.group(0)} ", markdown_text)


def simplify_markdown_links_fn(markdown_text):
    """简化为纯文本（移除链接标记）"""
    if markdown_text.startswith("![]"):
        return markdown_text
    pattern = r'\[([^\]]+)\]\([^\)]*\)'
    return re.sub(pattern, lambda match: match.group(1), markdown_text)


def replace_pc_gm_fn(markdown_text):
    """PC/GM → 玩家角色/游戏主持人"""
    text = re.sub(r'(?<![A-Za-z\(（])PC(?![A-Za-z\)）])', '玩家角色', markdown_text)
    text = re.sub(r'(?<![A-Za-z\(（])GM(?![A-Za-z\)）])', '游戏主持人', text)
    return text


def bold_numbers_and_dice_fn(markdown_text):
    """在中文上下文中加粗数字和骰子表达式"""
    chinese_chars = r'一-龥'
    find_pattern = r'([-−+]?)\s*(\d*d\d+(?:[-−+]\s*\d+)?|\d+)'

    parts = markdown_text.split('**')
    new_parts = []
    for i, part in enumerate(parts):
        if i % 2 != 0:
            new_parts.append(part)
            continue

        new_sub_part = ""
        last_end = 0
        for match in re.finditer(find_pattern, part):
            new_sub_part += part[last_end:match.start()]
            start, end = match.start(), match.end()
            pre_char = part[start - 1] if start > 0 else ''
            post_char = part[end] if end < len(part) else ''

            if (pre_char == '(' and post_char == ')') or \
               (pre_char == '（' and post_char == '）'):
                new_sub_part += match.group(0)
                last_end = end
                continue

            is_pre_chinese = bool(re.search(f'[{chinese_chars}]', pre_char))
            is_post_chinese = bool(re.search(f'[{chinese_chars}]', post_char))

            if is_pre_chinese or is_post_chinese:
                cleaned = re.sub(r'\s', '', match.group(0))
                pre_space = '' if pre_char.isspace() or not pre_char else ' '
                post_space = '' if post_char.isspace() or not post_char else ' '
                new_sub_part += f"{pre_space}**{cleaned}**{post_space}"
            else:
                new_sub_part += match.group(0)
            last_end = end

        new_sub_part += part[last_end:]
        new_parts.append(new_sub_part)

    return '**'.join(new_parts)


# Makeup 函数列表（按顺序应用）
MAKEUP_FUNCS = [
    remove_image_filename,
    remove_paratranz_tags,
    remove_span,
    format_resource_phrases_fn,
    bold_numbers_and_dice_fn,
    add_space_around_italics_fn,
    simplify_markdown_links_fn,
    replace_pc_gm_fn,
]


def apply_makeup(text):
    """对文本依次应用所有 makeup 函数"""
    paragraphs = text.split('\n\n')
    processed = []
    for para in paragraphs:
        p = para
        for func in MAKEUP_FUNCS:
            p = func(p)
        processed.append(p)
    return '\n\n'.join(processed)
