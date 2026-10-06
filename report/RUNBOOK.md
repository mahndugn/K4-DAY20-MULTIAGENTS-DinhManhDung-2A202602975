# Tái lập trên Windows bằng Docker

Để tái lập toàn bộ thí nghiệm, dùng một bản sao starter repo riêng chưa có tag freeze, chép bốn module đã hoàn thiện và các file hỗ trợ trong report vào đó. Chạy PowerShell tại thư mục gốc repo. Điền key của bạn trong `.env`, với duy nhất một dòng `LAB_MODEL=google_genai:gemini-3.5-flash-lite`. Model có thể đổi theo quyền truy cập của tài khoản; không trộn model trong cùng bảng so sánh.

```powershell
docker desktop start
docker build -t lab-deepagents .
docker build -f report/Dockerfile -t lab-deepagents-runner .
docker run --rm -v "${PWD}:/lab" lab-deepagents python -m pytest
docker run --rm -v "${PWD}:/lab" lab-deepagents python scripts/tour.py
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.runner --condition baseline --tasks learn
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.runner --condition subagents --tasks learn
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.curator
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.runner --condition skills-auto --tasks learn --recursion-limit 100
```

Đánh giá từng skill theo GUIDE, giữ nguyên nội dung mô hình sinh. Điền H1–H3 trước khi xem điểm eval. Lưu bản dev và tạo lịch sử đóng băng trên **nhánh thí nghiệm mới**, không ghi đè tag `freeze` của bài nộp hiện có:

```powershell
Move-Item -LiteralPath results/skills-auto -Destination results/skills-auto-dev
git add src/lab/agent.py src/lab/subagents.py src/lab/runner.py src/lab/curator.py skills report results
git commit -m "hypotheses"
git commit --allow-empty -m "freeze skills"
git tag freeze
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.runner --condition baseline --tasks eval --recursion-limit 100
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.runner --condition subagents --tasks eval --recursion-limit 100
docker run --rm --env-file .env -v "${PWD}:/lab" lab-deepagents python -m lab.runner --condition skills-auto --tasks all --recursion-limit 100
docker run --rm -v "${PWD}:/lab" lab-deepagents-runner python scripts/verify_freeze.py
docker run --rm -v "${PWD}:/lab" lab-deepagents python -c "from pathlib import Path; from lab.compare import build_table,load_runs; Path('report/table.md').write_text(build_table(load_runs())+'\n',encoding='utf-8')"
docker run --rm -v "${PWD}:/lab" lab-deepagents-runner python scripts/check_breakdown.py
```

Không chạy lại lệnh curator sau freeze. Khi tái lập, sao lưu kết quả cũ hoặc dùng `--results` riêng để tránh ghi đè bằng chứng của lần nộp này. `verify_freeze.py` cần chạy trong Linux cùng các lần đo: hàm hash có tên đường dẫn phụ thuộc hệ điều hành. verify_freeze và check_breakdown đều cần Git, nên dùng image lab-deepagents-runner; image bổ sung Git không thay đổi thư viện agent.

`requirements-lock.txt` lưu phiên bản thực tế; khi cần tái lập phiên bản thư viện chính xác, cài các dòng version pin trong file đó, bỏ dòng editable `/lab`. Key không nằm trong image Docker: Dockerfile gốc chỉ COPY pyproject và src.

## Bộ so sánh mới khi đổi model

Theo lựa chọn người dùng, lịch chờ quota model 3.5 đã hủy. Bộ mới dùng Gemini 3.1 Flash-Lite, temperature 0 và limit 100; giữ nguyên skill do curator 3.5 sinh. Không chạy lại curator sau khi đã xem eval. Chạy tuần tự trong image gốc:

```powershell
docker run --rm --env-file .env -e LAB_MODEL=google_genai:gemini-3.1-flash-lite -e LAB_TEMPERATURE=0 -e PYTHONWARNINGS=ignore -v "${PWD}:/lab" lab-deepagents python report/run_cohort.py --results results/gemini-3.1-temp0
docker run --rm --env-file .env -e LAB_MODEL=google_genai:gemini-3.1-flash-lite -e LAB_TEMPERATURE=0 -e PYTHONWARNINGS=ignore -v "${PWD}:/lab" lab-deepagents python report/run_cohort.py --results results/repeat-learning --repeat-learning
```

Script bỏ qua bản ghi đã có cùng model/config, kể cả lỗi recursion. Không thử lại để chọn điểm tốt hơn; lỗi API/hạ tầng dừng bộ chạy và cần giữ riêng trước khi tiếp tục. Ba lượt lặp học đều sau freeze, nên dùng để đo nhiễu cùng model, không gọi chúng là dev trước freeze. Dev gốc 3.5 được giữ tại results/skills-auto-dev.

Sau khi đủ 18 bản ghi, chuyển nguyên bộ cũ sang results/previous-gemini-3.5, rồi chuyển ba thư mục điều kiện của bộ mới về results/. Đây là bước quản lý artifact, không sửa nội dung run.json hoặc trace. Chạy verify_freeze và report/finalize_report.py trong image lab-deepagents-runner. Finalizer từ chối bảng trộn model, thiếu lượt, lỗi API/hạ tầng hoặc skill bị sửa; chấp nhận recursion như kết quả hành vi và báo cáo rõ. Không tạo lại tag freeze.
