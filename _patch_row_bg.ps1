import os
path = r'D:\A_Claude_MyCodeProject\health-reminder\ui\settings.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """    if THEME.get("bg_start", (102, 126, 234))[0] < 50:
        return \"\"\"
            background: rgba(10,10,15,0.96);
            border: 1px solid rgba(200,200,220,0.06);
            border-radius: 10px; padding: 8px 12px;
        \"\"\"
    else:
        return \"\"\"
            background: rgba(25,25,40,0.96);
            border: 1px solid rgba(200,180,255,0.08);
            border-radius: 10px; padding: 8px 12px;
        \"\"\""""

new = """    if THEME.get("bg_start", (102, 126, 234))[0] < 50:
        return \"\"\"
            background: rgba(180,180,220,0.12);
            border: 1px solid rgba(200,200,220,0.1);
            border-radius: 10px; padding: 8px 12px;
        \"\"\"
    else:
        return \"\"\"
            background: rgba(200,180,255,0.12);
            border: 1px solid rgba(200,180,255,0.15);
            border-radius: 10px; padding: 8px 12px;
        \"\"\""""

if old not in content:
    print("ERROR: old block not found")
else:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("patched ok")
