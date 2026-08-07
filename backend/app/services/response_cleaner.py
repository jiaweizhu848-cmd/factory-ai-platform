import re


EMPTY_FINAL_ANSWER_MESSAGE = "抱歉，这次模型没有返回可展示的最终答案，请重新提问。"
FINAL_MARKER_PATTERN = re.compile(r"^\s*(Final Answer|Final|Answer)\s*:?\s*$", re.IGNORECASE)
PROCESS_HEADING_PATTERN = re.compile(
    r"^\s*(?:"
    r"Here(?:'s| is) a thinking process|"
    r"Thinking Process|"
    r"Internal Monologue|"
    r"Drafting the response|"
    r"Formulate Response \(Internal Draft\)|"
    r"Refining the response"
    r")\s*:?\s*$",
    re.IGNORECASE,
)
NUMBERED_PROCESS_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+\.\s*)?"
    r"(?:Check(?: Against)? Constraints|Final Output Generation|Self-Correction/(?:Refinement|Verification) during thought|Output Generation)"
    r"\b.*$",
    re.IGNORECASE,
)
PROCESS_BOUNDARY_PATTERN = re.compile(
    r"^(?:"
    r"Check(?: Against)? Constraints|"
    r"Check Accuracy(?:\s*(?:&|and)\s*(?:Tone)?)?|"
    r"Final Output Generation|"
    r"Self-Correction/(?:Refinement|Verification) during (?:thought|drafting)|"
    r"Output Generation|"
    r"Meets all constraints|"
    r"Output matches|"
    r"Proceed|"
    r"Done"
    r")"
    r"\b.*$",
    re.IGNORECASE,
)


def clean_assistant_content(content: str) -> str:
    original = content.strip()
    if not original:
        return content

    marker_line_index = _find_final_marker_line(original.splitlines())
    if marker_line_index is not None:
        cleaned = _collapse_blank_lines(
            "\n".join(original.splitlines()[marker_line_index + 1 :]).strip()
        )
        return _fallback_if_empty(cleaned, original)

    lines = []
    skipping_process_block = False
    for line in original.splitlines():
        if _is_process_boundary(line) and any(existing_line.strip() for existing_line in lines):
            break

        if NUMBERED_PROCESS_HEADING_PATTERN.match(line) or _is_process_boundary(line):
            if any(existing_line.strip() for existing_line in lines):
                break
            skipping_process_block = True
            continue

        if PROCESS_HEADING_PATTERN.match(line):
            skipping_process_block = True
            continue

        if skipping_process_block and _looks_like_process_line(line):
            continue

        skipping_process_block = False
        lines.append(line)

    cleaned = _collapse_blank_lines("\n".join(lines).strip())
    return _fallback_if_empty(cleaned, original)


def _looks_like_process_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return bool(re.match(r"^(?:\d+\.|\*|-)\s", stripped))


def _is_process_boundary(line: str) -> bool:
    stripped = line.strip()
    stripped = re.sub(r"^\s*[-*]\s+", "", stripped)
    stripped = stripped.strip("*_` \t")
    stripped = re.sub(r"^\s*\d+\.\s*", "", stripped)
    stripped = stripped.strip("*_` \t")
    stripped = stripped.lstrip("(").strip()
    return bool(PROCESS_BOUNDARY_PATTERN.match(stripped))


def _find_final_marker_line(lines: list[str]) -> int | None:
    marker_line_index = None
    has_process_heading = False

    for index, line in enumerate(lines):
        if PROCESS_HEADING_PATTERN.match(line):
            has_process_heading = True
            continue

        marker_match = FINAL_MARKER_PATTERN.match(line)
        if not marker_match:
            continue

        if has_process_heading:
            marker_line_index = index

    return marker_line_index


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


def _fallback_if_empty(cleaned: str, original: str) -> str:
    if cleaned:
        return cleaned

    if any(
        PROCESS_HEADING_PATTERN.match(line)
        or NUMBERED_PROCESS_HEADING_PATTERN.match(line)
        or _is_process_boundary(line)
        for line in original.splitlines()
    ):
        return EMPTY_FINAL_ANSWER_MESSAGE

    return original
