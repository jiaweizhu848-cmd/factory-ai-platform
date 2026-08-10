from app.services.response_cleaner import clean_assistant_content


def test_clean_assistant_content_removes_leading_chinese_vision_process():
    raw = """用户希望我分析这张PCB图片，统计MLCC和芯片的数量。

**1. 芯片（ICs/Chips）：**
- 左上角：1 个 DIP 封装芯片。
- 中间：2 个 QFP 封装芯片。

**2. MLCC：**
- 估计约 45 个。
"""

    assert clean_assistant_content(raw).startswith("**1. 芯片")
