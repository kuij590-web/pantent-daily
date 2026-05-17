#!/usr/bin/env python3
"""Test the new template - standalone, no imports from the project"""
import sys
import os

# Read and exec the wechat_draft file directly
filepath = os.path.join(os.path.dirname(__file__), "src", "publisher", "wechat_draft.py")
with open(filepath, "r", encoding="utf-8") as f:
    source = f.read()

# Remove all pyc files
import subprocess
subprocess.run(["find", os.path.dirname(__file__), "-name", "*.pyc", "-delete"], capture_output=True)

# Execute the source to define the function
exec(source)

articles_by_category = {
    "政策动态": [("<p>test</p>", "")],
}
html = generate_daily_digest_html(
    date_str="2026-05-10",
    articles_by_category=articles_by_category,
)

markers = [
    ("large_title_26px", "font-size:26px" in html),
    ("apple_gray_86868b", "#86868b" in html),
    ("apple_black_1d1d1f", "#1d1d1f" in html),
    ("nav_tags_pill", "padding:4px 12px" in html),
    ("disclaimer", "免责声明" in html),
]

all_ok = True
for name, ok in markers:
    status = "OK" if ok else "FAIL"
    if not ok:
        all_ok = False
    print(f"  [{status}] {name}")

print(f"\nPreview:\n{html[:500]}")
sys.exit(0 if all_ok else 1)
