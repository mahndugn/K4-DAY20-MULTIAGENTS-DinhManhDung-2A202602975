"""Build the final report only after all 18 primary runs are valid."""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from dotenv import dotenv_values

from lab.compare import build_table, load_runs
from lab.tasks import list_tasks


def main():
    runs = load_runs()
    expected = {(c, t.id) for c in ("baseline", "subagents", "skills-auto") for t in list_tasks()}
    assert {(r["condition"], r["task"]) for r in runs} == expected, "Primary results are incomplete"
    assert all(not r.get("skills_modified") and (not r.get("error") or r["error"].startswith("GraphRecursionError:")) for r in runs), "Infrastructure error or modified skills"
    model_names = {r["model"] for r in runs}
    assert len(model_names) == 1, "Mixed models in primary comparison"
    model_name = next(iter(model_names))
    assert all(r["recursion_limit"] == 100 for r in runs), "Mixed limits"
    recursion_failures = [f"{r['condition']}/{r['task']}" for r in runs if r.get("error")]
    verify = subprocess.run(["python", "scripts/verify_freeze.py"], capture_output=True, text=True, check=True).stdout
    breakdown = subprocess.run(["python", "scripts/check_breakdown.py"], capture_output=True, text=True, check=True).stdout
    subprocess.run(["python", "report/summarize.py"], capture_output=True, text=True, check=True)
    Path("report/verification.txt").write_text(verify + "\n" + breakdown, encoding="utf-8")
    Path("report/check-breakdown-current.txt").write_text(breakdown, encoding="utf-8")
    table = build_table(runs)
    cells = {(r["condition"], r["task"]): r for r in runs}
    conditions = ("baseline", "subagents", "skills-auto")
    groups = {(c, role): [r for r in runs if r["condition"] == c and r["role"] == role]
              for c in conditions for role in ("learn", "eval")}
    scores = {k: mean(r["score"] for r in rs) for k, rs in groups.items()}
    tokens = {k: mean(r["tokens"]["total"] for r in rs) for k, rs in groups.items()}
    all_tokens = {c: mean(r["tokens"]["total"] for r in runs if r["condition"] == c) for c in conditions}
    all_scores = {c: mean(r["score"] for r in runs if r["condition"] == c) for c in conditions}
    original = Path("report/REPORT.md").read_text(encoding="utf-8")
    preregistration = subprocess.check_output(["git", "show", "c14d5eb:report/REPORT.md"], text=True)
    hypotheses = preregistration.split("## 2.", 1)[1].split("## 3.", 1)[0]
    hypotheses = "## 2." + hypotheses.replace("sẽ được chốt", "đã được chốt")
    freeze = subprocess.check_output(["git", "rev-parse", "freeze"], text=True).strip()
    count = len(list(Path("results").rglob("run.json")))
    taxonomy = ["| Tác vụ | Check thất bại | Nhóm | Bằng chứng detail |", "|---|---|---|---|"]
    for r in groups[("baseline", "learn")]:
        for c in r["checks"]:
            if not c["passed"]:
                taxonomy.append(f"| {r['task']} | {c['name']} | {'E' if c['name'].startswith('rule_') else 'G'} | {c['detail'].replace('|', '/')} |")
    delegation = ["| Tác vụ | Calls task | Tên quan sát trong trace | Token | Giây |", "|---|---:|---|---:|---:|"]
    for r in [cells[("subagents", t.id)] for t in list_tasks()]:
        trace = Path(f"results/subagents/{r['task']}/trace.md").read_text(encoding="utf-8")
        names = re.findall(r'"subagent_type"\s*:\s*"([^"]+)"', trace)
        delegation.append(f"| {r['task']} | {r['subagent_calls']} | {', '.join(names) or 'Không quan sát được tên'} | {r['tokens']['total']:,} | {r['seconds']} |")
    skills = ["| Tác vụ | Skills read | Điểm | Quy ước còn thất bại |", "|---|---:|---|---|"]
    improved = []
    for t in list_tasks():
        r = cells[("skills-auto", t.id)]
        b = {c["name"]: c["passed"] for c in cells[("baseline", t.id)]["checks"]}
        failed = [c["name"] for c in r["checks"] if c["name"].startswith("rule_") and not c["passed"]]
        improved.extend(f"{t.id}/{c['name']}" for c in r["checks"] if c["name"].startswith("rule_") and c["passed"] and not b.get(c["name"]))
        skills.append(f"| {t.id} | {r['skills_read']} | {r['passed']}/{r['total']} | {', '.join(failed) or 'Không'} |")
    noise = ["| Tác vụ học | Lặp sau freeze | Bộ chính | Δ điểm | Token lặp / chính | Skill đọc lặp / chính | Lỗi lượt lặp |", "|---|---:|---:|---:|---:|---:|---|"]
    noise_deltas = []
    for t in list_tasks("learn"):
        dev = json.loads(Path(f"results/repeat-learning/skills-auto/{t.id}/run.json").read_text(encoding="utf-8"))
        assert dev["model"] == model_name and dev["recursion_limit"] == 100
        r = cells[("skills-auto", t.id)]
        delta = r["score"] - dev["score"]
        noise_deltas.append(abs(delta))
        noise.append(f"| {t.id} | {dev['passed']}/{dev['total']} | {r['passed']}/{r['total']} | {delta:+.3f} | {dev['tokens']['total']:,} / {r['tokens']['total']:,} | {dev['skills_read']} / {r['skills_read']} | {dev['error'].split(':', 1)[0] if dev.get('error') else 'Không'} |")
    new_rules = [("code-eval", "rule_version_bump"), ("data-eval", "rule_sorted_keys_format"), ("logs-eval", "rule_source_line")]
    novel = ["| Quy ước mới trên eval | baseline | subagents | skills-auto |", "|---|---|---|---|"]
    for tid, name in new_rules:
        values = [next(c["passed"] for c in cells[(cond, tid)]["checks"] if c["name"] == name) for cond in conditions]
        novel.append(f"| {tid}/{name} | " + " | ".join("Đạt" if v else "Không đạt" for v in values) + " |")
    efficiency = ["| Điều kiện | Token trung bình (6 task) | Điểm TB / 100.000 token |", "|---|---:|---:|"]
    for c in conditions:
        efficiency.append(f"| {c} | {all_tokens[c]:,.0f} | {all_scores[c] * 100000 / all_tokens[c]:.3f} |")
    learning_delta = scores[("skills-auto", "learn")] - scores[("baseline", "learn")]
    eval_delta = scores[("skills-auto", "eval")] - scores[("baseline", "eval")]
    sub_delta = scores[("subagents", "eval")] - scores[("baseline", "eval")]
    sub_ratio = tokens[("subagents", "eval")] / tokens[("baseline", "eval")]
    gap = scores[("skills-auto", "learn")] - scores[("skills-auto", "eval")]
    h1 = abs(sub_delta) < .10 and sub_ratio >= 1.20
    h2 = eval_delta >= .10
    h3 = gap >= .05
    appendix = original.split("### Mở rộng 6c:", 1)[1] if "### Mở rộng 6c:" in original else ""
    def join(rows):
        return "\n".join(rows)
    report = f"""# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Đinh Mạnh Dũng | 2A202602975 | Harness, thí nghiệm, phân tích với hỗ trợ Codex; thông tin suy ra từ tên repo. |

Bộ so sánh mới dùng duy nhất `{model_name}`, LAB_TEMPERATURE=0, recursion_limit=100 cho cả 18 lượt. Curator và giai đoạn học gốc dùng Gemini 3.5 Flash-Lite; model này hết quota nên người dùng yêu cầu đổi model miễn phí và chạy lại toàn bộ so sánh. Không sinh lại skill sau khi đã xem eval. Deep Agents 0.7.21, Python 3.12.15, Docker Linux trên Windows. 32 test ngoại tuyến đạt; 6 test runner đạt sau bổ sung metadata. Phiên bản thư viện ở requirements-lock.txt. Key chỉ ở .env, không commit.

Gemini 3.1 Flash-Lite có free tier theo [bảng giá chính thức Google](https://ai.google.dev/gemini-api/docs/pricing). Free tier vẫn có quota theo tài khoản; không suy diễn rằng key OpenAI có credit từ việc models.list thành công. Cấu hình temperature là giá trị yêu cầu, không bảo đảm tái lập tuyệt đối hoặc có seed cố định.

Đủ 18/18 bản ghi được chấm, không có skills_modified. Lượt chạm giới hạn bước: {', '.join(recursion_failures) or 'không có'}. Giữ điểm phần việc đã hoàn thành, error và toàn bộ trace; không chạy lại để chọn điểm tốt hơn. Có {count} lượt có run.json trên toàn bộ results, bao gồm dev, lỗi và probe; không coi đây là số lượt thành công. Tag freeze: {freeze}; commit hypotheses: c14d5eb. Bộ skill không đổi sau tag. Lượt bị ngắt chưa có run.json không nằm trong số đếm này.

{hypotheses}
## 3. Làm quen Deep Agents

Tour dùng model giả: ls, read_file, write_file, edit_file, delete, glob, grep, execute, task. Execute chạy shell. General-purpose có công cụ như agent chính; mỗi lần gọi mặc định chỉ nhận prompt giao việc và trả về một báo cáo cuối. Tool task yêu cầu “Put full detail in the prompt and state exactly what it should return”; execute yêu cầu “Quote paths containing spaces”. System prompt tour là chuỗi rỗng; harness giữ nguyên BASE_PROMPT của đề. Xem tour.txt.

## 4. Đường cơ sở và phân loại lỗi

{join(taxonomy)}

Cả 9 lỗi baseline learn thuộc E; check kỹ thuật đạt 18/18 (code 7/7, data 5/5, logs 6/6). Đây là bằng chứng không quan sát lỗi A–D trong các check đã đo, không chứng minh agent không thể mắc chúng. Vết code có chạy lại pytest; data xử lý trùng, sentinel, UTC; logs xử lý traceback và repetition. Không có bằng chứng báo file không tồn tại ở nhóm F. Quy ước ẩn có thể truyền qua skill, nhưng quy ước chưa xuất hiện trong phản hồi cần đánh giá riêng.

## 5. Điều kiện subagents

Explorer đọc và báo cáo, không sửa; implementer thực hiện và kiểm chứng; reviewer kiểm tra độc lập, không sửa. Description nêu khi gọi; system prompt giới hạn phạm vi; build_agent nối PATHS_NOTE vào từng subagent. Ngữ cảnh cô lập nên cần truyền đủ quy tắc.

{join(delegation)}

Tên trong bảng lấy trực tiếp từ args của tool task trong trace mới. Số 0 nghĩa là không quan sát giao việc, không cho biết động cơ nội bộ. Các lời giao việc chỉ cung cấp nội dung prompt cho subagent, nên cần kiểm tra việc truyền yêu cầu giữ nguyên test, định dạng output và bước xác minh. Không dùng kết luận hành vi của bộ model cũ để giải thích vết mới.

Ở data-eval, model gọi implementer một lần. Prompt giao việc truyền đủ năm khóa answer, dedup giữ bản đầu, UTC, sentinel -1 và normalize category; không thể truyền các quy ước Acme ẩn mà baseline chưa học. Agent chính đọc kết quả, thử kiểm tra bằng dateutil (thiếu thư viện), sau đó dùng datetime trong thư viện chuẩn và xác nhận năm giá trị trước khi ghi answer.json. Check kỹ thuật đạt 5/5, quy ước đạt 0/4. Năm task còn lại không gọi subagent dù SUBAGENTS_NOTE yêu cầu delegation; đây là hạn chế tuân thủ prompt, không phải thử nghiệm đầy đủ năng lực của ba vai trò.

Data-learn lặp execute đọc CSV: baseline xoay quanh count số dòng/dedup, subagents lặp count sentinel -999. Cả hai chạm 100 bước và giữ 5/8. Baseline code-eval sửa test_add_slot_single_call trong file test gốc dù đề cấm; tests_not_modified thất bại, còn subagents code-eval giữ test nên đạt thêm một check. Sự cải thiện này xảy ra mà không có task call, vì vậy không quy cho việc cộng tác giữa subagent.

Trên learn, token trung bình subagents {tokens[('subagents','learn')]:,.0f} so với baseline {tokens[('baseline','learn')]:,.0f}. Trên eval, điểm chênh {sub_delta:+.3f}, token bằng {sub_ratio:.2f} lần baseline. Số token gồm subagent; trace và tool_calls chỉ phản ánh luồng chính, không đủ để quan sát toàn bộ quy trình bên trong subagent.

## 6. Self-evolving: skill do curator sinh

Curator Gemini 3.5 Flash-Lite chạy một lần trên baseline learn gốc (hiện lưu tại results/previous-gemini-3.5/baseline), không xóa và không sửa tay skill. Chỉ đưa role learn không có lỗi hạ tầng, failed check name/detail và 6000 ký tự cuối trace vào prompt. Giữ ba skill hợp lệ, mỗi file 7 dòng với 3 bullet và description bắt đầu Use when. Đây là so sánh áp dụng skill cố định sang model thực thi mới, không phải chứng minh Gemini 3.1 tự sinh skill hiệu quả.

| Skill | Tổng quát | Đúng và thiếu | Description |
|---|---|---|---|
| python-code-quality-and-testing | Quy trình sửa Python | Type hints/changelog đúng; thiếu tên tests/test_regressions.py và ngưỡng 3 test | Writing or modifying Python source code and tests |
| robust-data-cleaning-and-output | Bảng dữ liệu và output | Cent đúng trong Acme, không phổ quát cho mọi JSON; thiếu tên khóa meta và header/tên CSV | Processing tabular data, cleaning records, formatting JSON/CSV |
| structured-log-parsing | Parse log | Service và sort đúng; thiếu schema_version=2 và generated_by=log-triage | Parsing application logs, filtering levels, JSON outputs |

Skill ngắn nhưng rút gọn quá mức làm mất quy tắc cụ thể. Hợp lệ định dạng không đồng nghĩa đủ hoặc đúng trong mọi tổ chức. Tên output quy ước được GUIDE cho phép giữ, nhưng curator không giữ đầy đủ.

{join(skills)}

## 7. Kết quả so sánh

{table}

```text
{breakdown.strip()}
```

```text
{verify.strip()}
```

Các lỗi API/hạ tầng và model khác được lưu riêng tại infrastructure-crlf, skills-auto-dev-errors, quota-errors, flash-probe, gemini-3.7 và gemini-3.1-temp03. Bộ Gemini 3.5 cũ ở previous-gemini-3.5. Bộ chính giữ lỗi GraphRecursionError vì đây là hành vi không kết thúc trong ngân sách bước, vẫn có output được bộ chấm đo. Không trộn model hoặc chọn lại điểm tốt hơn.

## 8. Phân tích

1. Skills-auto chênh baseline {learning_delta:+.3f} trên learn và {eval_delta:+.3f} trên eval. H1 {'được hỗ trợ' if h1 else 'chưa được hỗ trợ đầy đủ'} theo ngưỡng đã đăng ký (eval delta {sub_delta:+.3f}, token ratio {sub_ratio:.2f}); H2 {'được hỗ trợ' if h2 else 'chưa được hỗ trợ'} (ngưỡng +0,10); H3 {'được hỗ trợ' if h3 else 'chưa được hỗ trợ'} (learn trừ eval {gap:+.3f}, ngưỡng 0,05). Đây là đối chiếu dự đoán với mẫu nhỏ, không phải kiểm định ý nghĩa thống kê.

H3 đúng ngưỡng không đủ chứng minh quá khớp skill: điểm learn giống baseline, cả hai role không đạt quy ước nào và số check mỗi task khác nhau. Chênh learn/eval còn phản ánh hai lỗi timezone của data-eval và việc sửa test gốc ở code-eval. Không có bằng chứng lợi ích học quy ước của skill trong bộ model mới.

2. Check kỹ thuật và quy ước được tách trong breakdown. Các check quy ước cải thiện so với baseline: {', '.join(improved) or 'không có'}. Điểm kỹ thuật có thể thay đổi khi skill chưa được đọc, nên không quy mọi chênh lệch thành lợi ích của nội dung skill. Bảng compare/breakdown có sẵn lấy phần nguyên token trung bình; đoạn phân tích làm tròn đến token gần nhất.

{join(novel)}

Ba quy ước eval mới không có trong skill đóng băng: tăng patch version, format/sort JSON keys, source_line. Bất kỳ check mới nào đạt cần xem là kết quả agent tự thực hiện hoặc suy đoán; skill không chứa đầy đủ quy tắc này.

3. Đối chiếu skills_read và trace.md theo từng hàng ở mục 6. Đọc skill là bằng chứng nạp nội dung, không chứng minh tuân thủ. Code-eval không có lệnh đọc skill, bỏ type hints/changelog và chuyển test gốc sang unittest dù đề cấm sửa test. Data-eval cũng không đọc skill: trace dùng datetime.fromisoformat rồi xét dt.month trực tiếp, thiếu astimezone(timezone.utc); march_revenue_utc và march_orders_utc sai, dù phần tóm tắt cuối nói đã xác định tháng theo UTC. Đây là lỗi xử lý timezone (D), không đủ bằng chứng quy nguyên nhân cho nội dung skill vì nội dung chưa được đọc.

Ở dev trước freeze với model 3.5, code đạt thêm type hints/changelog và logs đạt service/sort; các skill có checklist tương ứng. Nhưng data money_in_cents thất bại dù đọc skill, cho thấy chỉ tuân thủ một phần. Đây là ví dụ lịch sử về check skill hỗ trợ và check không giúp, không phải bằng chứng thành công của bộ model mới. Regression filename, meta schema và log header còn thiếu trong skill. Không suy ra toàn bộ nội bộ subagent từ trace.

Trong bộ mới, data-learn đọc robust-data-cleaning-and-output sau README nhưng không phải hành động đầu như SKILLS_NOTE yêu cầu. answer.json vẫn dùng revenue 3130.24 thay vì cent; metadata có tên acme_metadata, total_input_rows và valid_rows_used thay vì meta/rows_in/rows_used. Vì vậy money_in_cents là ví dụ đọc nhưng không làm theo, còn meta_block là ví dụ checklist bỏ mất schema chính xác. Chỉ 1/6 lượt skills-auto đọc skill; cả 21 check quy ước learn+eval đều thất bại. Data-learn kết thúc bình thường và dùng ít token hơn lượt baseline bị vòng lặp, nhưng điểm vẫn 5/8; không đủ căn cứ coi việc hết vòng lặp là hiệu quả học quy ước.

4. Chi phí:

{join(efficiency)}

Chỉ số là điểm chuẩn hóa trung bình chia token trung bình, quy về 100.000 token; không phải chi phí tiền hoặc xác suất thành công tuyệt đối. Token tổng tính mọi lần gọi LLM, kể cả subagent. Lượt chạm giới hạn bước vẫn được tính toàn bộ token, tránh làm hiệu quả chi phí trông cao hơn bằng cách bỏ các lần không kết thúc.

Riêng eval, token trung bình baseline {tokens[('baseline','eval')]:,.0f}, subagents {tokens[('subagents','eval')]:,.0f}, skills-auto {tokens[('skills-auto','eval')]:,.0f}. Điểm/100.000 token tương ứng {scores[('baseline','eval')]*100000/tokens[('baseline','eval')]:.3f}, {scores[('subagents','eval')]*100000/tokens[('subagents','eval')]:.3f}, {scores[('skills-auto','eval')]*100000/tokens[('skills-auto','eval')]:.3f}. Subagents chỉ nhỉnh hơn baseline nhờ giữ test code-eval, không tăng năng lực tuân thủ quy ước; chỉ một task thực sự giao việc. Skills-auto có tỷ lệ điểm/token cả sáu task tốt hơn vì tránh vòng lặp data-learn, nhưng eval vừa thấp điểm hơn vừa tốn token hơn; không kết luận đây là lựa chọn tốt nhất cho chuyển giao.

5. Curator không đọc eval, skill được kiểm tra marker và giữ nguyên trước freeze. Không thấy marker hoặc đáp án eval trong ba skill chính. Các quy ước đặc thù Acme có thể làm hạn chế chuyển sang tổ chức khác, dù không có tên input riêng. Audit 6c chỉ ra bộ lọc substring chưa chống mọi cách che giấu định danh; không có bằng chứng official skills bị tấn công.

6. Nhiễu của cùng model và cùng skill:

{join(noise)}

Chênh lệch tuyệt đối lớn nhất {max(noise_deltas):.3f}. Cặp này dùng cùng Gemini 3.1, temperature 0, limit 100 và skill đóng băng, nhưng cả hai đều chạy sau freeze; không gọi lượt lặp là dev trước freeze. Hai lượt không đủ ước lượng phân phối hoặc khoảng tin cậy. Dev gốc trước freeze ở results/skills-auto-dev dùng Gemini 3.5: code 9/10, data 5/8, logs 8/9; chỉ báo cáo lịch sử, không dùng chênh lệch giữa hai model để ước lượng nhiễu.

## 9. Hạn chế và tính hợp lệ

1. Chỉ 3 task mỗi role, mỗi cấu hình chính một lượt: không suy rộng hoặc kết luận ý nghĩa thống kê.
2. Một model thực thi trong bảng, không có seed kiểm soát; alias/provider có thể thay đổi. Curator dùng model khác vì quota, nên kết quả chỉ đo chuyển giao bộ skill này sang model thực thi.
3. Đề cố tình chứa quy ước ẩn: lợi ích có thể là truyền quy tắc tổ chức, không phải tăng năng lực suy luận chung.
4. Skills_read không đo tuân thủ; trace bỏ nội bộ subagent và cắt từng message ở 1500 ký tự, giới hạn giải thích cơ chế.
5. Giới hạn bước của toàn bộ bộ mới là 100; model/temperature đã được thử khả dụng trước khi chọn. Giữ nguyên bộ skill và giả thuyết sau khi xem eval; không tạo giả thuyết mới cho model mới. Lỗi vòng lặp giữ trong bảng, nên điểm phần việc hoàn thành không đồng nghĩa agent kết thúc bình thường.

## 10. Kết luận

Harness đã hoàn thiện và kết quả chính dùng một model thực thi, skill đóng băng, đủ 18 bản ghi được chấm. Skills-auto chênh baseline {eval_delta:+.3f} trên eval; kết quả này chỉ áp dụng cho bộ task nhỏ và bộ skill được model khác sinh. Subagents dùng {sub_ratio:.2f} lần token baseline trên eval, cần cân nhắc cùng chênh điểm {sub_delta:+.3f}. Skill tự sinh ngắn vẫn có thể bỏ sót schema và bị tuân thủ một phần. Bước tiếp theo là một thí nghiệm mới giữ chính xác quy ước trong skill, rồi lặp đo nhiều lần với cùng điều kiện.

## Phụ lục

Lệnh và môi trường tái lập: RUNBOOK.md, requirements-lock.txt, Dockerfile bổ sung Git cho verify_freeze. Thứ tự gốc: tests → baseline/subagents learn → curator → skills-auto learn → hypotheses → freeze → eval. Sau lỗi quota và yêu cầu đổi model của người dùng: run_cohort.py chạy đủ ba điều kiện, lặp ba tác vụ học với skill cố định, verify → compare/breakdown. Lịch chờ finish_lab.py cũ đã hủy, không còn tiến trình chờ model 3.5.

Lỗi môi trường CRLF: hash test gốc khi đổi CRLF thành LF khớp hash bộ chấm. Chỉ chuẩn hóa .py trong sandbox, giữ nguyên tasks/ của repo. Hai pilot code chạm 60 bước được lưu riêng; dev hợp lệ đạt 9/10 với limit 100. Gemini 2.5 Flash-Lite trả 404 cho tài khoản mới; Flash-Lite 3.5 dùng được nhưng hết quota 500 request/ngày. Flash 3.5 thử riêng gặp quota 20/ngày; model 3.8/3.7 gặp 504/503; 3.1 Flash-Lite có lượt data lặp lệnh đến recursion limit. Không trộn các probe với bảng chính và không suy diễn key OpenAI có credit chỉ từ models.list thành công.

### Mở rộng 6c:{appendix}
"""
    backup = Path("report/REPORT-before-finalization.md")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    report = "\n".join(line.rstrip() for line in report.splitlines()).rstrip() + "\n"
    Path("report/REPORT.md").write_text(report, encoding="utf-8")
    manifest_path = Path("report/experiments.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update(pending_primary_runs=0, completed_primary_runs=18,
                        completion_timestamp=datetime.now(timezone.utc).isoformat())
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    keys = [v for k, v in dotenv_values(".env").items() if k.endswith("API_KEY") and v and len(v) > 16]
    for folder in ("src", "report", "results", "skills"):
        for path in Path(folder).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".json", ".txt", ".log"}:
                content = path.read_text(encoding="utf-8", errors="ignore")
                assert not any(key in content for key in keys), f"Secret detected in {path}; refusing completion"
    print("Final report generated from 18 graded primary runs, including retained recursion outcomes.")


if __name__ == "__main__":
    main()
