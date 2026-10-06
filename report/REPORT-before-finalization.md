# Báo cáo Lab: Self evolving Agentic

> Bản nháp lịch sử của bộ Gemini 3.5. Ngày 2026-10-06, người dùng chọn đổi sang Gemini miễn phí khác và chạy lại toàn bộ so sánh. Bộ Gemini 3.1 Flash-Lite (temperature 0, limit 100) đang được ghi riêng tại results/gemini-3.1-temp0; lịch chờ model 3.5 đã hủy. Các bảng bên dưới chưa phải bảng cuối của model mới. Không sửa skill hoặc giả thuyết đã đóng băng.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Đinh Mạnh Dũng | 2A202602975 | Hoàn thiện harness, chạy thí nghiệm và phân tích (có hỗ trợ Codex); thông tin suy ra từ tên repo. |

Mô hình: `google_genai:gemini-3.5-flash-lite`. Cấu hình `LAB_TEMPERATURE=0`, nhưng provider thông báo model dùng sampling cố định và bỏ qua temperature. Giới hạn 60 bước ở các lần học ban đầu; tăng lên 100 sau hai lần dev code chạm giới hạn, dùng 100 cho các lần chính thức của cả ba điều kiện. Baseline/subagents learn kết thúc trước giới hạn 60. Deep Agents 0.7.21; Python 3.12.15 trong Docker Linux trên Windows. API key chỉ lưu trong `.env`, không đưa vào báo cáo hoặc commit.

Đã chạy kiểm thử ngoại tuyến: **32 passed**; 6 test runner cũng đạt sau khi bổ sung metadata. Phiên bản thư viện xem `requirements-lock.txt`. Hiện có 10/18 lượt chính thức hợp lệ; còn 8 lượt chờ quota. Có 26 lượt có run.json trên toàn bộ results (gồm dev, lỗi và probe); không coi đây là số lượt thành công.

## 2. Giả thuyết

- H1 (subagents so với baseline): Điểm đánh giá của subagents gần baseline (chênh lệch tuyệt đối dưới 0,10), nhưng token trung bình cao hơn ít nhất 20%. Phân công có thể giúp kiểm chứng kỹ thuật, song không cung cấp các quy ước tổ chức chưa từng thấy.
- H2 (skills-auto so với baseline): Skills-auto có điểm đánh giá cao hơn baseline ít nhất 0,10 nhờ chuyển các quy ước lặp lại trong phản hồi thành checklist; dự đoán không đạt điểm tối đa vì quy ước mới và khả năng chỉ tuân thủ một phần. Đây là dự đoán cho lab có phản hồi quy tắc cụ thể, không phải kết luận rằng mọi skill tự sinh đều hiệu quả.
- H3 (tác vụ học so với tác vụ đánh giá): Điểm trung bình skills-auto trên tác vụ học cao hơn trên tác vụ đánh giá ít nhất 0,05. Quy ước mới và chuyển miền dữ liệu có thể làm lợi ích giảm; cần phân biệt điều này với nhiễu bằng việc so sánh lần dev và lần chạy sau freeze.

Căn cứ: hướng dẫn lab dự đoán lỗi quy ước (`rule_`) chiếm đa số. [SkillsBench v4](https://arxiv.org/abs/2602.12670v4) báo cáo lợi ích của skill **được tuyển chọn**, đồng thời nhấn mạnh các gói skill tập trung; kết quả đó không trực tiếp chứng minh lợi ích của skill tự sinh. [SkillEvolBench](https://arxiv.org/abs/2605.24117) cho thấy thích nghi cục bộ không đảm bảo skill bền vững trên triển khai đóng băng. Các giả thuyết trên sẽ được chốt trước khi chạy tác vụ đánh giá.

## 3. Làm quen Deep Agents

1. `tour.py` cho thấy các tool: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`; `execute` chạy shell. Bản ghi đầy đủ ở `tour.txt`.
2. `general-purpose` có các công cụ như agent chính, dùng cho nghiên cứu và công việc nhiều bước. Mỗi lần gọi mặc định là stateless, chỉ nhận prompt giao việc và trả về một báo cáo cuối; không tự thấy toàn bộ hội thoại của agent chính.
3. Tool `task` yêu cầu: “Put full detail in the prompt and state exactly what it should return”. Tool `execute` yêu cầu: “Quote paths containing spaces”. System prompt mặc định của tour là chuỗi rỗng; harness của lab dùng `BASE_PROMPT` được cung cấp sẵn.

## 4. Đường cơ sở và phân loại lỗi

| Tác vụ | Check thất bại | Nhóm | Bằng chứng từ detail |
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

Cả 9 lỗi baseline đều thuộc nhóm E; 18/18 check kỹ thuật đạt (code 7/7, data 5/5, logs 6/6). Đây là bằng chứng không thấy lỗi kỹ thuật thuộc A–D trong các check đã đo; không chứng minh agent không thể mắc các lỗi đó. Trace code cho thấy chạy lại pytest thành công; data xử lý trùng, sentinel và UTC; logs xử lý stack trace và repetition. Không có bằng chứng nhóm F từ các file được agent báo cáo. Skill có thể truyền quy ước đã biết, nhưng không suy ra đầy đủ quy ước mới.

## 5. Điều kiện subagents

Ba vai trò tự định nghĩa: explorer đọc đặc tả và dữ liệu, không sửa file; implementer thực hiện và kiểm chứng; reviewer kiểm tra độc lập, không sửa file. Description nêu khi gọi và system prompt giới hạn phạm vi. Mỗi subagent nhận thêm PATHS_NOTE.

| Tác vụ học | Calls task | Subagent quan sát được | Token | Giây |
|---|---:|---|---:|---:|
| code-learn | 1 | explorer | 234840 | 119.3 |
| data-learn | 5 | general-purpose (cả 5 lần) | 1483179 | 486.3 |
| logs-learn | 0 | Không giao việc | 66904 | 32.5 |

Code: lời giao việc yêu cầu explorer vừa đọc vừa implement, trái phạm vi read-only; không truyền quy tắc không sửa test. Agent chính có đọc code/test và chạy pytest (8 passed), nhưng không kiểm tra hash test gốc; check tests_not_modified thất bại là lỗi thật trong lần đã chuẩn hóa LF. Đây là bằng chứng phân công thiếu quy tắc và kiểm chứng chưa đủ, không phải lỗi CRLF của lần baseline đầu.

Data: agent ưu tiên general-purpose hơn các vai trò tự định nghĩa. Lời giao việc đầu chứa nhiều quy tắc ngày, vùng và sentinel nhưng để mở quyết định dedup; các lần sau rút gọn ngữ cảnh, yêu cầu viết/kiểm tra script và suy đoán quy ước Acme. Vết ghi nhiều vòng xác minh, nhưng north_q1_orders vẫn sai (got 13). Việc xác minh trùng lặp không đảm bảo kiểm chứng độc lập đúng định nghĩa; token bằng 10,95 lần baseline data và thời gian bằng 9,39 lần. Logs không giao việc là kết quả hợp lệ: agent tự parse bằng script; không thể khẳng định động cơ nội bộ, chỉ quan sát không có call task.

Trên tập học, subagents dùng trung bình 594974 token và 212,7 giây, baseline 110995 token và 49,9 giây. Đa tác tử tốn khoảng 5,36 lần token nhưng điểm giảm từ 0,664 xuống 0,589. Trace chỉ ghi luồng chính và báo cáo cuối; không thể xác định từng thao tác bên trong agent con.

## 6. Self-evolving: skill do curator sinh

Curator chạy một lần trên baseline learn, sinh ba skill hợp lệ, giữ nguyên đầu ra và không xóa skill. Chỉ đọc run role learn không có lỗi hạ tầng, tên/detail check thất bại và 6000 ký tự cuối trace. Không đọc kết quả eval để sinh skill.

| Skill | Tính tổng quát | Đúng và thiếu | Độ dài và description |
|---|---|---|---|
| python-code-quality-and-testing | Quy trình sửa Python, không nêu dữ liệu hay hàm riêng | Type hints và changelog đúng phản hồi; chỉ nói dedicated test file nên thiếu tên tests/test_regressions.py và ngưỡng ít nhất 3 test | 7 dòng, 3 bullet; Use when writing or modifying Python source code... kích hoạt rộng |
| robust-data-cleaning-and-output | Quy trình bảng dữ liệu và output | Quy đổi cent đúng trong Acme; cần giới hạn ở quy ước tổ chức vì không phải mọi JSON dùng cent. Metadata thiếu tên meta/source/rows_in/rows_used; CSV thiếu header và tên output cụ thể | 7 dòng, 3 bullet; Use when processing tabular data... phù hợp data |
| structured-log-parsing | Quy trình log, không lặp tên input | Chuẩn service và sort đúng; thiếu schema_version=2 và generated_by=log-triage nên không cung cấp đủ quy tắc header | 7 dòng, 3 bullet; Use when parsing application logs... phù hợp logs |

Cả ba skill ngắn, không thừa và không có marker đánh giá, nhưng rút gọn quá mức làm mất quy tắc kiểm chứng được. Hợp lệ về định dạng không đồng nghĩa đủ hoặc hoàn toàn tổng quát. Các tên output quy ước được GUIDE cho phép giữ lại; lần curator này đã không giữ đầy đủ. Lần dev đầu: code đọc 3 skill, đạt 9/10 nhưng chạm recursion limit 60 (lưu riêng và chạy lại); data đọc 1 skill, đạt 5/8; logs đọc 1 skill, đạt 8/9. Data vẫn viết tiền theo USD, metadata không khớp schema và không có clean.csv; logs cải thiện chuẩn service và sort, còn thiếu schema header. Những kết quả này phù hợp các thiếu sót nội dung đã nhận diện.

## 7. Kết quả so sánh

Bảng tạm do lab.compare sinh từ các lượt hợp lệ hiện có. Cột skills-auto chính thức còn thiếu; dev giữ riêng. Subagents eval chỉ có code-eval nên không so sánh trung bình eval 1 task với baseline 3 task.

| Task | baseline | subagents |
|---|---|---|
| code-learn | 7/10 | 6/10 |
| data-learn | 5/8 | 4/8 |
| logs-learn | 6/9 | 6/9 |
| code-eval | 7/11 | 7/11 |
| data-eval | 5/9 | - |
| logs-eval | 6/10 | - |
| **Mean score - learning tasks** | 0.66 | 0.59 |
| **Mean score - evaluation tasks** | 0.60 | 0.64 |
| **Mean tokens per run** | 100,870 | 495,823 |
| **Runs that read a skill** | 0/6 | 0/4 |

Thống kê hiện tại:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     18/18         0/12          90,746      0/3     
baseline      learn    18/18         0/9          110,995      0/3     
subagents     eval      7/7          0/4          198,370      0/1     
subagents     learn    16/18         0/9          594,974      0/3     
```

Còn thiếu: subagents data-eval/logs-eval và skills-auto cả 6 task. Verify_freeze hiện kiểm tra 0 lượt skill chính thức; OK về lịch sử nhưng chưa chứng minh đủ 6 lượt.

## 8. Phân tích

Trên learn, baseline đạt trung bình 0,664; subagents đạt 0,589 và tốn 5,36 lần token. Dev skills-auto hợp lệ đạt 0,805 (code 9/10, data 5/8, logs 8/9), tăng 0,141 so với baseline learn, nhưng chưa phải kết quả chính thức sau freeze. Skill giúp type hints/changelog và service/sort ở dev, còn thiếu regression filename và schema cụ thể; data đọc skill vẫn xuất tiền theo USD.

Baseline eval đạt 0,597; code-eval subagents đạt 7/11 ngang baseline code-eval và tốn 198370 so với 110439 token. Chưa có đủ subagents eval hoặc bất kỳ skills-auto eval hợp lệ, nên chưa kết luận H1–H3 hay khả năng chuyển sang eval. Check kỹ thuật baseline đạt 18/18 ở cả learn/eval; quy ước đạt 0/9 ở learn và 0/12 ở eval. Quota API là lỗi hạ tầng, không tính điểm 0 của các lượt đó vào bảng so sánh.

Cặp đo nhiễu cần các lượt skills-auto learn sau freeze với đúng bộ skill và model. Hiện chỉ có dev trước freeze, chưa đủ để tính chênh lệch thuần do nhiễu. Các thử Gemini 3.1/Flash nằm riêng và không thể dùng làm cặp đo nhiễu của Flash-Lite 3.5.

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba tác vụ mỗi vai trò: không đại diện cho toàn bộ công việc coding/data/logs thực tế.
2. Mỗi cấu hình chính thức chạy một lần và model dùng sampling cố định: khác biệt có thể do nhiễu, không đủ để kết luận ý nghĩa thống kê.
3. Chỉ một model và một harness: không suy rộng sang provider hoặc mô hình khác.
4. Bài tập cố tình chứa quy ước ẩn: lợi ích có thể đến từ việc truyền quy tắc tổ chức, không phải cải thiện năng lực suy luận chung.
5. Token tính cả subagent; trace và số tool call chỉ phản ánh luồng chính. Không thể suy ra đầy đủ quy trình nội bộ subagent từ báo cáo cuối.

## 10. Kết luận

Harness đã hoàn thiện và ba skill do curator sinh được giữ nguyên sau freeze. Dev cho thấy lợi ích ở một số quy ước nhưng cũng cho thấy đọc skill không đảm bảo tuân thủ. Bộ so sánh chính chưa đủ vì quota ngày 500 request của Flash-Lite 3.5 đã hết, nên chưa kết luận hiệu quả eval. Tiến trình finish_lab.py đã được chuẩn bị để tiếp tục lúc 2026-10-07 00:04:59 UTC (khoảng 07:05 giờ Việt Nam/Thái Lan), chỉ sinh báo cáo hoàn tất khi đủ 18 lượt hợp lệ và verify_freeze đạt.

## Phụ lục

Thực hiện đúng thứ tự GUIDE: offline tests → baseline/subagents learn → curator → skills-auto learn → hypotheses commit → freeze tag → baseline/subagents eval → skills-auto all → verify_freeze → compare/check_breakdown.

Lỗi môi trường: lần baseline code-learn đầu tiên có check tests_not_modified thất bại vì CRLF của checkout Windows. Hash bản test khi chuyển CRLF thành LF khớp hash nhúng của bộ chấm. Runner chuẩn hóa `.py` trong **bản sao sandbox**, giữ nguyên file đề bài; kết quả đầu tiên được lưu riêng tại `results/infrastructure-crlf/` và không dùng trong so sánh chính.

Lựa chọn model: API từ chối gemini-2.5-flash-lite bằng 404 và đề nghị gemini-3.5-flash-lite; probe model mới trả lời OK. Không tính probe vào số lần chạy tác vụ.

Hai lần skills-auto dev code gặp GraphRecursionError tại 60 bước được lưu tại `results/skills-auto-dev-errors/` (9/10 và 8/10); không dùng hai lần lỗi này làm cặp đo nhiễu. Lần dev code hợp lệ chạy với limit 100; dev data/logs giữ limit 60 vì đã kết thúc trước giới hạn. Giới hạn chính thức là 100 cho cả ba điều kiện; đây là điều chỉnh hạ tầng, vẫn cần ghi nhận ảnh hưởng tiềm tàng đến chi phí.

Dev hợp lệ dùng cùng bộ skill: code 9/10 (1 skill đọc, 253179 token, 106,2s), data 5/8 (1 skill đọc, 178036 token, 71,6s), logs 8/9 (1 skill đọc, 86968 token, 56,6s). Đã sao lưu toàn bộ vào results/skills-auto-dev trước freeze. Không sinh lại hoặc xóa skill.

Tag freeze: 74f4a726739df12521ad39155798dc386e184db7; giả thuyết nằm trong commit hypotheses ngay trước tag.

Phục hồi quota: các lượt subagents data/logs eval và skills-auto code-eval bị lỗi 429 được chuyển sang results/quota-errors, không dùng trong bảng chính. Flash 3.5 có quota 20/ngày và không đủ cho một lượt data thử; model 3.8/3.7 gặp 504/503; Gemini 3.1 Flash-Lite có một lượt data lặp lệnh đến limit 100. Các kết quả model khác ở flash-probe và gemini-3.1 giữ riêng. Chỉ kiểm tra models.list của OpenAI, không dùng nó làm bằng chứng key có credit và không chạy thí nghiệm OpenAI.

### Mở rộng 6c: kiểm tra đầu ra đối kháng của curator

Thí nghiệm ngoại tuyến độc lập tại `report/red_team_validator.py`, kết quả riêng ở `results/red-team-validator/results.json`. Sau freeze, tạo 5 chuỗi skill giả lập: 1 control hợp lệ và 4 đầu ra đối kháng (tên chứa ../, định danh eval nguyên văn, định danh chèn khoảng trắng, định danh chèn ký tự zero-width). Gọi đúng validate_skill có sẵn; không gọi LLM, không ghi hay thay đổi skills/auto.

Control được nhận; traversal và định danh nguyên văn bị chặn; hai dạng che giấu định danh đều được nhận. Bộ lọc chặn 2/4 đầu ra đối kháng, so với 1/1 đầu ra control được nhận. Nguyên nhân nằm ở phép dò substring trên text.lower(): khoảng trắng hoặc ký tự vô hình làm gián đoạn marker. Đây là kiểm tra khả năng lọt qua validator, không phải bằng chứng mô hình curator thực tế sẽ tạo nội dung gian lận hoặc official skills đã rò rỉ.

Đề xuất: trong một harness ngoài lab, chuẩn hóa Unicode, loại ký tự vô hình và kiểm tra các biểu diễn token trước khi dò marker; bổ sung review ngữ nghĩa và xác minh provenance học. Chưa sửa validate_skill vì RUBRIC cấm sửa mã có sẵn. Hạn chế: chỉ 4 mẫu thủ công, không đo xác suất tấn công LLM thành công; bước tiếp theo là thử prompt injection trên curator thật với dữ liệu giả và lưu đầy đủ prompt/reply riêng. Có thể chạy lại bằng `docker run --rm -v "${PWD}:/lab" lab-deepagents python report/red_team_validator.py`.
