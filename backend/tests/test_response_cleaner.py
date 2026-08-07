from app.services.response_cleaner import clean_assistant_content


def test_clean_assistant_content_extracts_final_answer():
    raw = """Thinking Process:
1. Analyze user input.
2. Draft answer.

Final Answer:
你好，我可以帮助你分析工厂数据。
"""

    assert clean_assistant_content(raw) == "你好，我可以帮助你分析工厂数据。"


def test_clean_assistant_content_removes_common_process_headings():
    raw = """Thinking Process:

Internal Monologue:

Drafting the response:

Refining the response:

可以，我会直接给出结论。
"""

    assert clean_assistant_content(raw) == "可以，我会直接给出结论。"


def test_clean_assistant_content_preserves_normal_answer():
    raw = """可以按下面步骤操作：

1. 启动 vLLM
2. 启动后端
3. 启动前端
"""

    assert clean_assistant_content(raw) == raw.strip()


def test_clean_assistant_content_falls_back_when_cleaned_empty():
    raw = "Thinking Process:"

    assert clean_assistant_content(raw) == raw


def test_clean_assistant_content_extracts_final_answer_without_colon():
    raw = """Thinking Process:
1. Analyze user input.

Final Answer
可以，我会给出最终结论。
"""

    assert clean_assistant_content(raw) == "可以，我会给出最终结论。"


def test_clean_assistant_content_extracts_final_or_answer_with_process_context():
    final_raw = """Thinking Process:
I should reason internally first.

Final:
可以，这是最终回答。
"""
    answer_raw = """Internal Monologue:
Draft before answer.

Answer:
可以，这是答案。
"""

    assert clean_assistant_content(final_raw) == "可以，这是最终回答。"
    assert clean_assistant_content(answer_raw) == "可以，这是答案。"


def test_clean_assistant_content_preserves_normal_answer_example():
    raw = """可以参考这个格式：

Question: 如何启动？
Answer: 先启动后端，再启动前端。
"""

    assert clean_assistant_content(raw) == raw.strip()


def test_clean_assistant_content_collapses_blank_lines_after_final_marker():
    raw = """Thinking Process:
1. Analyze.

Final Answer:


可以，结论如下。



下一步启动后端。
"""

    assert clean_assistant_content(raw) == "可以，结论如下。\n\n下一步启动后端。"


def test_clean_assistant_content_preserves_process_prose_without_final_marker():
    raw = """Thinking Process:
I should analyze the request first.
可以，结论如下。
"""

    assert clean_assistant_content(raw) == "I should analyze the request first.\n可以，结论如下。"


def test_clean_assistant_content_preserves_final_answer_example_without_process_context():
    raw = """请按这个格式输出：

Final Answer:
你的答案
"""

    assert clean_assistant_content(raw) == raw.strip()


def test_clean_assistant_content_preserves_final_answer_without_process_context():
    raw = """Final Answer:
Restart the backend service.
"""

    assert clean_assistant_content(raw) == raw.strip()


def test_clean_assistant_content_extracts_english_answer_after_final_marker_with_process_context():
    raw = """Thinking Process:
I should analyze first.
Final Answer:
Restart the backend service.
"""

    assert clean_assistant_content(raw) == "Restart the backend service."


def test_clean_assistant_content_removes_process_heading_and_numbered_lines_before_english_answer():
    raw = """Thinking Process:
1. Analyze.
Restart the backend service.
"""

    assert clean_assistant_content(raw) == "Restart the backend service."
