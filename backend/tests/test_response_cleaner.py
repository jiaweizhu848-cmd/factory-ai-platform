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


def test_clean_assistant_content_handles_here_is_a_thinking_process_wrapper():
    raw = """Here's a thinking process:

1. Analyze User Input:

- User asks: 你是谁，你能帮我做什么？
- Language: Chinese

2. Check Constraints:

- System prompt asks for final answer only.

3. Formulate Response (Internal Draft):

- Identity: 我是 Factory AI。

我是 Factory AI，可以帮助你进行工厂场景下的信息查询、数据分析、文档整理和问题排查。
"""

    assert (
        clean_assistant_content(raw)
        == "我是 Factory AI，可以帮助你进行工厂场景下的信息查询、数据分析、文档整理和问题排查。"
    )


def test_clean_assistant_content_truncates_numbered_process_sections_after_answer():
    raw = """I am Factory AI. I can answer questions and help with writing, coding, data analysis, reasoning, translation, and creative generation.

3. Check Constraints:

- Direct answer? Yes.
- Only final answer? Yes.

4. Final Output Generation: (Matches the draft)

I am Factory AI. I can answer questions.

- Self-Correction/Refinement during thought: The prompt says final answer only.
"""

    assert (
        clean_assistant_content(raw)
        == "I am Factory AI. I can answer questions and help with writing, coding, data analysis, reasoning, translation, and creative generation."
    )


def test_clean_assistant_content_truncates_check_against_constraints_after_answer():
    raw = """I am Factory AI, an intelligent assistant. I can help answer questions, draft text, code, analyze data, and provide practical support.

4. Check Against Constraints:

* Direct answer? Yes.
* No thinking process/reasoning? Yes.
* In Chinese? Yes.

5. Final Output Generation: (Matches the draft)

"I am Factory AI, an intelligent assistant."

(Self-Correction/Verification during thought: The prompt says final answer only.)
"""

    assert (
        clean_assistant_content(raw)
        == "I am Factory AI, an intelligent assistant. I can help answer questions, draft text, code, analyze data, and provide practical support."
    )


def test_clean_assistant_content_truncates_trailing_self_check_bullets_after_answer():
    raw = """I am Factory AI. I can answer questions, provide information, help with writing and coding, analyze data, and translate.

* Meets all constraints. Ready.
* Output matches exactly.
* Proceed.
* Self-Correction/Verification during thought: The prompt says final answer only.
* Output matches response.
* Done.
* Output Generation (matches the final refined version)
"I am Factory AI. I can answer questions."
"""

    assert (
        clean_assistant_content(raw)
        == "I am Factory AI. I can answer questions, provide information, help with writing and coding, analyze data, and translate."
    )


def test_clean_assistant_content_truncates_markdown_bold_process_sections_after_answer():
    raw = """I am Factory AI. I can answer questions and provide support.

**4. Check Against Constraints:**

* Direct answer? Yes.
* No thinking process/reasoning? Yes.

**5. Final Output Generation:** (Matches the drafted response)

"I am Factory AI. I can answer questions and provide support."

(Self-Correction/Verification during drafting: The prompt says final answer only.)
"""

    assert (
        clean_assistant_content(raw)
        == "I am Factory AI. I can answer questions and provide support."
    )


def test_clean_assistant_content_truncates_accuracy_and_tone_sections_after_answer():
    raw = """Hi Michael,

Please add the isolated IP segment to the firewall allowlist.

4. Check Accuracy & Tone:

* Matches original meaning precisely.
* Technical.
"""

    assert (
        clean_assistant_content(raw)
        == "Hi Michael,\n\nPlease add the isolated IP segment to the firewall allowlist."
    )


def test_clean_assistant_content_truncates_partial_accuracy_heading_after_stop():
    raw = """Hi Michael,

Please add the isolated IP segment to the firewall allowlist.

4. **Check Accuracy &
"""

    assert (
        clean_assistant_content(raw)
        == "Hi Michael,\n\nPlease add the isolated IP segment to the firewall allowlist."
    )
