"""清洗附录领域卡的 item(...) 等特殊格式，只保留原始 MD"""
import re
import os

INPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                     'DH-SRD-1.0-June-26-2025.md.json.md.fixed.md')

with open(INPUT, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到附录起始
appendix_start = None
for i, line in enumerate(lines):
    if re.match(r'^#\s+附录\s*$', line):
        appendix_start = i
        break

if appendix_start is None:
    print("未找到附录章节")
    exit(1)

print(f"附录起始行: {appendix_start + 1}")

# 保留附录前的内容
before = lines[:appendix_start]

# 清理附录内容
cleaned = []
in_item = False

for line in lines[appendix_start:]:
    s = line.rstrip()

    # 跳过纯 item( 行
    if re.match(r'^item\($', s):
        in_item = True
        continue
    # 跳过纯 ) 行（关闭 item block）
    if in_item and re.match(r'^\)$', s):
        in_item = False
        continue
    # 跳过纯 |/ 分隔行
    if re.match(r'^[|/]+$', s):
        continue
    # 跳过纯 - 分隔行（卡片内部）
    if in_item and re.match(r'^-+$', s):
        continue
    # 跳过 rules(
    if re.match(r'^rules\($', s):
        continue
    # 跳过 (( "..."))
    if re.match(r'^\(\(\".*\"\)\)$', s):
        continue
    # 跳过纯 ---
    if re.match(r'^---+$', s):
        continue

    # 处理 ; 元数据行 → **1 级 奥术 法术 回想费用：0**
    if re.match(r'^;\s*', s):
        meta = re.sub(r'^;\s*', '', s)
        meta = re.sub(r',', ' ', meta)
        meta = re.sub(r'\s+', ' ', meta).strip()
        cleaned.append(meta + '\n')
        continue

    # 处理 (("...")) 格式
    s = re.sub(r'\(\(".*?"\)\)', '', s)

    # 行尾残留 )
    if in_item:
        s = re.sub(r'\)$', '', s).strip()
        if s:
            cleaned.append(s + '\n')
    else:
        cleaned.append(line)

# 合并多余空行
text = ''.join(before) + ''.join(cleaned)
text = re.sub(r'\n{4,}', '\n\n\n', text)

with open(INPUT, 'w', encoding='utf-8') as f:
    f.write(text)

print(f"清理完成。总行数: {len(lines)} → {len(text.splitlines())}")
