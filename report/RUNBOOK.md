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
docker run --rm -v "${PWD}:/lab" lab-deepagents python scripts/check_breakdown.py
```

Không chạy lại lệnh curator sau freeze. Khi tái lập, sao lưu kết quả cũ hoặc dùng `--results` riêng để tránh ghi đè bằng chứng của lần nộp này. `verify_freeze.py` cần chạy trong Linux cùng các lần đo: hàm hash có tên đường dẫn phụ thuộc hệ điều hành. Image bổ sung Git chỉ dùng cho kiểm tra lịch sử, không thay đổi thư viện agent.

`requirements-lock.txt` lưu phiên bản thực tế; khi cần tái lập phiên bản thư viện chính xác, cài các dòng version pin trong file đó, bỏ dòng editable `/lab`. Key không nằm trong image Docker: Dockerfile gốc chỉ COPY pyproject và src.
