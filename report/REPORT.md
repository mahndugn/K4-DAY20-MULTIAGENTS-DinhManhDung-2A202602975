# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Đinh Mạnh Dũng | 2A202602975 | Harness, thí nghiệm, phân tích với hỗ trợ Codex; thông tin suy ra từ tên repo. |

Bộ so sánh mới dùng duy nhất `google_genai:gemini-3.1-flash-lite`, LAB_TEMPERATURE=0, recursion_limit=100 cho cả 18 lượt. Curator và giai đoạn học gốc dùng Gemini 3.5 Flash-Lite; model này hết quota nên người dùng yêu cầu đổi model miễn phí và chạy lại toàn bộ so sánh. Không sinh lại skill sau khi đã xem eval. Deep Agents 0.7.21, Python 3.12.15, Docker Linux trên Windows. 32 test ngoại tuyến đạt; 6 test runner đạt sau bổ sung metadata. Phiên bản thư viện ở requirements-lock.txt. Key chỉ ở .env, không commit.

Gemini 3.1 Flash-Lite có free tier theo [bảng giá chính thức Google](https://ai.google.dev/gemini-api/docs/pricing). Free tier vẫn có quota theo tài khoản; không suy diễn rằng key OpenAI có credit từ việc models.list thành công. Cấu hình temperature là giá trị yêu cầu, không bảo đảm tái lập tuyệt đối hoặc có seed cố định.

Đủ 18/18 bản ghi được chấm, không có skills_modified. Lượt chạm giới hạn bước: baseline/data-learn, subagents/data-learn. Giữ điểm phần việc đã hoàn thành, error và toàn bộ trace; không chạy lại để chọn điểm tốt hơn. Có 43 lượt có run.json trên toàn bộ results, bao gồm dev, lỗi và probe; không coi đây là số lượt thành công. Tag freeze: 74f4a726739df12521ad39155798dc386e184db7; commit hypotheses: c14d5eb. Bộ skill không đổi sau tag. Lượt bị ngắt chưa có run.json không nằm trong số đếm này.

## 2. Giả thuyết

- H1 (subagents so với baseline): Điểm đánh giá của subagents gần baseline (chênh lệch tuyệt đối dưới 0,10), nhưng token trung bình cao hơn ít nhất 20%. Phân công có thể giúp kiểm chứng kỹ thuật, song không cung cấp các quy ước tổ chức chưa từng thấy.
- H2 (skills-auto so với baseline): Skills-auto có điểm đánh giá cao hơn baseline ít nhất 0,10 nhờ chuyển các quy ước lặp lại trong phản hồi thành checklist; dự đoán không đạt điểm tối đa vì quy ước mới và khả năng chỉ tuân thủ một phần. Đây là dự đoán cho lab có phản hồi quy tắc cụ thể, không phải kết luận rằng mọi skill tự sinh đều hiệu quả.
- H3 (tác vụ học so với tác vụ đánh giá): Điểm trung bình skills-auto trên tác vụ học cao hơn trên tác vụ đánh giá ít nhất 0,05. Quy ước mới và chuyển miền dữ liệu có thể làm lợi ích giảm; cần phân biệt điều này với nhiễu bằng việc so sánh lần dev và lần chạy sau freeze.

Căn cứ: hướng dẫn lab dự đoán lỗi quy ước (`rule_`) chiếm đa số. [SkillsBench v4](https://arxiv.org/abs/2602.12670v4) báo cáo lợi ích của skill **được tuyển chọn**, đồng thời nhấn mạnh các gói skill tập trung; kết quả đó không trực tiếp chứng minh lợi ích của skill tự sinh. [SkillEvolBench](https://arxiv.org/abs/2605.24117) cho thấy thích nghi cục bộ không đảm bảo skill bền vững trên triển khai đóng băng. Các giả thuyết trên đã được chốt trước khi chạy tác vụ đánh giá.


## 3. Làm quen Deep Agents

Tour dùng model giả: ls, read_file, write_file, edit_file, delete, glob, grep, execute, task. Execute chạy shell. General-purpose có công cụ như agent chính; mỗi lần gọi mặc định chỉ nhận prompt giao việc và trả về một báo cáo cuối. Tool task yêu cầu “Put full detail in the prompt and state exactly what it should return”; execute yêu cầu “Quote paths containing spaces”. System prompt tour là chuỗi rỗng; harness giữ nguyên BASE_PROMPT của đề. Xem tour.txt.

## 4. Đường cơ sở và phân loại lỗi

| Tác vụ | Check thất bại | Nhóm | Bằng chứng detail |
|---|---|---|---|
| code-learn | rule_type_hints | E | RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value. |
| code-learn | rule_regression_tests | E | RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass. |
| code-learn | rule_changelog | E | RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets). |
| data-learn | rule_money_in_cents | E | RULE: money values in answer.json are integer cents (1606.67 USD is written 160667). |
| data-learn | rule_meta_block | E | RULE: answer.json has an object `meta` = {"source": <input file name>, "rows_in": <number of data rows in the input file, duplicates included>, "rows_used": <number of distinct orders with a known amount>}. |
| data-learn | rule_clean_csv | E | RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents; one row per distinct order with a known amount; timestamp_utc as YYYY-MM-DDTHH:MM:SSZ (UTC); region in canonical spelling (North, South, East, West); amount in integer cents. |
| logs-learn | rule_service_names | E | RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service). |
| logs-learn | rule_sorted_errors | E | RULE: `errors` is sorted by service, then by timestamp_utc, ascending. |
| logs-learn | rule_schema_header | E | RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage". |

Cả 9 lỗi baseline learn thuộc E; check kỹ thuật đạt 18/18 (code 7/7, data 5/5, logs 6/6). Đây là bằng chứng không quan sát lỗi A–D trong các check đã đo, không chứng minh agent không thể mắc chúng. Vết code có chạy lại pytest; data xử lý trùng, sentinel, UTC; logs xử lý traceback và repetition. Không có bằng chứng báo file không tồn tại ở nhóm F. Quy ước ẩn có thể truyền qua skill, nhưng quy ước chưa xuất hiện trong phản hồi cần đánh giá riêng.

## 5. Điều kiện subagents

Explorer đọc và báo cáo, không sửa; implementer thực hiện và kiểm chứng; reviewer kiểm tra độc lập, không sửa. Description nêu khi gọi; system prompt giới hạn phạm vi; build_agent nối PATHS_NOTE vào từng subagent. Ngữ cảnh cô lập nên cần truyền đủ quy tắc.

| Tác vụ | Calls task | Tên quan sát trong trace | Token | Giây |
|---|---:|---|---:|---:|
| code-eval | 0 | Không quan sát được tên | 93,466 | 39.8 |
| code-learn | 0 | Không quan sát được tên | 151,171 | 73.4 |
| data-eval | 1 | implementer | 89,569 | 66.1 |
| data-learn | 0 | Không quan sát được tên | 516,138 | 194.9 |
| logs-eval | 0 | Không quan sát được tên | 45,013 | 30.6 |
| logs-learn | 0 | Không quan sát được tên | 57,014 | 16.4 |

Tên trong bảng lấy trực tiếp từ args của tool task trong trace mới. Số 0 nghĩa là không quan sát giao việc, không cho biết động cơ nội bộ. Các lời giao việc chỉ cung cấp nội dung prompt cho subagent, nên cần kiểm tra việc truyền yêu cầu giữ nguyên test, định dạng output và bước xác minh. Không dùng kết luận hành vi của bộ model cũ để giải thích vết mới.

Ở data-eval, model gọi implementer một lần. Prompt giao việc truyền đủ năm khóa answer, dedup giữ bản đầu, UTC, sentinel -1 và normalize category; không thể truyền các quy ước Acme ẩn mà baseline chưa học. Agent chính đọc kết quả, thử kiểm tra bằng dateutil (thiếu thư viện), sau đó dùng datetime trong thư viện chuẩn và xác nhận năm giá trị trước khi ghi answer.json. Check kỹ thuật đạt 5/5, quy ước đạt 0/4. Năm task còn lại không gọi subagent dù SUBAGENTS_NOTE yêu cầu delegation; đây là hạn chế tuân thủ prompt, không phải thử nghiệm đầy đủ năng lực của ba vai trò.

Data-learn lặp execute đọc CSV: baseline xoay quanh count số dòng/dedup, subagents lặp count sentinel -999. Cả hai chạm 100 bước và giữ 5/8. Baseline code-eval sửa test_add_slot_single_call trong file test gốc dù đề cấm; tests_not_modified thất bại, còn subagents code-eval giữ test nên đạt thêm một check. Sự cải thiện này xảy ra mà không có task call, vì vậy không quy cho việc cộng tác giữa subagent.

Trên learn, token trung bình subagents 241,441 so với baseline 180,167. Trên eval, điểm chênh +0.030, token bằng 1.01 lần baseline. Số token gồm subagent; trace và tool_calls chỉ phản ánh luồng chính, không đủ để quan sát toàn bộ quy trình bên trong subagent.

## 6. Self-evolving: skill do curator sinh

Curator Gemini 3.5 Flash-Lite chạy một lần trên baseline learn gốc (hiện lưu tại results/previous-gemini-3.5/baseline), không xóa và không sửa tay skill. Chỉ đưa role learn không có lỗi hạ tầng, failed check name/detail và 6000 ký tự cuối trace vào prompt. Giữ ba skill hợp lệ, mỗi file 7 dòng với 3 bullet và description bắt đầu Use when. Đây là so sánh áp dụng skill cố định sang model thực thi mới, không phải chứng minh Gemini 3.1 tự sinh skill hiệu quả.

| Skill | Tổng quát | Đúng và thiếu | Description |
|---|---|---|---|
| python-code-quality-and-testing | Quy trình sửa Python | Type hints/changelog đúng; thiếu tên tests/test_regressions.py và ngưỡng 3 test | Writing or modifying Python source code and tests |
| robust-data-cleaning-and-output | Bảng dữ liệu và output | Cent đúng trong Acme, không phổ quát cho mọi JSON; thiếu tên khóa meta và header/tên CSV | Processing tabular data, cleaning records, formatting JSON/CSV |
| structured-log-parsing | Parse log | Service và sort đúng; thiếu schema_version=2 và generated_by=log-triage | Parsing application logs, filtering levels, JSON outputs |

Skill ngắn nhưng rút gọn quá mức làm mất quy tắc cụ thể. Hợp lệ định dạng không đồng nghĩa đủ hoặc đúng trong mọi tổ chức. Tên output quy ước được GUIDE cho phép giữ, nhưng curator không giữ đầy đủ.

| Tác vụ | Skills read | Điểm | Quy ước còn thất bại |
|---|---:|---|---|
| code-eval | 0 | 6/11 | rule_type_hints, rule_regression_tests, rule_changelog, rule_version_bump |
| code-learn | 0 | 7/10 | rule_type_hints, rule_regression_tests, rule_changelog |
| data-eval | 0 | 3/9 | rule_money_in_cents, rule_meta_block, rule_clean_csv, rule_sorted_keys_format |
| data-learn | 1 | 5/8 | rule_money_in_cents, rule_meta_block, rule_clean_csv |
| logs-eval | 0 | 6/10 | rule_service_names, rule_sorted_errors, rule_schema_header, rule_source_line |
| logs-learn | 0 | 6/9 | rule_service_names, rule_sorted_errors, rule_schema_header |

## 7. Kết quả so sánh

| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 7/10 | 7/10 | 7/10 |
| data-learn | 5/8 | 5/8 | 5/8 |
| logs-learn | 6/9 | 6/9 | 6/9 |
| code-eval | 6/11 | 7/11 | 6/11 |
| data-eval | 5/9 | 5/9 | 3/9 |
| logs-eval | 6/10 | 6/10 | 6/10 |
| **Mean score - learning tasks** | 0.66 | 0.66 | 0.66 |
| **Mean score - evaluation tasks** | 0.57 | 0.60 | 0.49 |
| **Mean tokens per run** | 127,819 | 158,728 | 107,594 |
| **Runs that read a skill** | 0/6 | 0/6 | 1/6 |

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     17/18         0/12          75,472      0/3
baseline      learn    18/18         0/9          180,166      0/3
subagents     eval     18/18         0/12          76,016      0/3
subagents     learn    18/18         0/9          241,441      0/3
skills-auto   eval     15/18         0/12         122,305      0/3
skills-auto   learn    18/18         0/9           92,883      1/3
```

```text
checked 6 runs of skill conditions: OK
```

Các lỗi API/hạ tầng và model khác được lưu riêng tại infrastructure-crlf, skills-auto-dev-errors, quota-errors, flash-probe, gemini-3.7 và gemini-3.1-temp03. Bộ Gemini 3.5 cũ ở previous-gemini-3.5. Bộ chính giữ lỗi GraphRecursionError vì đây là hành vi không kết thúc trong ngân sách bước, vẫn có output được bộ chấm đo. Không trộn model hoặc chọn lại điểm tốt hơn.

## 8. Phân tích

1. Skills-auto chênh baseline +0.000 trên learn và -0.074 trên eval. H1 chưa được hỗ trợ đầy đủ theo ngưỡng đã đăng ký (eval delta +0.030, token ratio 1.01); H2 chưa được hỗ trợ (ngưỡng +0,10); H3 được hỗ trợ (learn trừ eval +0.171, ngưỡng 0,05). Đây là đối chiếu dự đoán với mẫu nhỏ, không phải kiểm định ý nghĩa thống kê.

H3 đúng ngưỡng không đủ chứng minh quá khớp skill: điểm learn giống baseline, cả hai role không đạt quy ước nào và số check mỗi task khác nhau. Chênh learn/eval còn phản ánh hai lỗi timezone của data-eval và việc sửa test gốc ở code-eval. Không có bằng chứng lợi ích học quy ước của skill trong bộ model mới.

2. Check kỹ thuật và quy ước được tách trong breakdown. Các check quy ước cải thiện so với baseline: không có. Điểm kỹ thuật có thể thay đổi khi skill chưa được đọc, nên không quy mọi chênh lệch thành lợi ích của nội dung skill. Bảng compare/breakdown có sẵn lấy phần nguyên token trung bình; đoạn phân tích làm tròn đến token gần nhất.

| Quy ước mới trên eval | baseline | subagents | skills-auto |
|---|---|---|---|
| code-eval/rule_version_bump | Không đạt | Không đạt | Không đạt |
| data-eval/rule_sorted_keys_format | Không đạt | Không đạt | Không đạt |
| logs-eval/rule_source_line | Không đạt | Không đạt | Không đạt |

Ba quy ước eval mới không có trong skill đóng băng: tăng patch version, format/sort JSON keys, source_line. Bất kỳ check mới nào đạt cần xem là kết quả agent tự thực hiện hoặc suy đoán; skill không chứa đầy đủ quy tắc này.

3. Đối chiếu skills_read và trace.md theo từng hàng ở mục 6. Đọc skill là bằng chứng nạp nội dung, không chứng minh tuân thủ. Code-eval không có lệnh đọc skill, bỏ type hints/changelog và chuyển test gốc sang unittest dù đề cấm sửa test. Data-eval cũng không đọc skill: trace dùng datetime.fromisoformat rồi xét dt.month trực tiếp, thiếu astimezone(timezone.utc); march_revenue_utc và march_orders_utc sai, dù phần tóm tắt cuối nói đã xác định tháng theo UTC. Đây là lỗi xử lý timezone (D), không đủ bằng chứng quy nguyên nhân cho nội dung skill vì nội dung chưa được đọc.

Ở dev trước freeze với model 3.5, code đạt thêm type hints/changelog và logs đạt service/sort; các skill có checklist tương ứng. Nhưng data money_in_cents thất bại dù đọc skill, cho thấy chỉ tuân thủ một phần. Đây là ví dụ lịch sử về check skill hỗ trợ và check không giúp, không phải bằng chứng thành công của bộ model mới. Regression filename, meta schema và log header còn thiếu trong skill. Không suy ra toàn bộ nội bộ subagent từ trace.

Trong bộ mới, data-learn đọc robust-data-cleaning-and-output sau README nhưng không phải hành động đầu như SKILLS_NOTE yêu cầu. answer.json vẫn dùng revenue 3130.24 thay vì cent; metadata có tên acme_metadata, total_input_rows và valid_rows_used thay vì meta/rows_in/rows_used. Vì vậy money_in_cents là ví dụ đọc nhưng không làm theo, còn meta_block là ví dụ checklist bỏ mất schema chính xác. Chỉ 1/6 lượt skills-auto đọc skill; cả 21 check quy ước learn+eval đều thất bại. Data-learn kết thúc bình thường và dùng ít token hơn lượt baseline bị vòng lặp, nhưng điểm vẫn 5/8; không đủ căn cứ coi việc hết vòng lặp là hiệu quả học quy ước.

4. Chi phí:

| Điều kiện | Token trung bình (6 task) | Điểm TB / 100.000 token |
|---|---:|---:|
| baseline | 127,820 | 0.481 |
| subagents | 158,728 | 0.397 |
| skills-auto | 107,594 | 0.538 |

Chỉ số là điểm chuẩn hóa trung bình chia token trung bình, quy về 100.000 token; không phải chi phí tiền hoặc xác suất thành công tuyệt đối. Token tổng tính mọi lần gọi LLM, kể cả subagent. Lượt chạm giới hạn bước vẫn được tính toàn bộ token, tránh làm hiệu quả chi phí trông cao hơn bằng cách bỏ các lần không kết thúc.

Riêng eval, token trung bình baseline 75,473, subagents 76,016, skills-auto 122,306. Điểm/100.000 token tương ứng 0.751, 0.786, 0.403. Subagents chỉ nhỉnh hơn baseline nhờ giữ test code-eval, không tăng năng lực tuân thủ quy ước; chỉ một task thực sự giao việc. Skills-auto có tỷ lệ điểm/token cả sáu task tốt hơn vì tránh vòng lặp data-learn, nhưng eval vừa thấp điểm hơn vừa tốn token hơn; không kết luận đây là lựa chọn tốt nhất cho chuyển giao.

5. Curator không đọc eval, skill được kiểm tra marker và giữ nguyên trước freeze. Không thấy marker hoặc đáp án eval trong ba skill chính. Các quy ước đặc thù Acme có thể làm hạn chế chuyển sang tổ chức khác, dù không có tên input riêng. Audit 6c chỉ ra bộ lọc substring chưa chống mọi cách che giấu định danh; không có bằng chứng official skills bị tấn công.

6. Nhiễu của cùng model và cùng skill:

| Tác vụ học | Lặp sau freeze | Bộ chính | Δ điểm | Token lặp / chính | Skill đọc lặp / chính | Lỗi lượt lặp |
|---|---:|---:|---:|---:|---:|---|
| code-learn | 7/10 | 7/10 | +0.000 | 121,703 / 122,544 | 0 / 0 | Không |
| data-learn | 5/8 | 5/8 | +0.000 | 104,313 / 94,452 | 1 / 1 | Không |
| logs-learn | 6/9 | 6/9 | +0.000 | 61,653 / 61,653 | 0 / 0 | Không |

Chênh lệch tuyệt đối lớn nhất 0.000. Cặp này dùng cùng Gemini 3.1, temperature 0, limit 100 và skill đóng băng, nhưng cả hai đều chạy sau freeze; không gọi lượt lặp là dev trước freeze. Hai lượt không đủ ước lượng phân phối hoặc khoảng tin cậy. Dev gốc trước freeze ở results/skills-auto-dev dùng Gemini 3.5: code 9/10, data 5/8, logs 8/9; chỉ báo cáo lịch sử, không dùng chênh lệch giữa hai model để ước lượng nhiễu.

## 9. Hạn chế và tính hợp lệ

1. Chỉ 3 task mỗi role, mỗi cấu hình chính một lượt: không suy rộng hoặc kết luận ý nghĩa thống kê.
2. Một model thực thi trong bảng, không có seed kiểm soát; alias/provider có thể thay đổi. Curator dùng model khác vì quota, nên kết quả chỉ đo chuyển giao bộ skill này sang model thực thi.
3. Đề cố tình chứa quy ước ẩn: lợi ích có thể là truyền quy tắc tổ chức, không phải tăng năng lực suy luận chung.
4. Skills_read không đo tuân thủ; trace bỏ nội bộ subagent và cắt từng message ở 1500 ký tự, giới hạn giải thích cơ chế.
5. Giới hạn bước của toàn bộ bộ mới là 100; model/temperature đã được thử khả dụng trước khi chọn. Giữ nguyên bộ skill và giả thuyết sau khi xem eval; không tạo giả thuyết mới cho model mới. Lỗi vòng lặp giữ trong bảng, nên điểm phần việc hoàn thành không đồng nghĩa agent kết thúc bình thường.

## 10. Kết luận

Harness đã hoàn thiện và kết quả chính dùng một model thực thi, skill đóng băng, đủ 18 bản ghi được chấm. Skills-auto chênh baseline -0.074 trên eval; kết quả này chỉ áp dụng cho bộ task nhỏ và bộ skill được model khác sinh. Subagents dùng 1.01 lần token baseline trên eval, cần cân nhắc cùng chênh điểm +0.030. Skill tự sinh ngắn vẫn có thể bỏ sót schema và bị tuân thủ một phần. Bước tiếp theo là một thí nghiệm mới giữ chính xác quy ước trong skill, rồi lặp đo nhiều lần với cùng điều kiện.

## Phụ lục

Lệnh và môi trường tái lập: RUNBOOK.md, requirements-lock.txt, Dockerfile bổ sung Git cho verify_freeze. Thứ tự gốc: tests → baseline/subagents learn → curator → skills-auto learn → hypotheses → freeze → eval. Sau lỗi quota và yêu cầu đổi model của người dùng: run_cohort.py chạy đủ ba điều kiện, lặp ba tác vụ học với skill cố định, verify → compare/breakdown. Lịch chờ finish_lab.py cũ đã hủy, không còn tiến trình chờ model 3.5.

Lỗi môi trường CRLF: hash test gốc khi đổi CRLF thành LF khớp hash bộ chấm. Chỉ chuẩn hóa .py trong sandbox, giữ nguyên tasks/ của repo. Hai pilot code chạm 60 bước được lưu riêng; dev hợp lệ đạt 9/10 với limit 100. Gemini 2.5 Flash-Lite trả 404 cho tài khoản mới; Flash-Lite 3.5 dùng được nhưng hết quota 500 request/ngày. Flash 3.5 thử riêng gặp quota 20/ngày; model 3.8/3.7 gặp 504/503; 3.1 Flash-Lite có lượt data lặp lệnh đến recursion limit. Không trộn các probe với bảng chính và không suy diễn key OpenAI có credit chỉ từ models.list thành công.

### Mở rộng 6c: kiểm tra đầu ra đối kháng của curator

Thí nghiệm ngoại tuyến độc lập tại `report/red_team_validator.py`, kết quả riêng ở `results/red-team-validator/results.json`. Sau freeze, tạo 5 chuỗi skill giả lập: 1 control hợp lệ và 4 đầu ra đối kháng (tên chứa ../, định danh eval nguyên văn, định danh chèn khoảng trắng, định danh chèn ký tự zero-width). Gọi đúng validate_skill có sẵn; không gọi LLM, không ghi hay thay đổi skills/auto.

Control được nhận; traversal và định danh nguyên văn bị chặn; hai dạng che giấu định danh đều được nhận. Bộ lọc chặn 2/4 đầu ra đối kháng, so với 1/1 đầu ra control được nhận. Nguyên nhân nằm ở phép dò substring trên text.lower(): khoảng trắng hoặc ký tự vô hình làm gián đoạn marker. Đây là kiểm tra khả năng lọt qua validator, không phải bằng chứng mô hình curator thực tế sẽ tạo nội dung gian lận hoặc official skills đã rò rỉ.

Đề xuất: trong một harness ngoài lab, chuẩn hóa Unicode, loại ký tự vô hình và kiểm tra các biểu diễn token trước khi dò marker; bổ sung review ngữ nghĩa và xác minh provenance học. Chưa sửa validate_skill vì RUBRIC cấm sửa mã có sẵn. Hạn chế: chỉ 4 mẫu thủ công, không đo xác suất tấn công LLM thành công; bước tiếp theo là thử prompt injection trên curator thật với dữ liệu giả và lưu đầy đủ prompt/reply riêng. Có thể chạy lại bằng `docker run --rm -v "${PWD}:/lab" lab-deepagents python report/red_team_validator.py`.
