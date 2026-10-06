"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {"name": "explorer",
         "description": "Delegate when you need to inspect specifications, docstrings or unfamiliar data before deciding on changes.",
         "system_prompt": "Read the supplied files and inspect relevant specifications and edge cases. Do not modify files. Report concrete findings with file paths and any missing information; do not invent task rules."},
        {"name": "implementer",
         "description": "Delegate when a defined code fix or data/log transformation needs implementation and verification.",
         "system_prompt": "Implement the delegated work according to every supplied rule. Read relevant documentation, fix root causes, and verify results with tests or a script. Modify only task outputs and code. Report actual changed files, verification results and remaining uncertainties."},
        {"name": "reviewer",
         "description": "Delegate when completed changes or generated outputs need an independent check against requirements and edge cases.",
         "system_prompt": "Independently inspect the supplied outputs against all delegated requirements. Run appropriate checks and inspect boundary cases. Do not modify files. Report evidence for each issue and distinguish verified results from assumptions."},
    ]
