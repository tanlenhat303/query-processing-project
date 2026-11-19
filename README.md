# Query Processing trên MySQL và MongoDB

Đồ án so sánh MySQL 8.4 và MongoDB 8.0 trên cùng dữ liệu thương mại điện tử. Benchmark mặc định tạo 1.000 khách hàng, 500 sản phẩm, 10.000 đơn hàng và 20.000 dòng chi tiết đơn hàng với seed 42.

| Truy vấn | MySQL | MongoDB |
|---|---|---|
| Lọc sản phẩm giá lớn hơn 500 | `WHERE price > 500` | `find` với `$gt` |
| Ghép đơn hàng với khách hàng | `JOIN` | `$lookup` và `$unwind` |
| Tính doanh thu theo khách hàng | `GROUP BY` và `SUM` | `$group` và `$sum` |
| Tìm đơn hàng của khách hàng 100 | `WHERE customer_id = 100` | `find` theo `customer_id` |

Cấu hình ban đầu giữ index khóa chính và index hỗ trợ khóa ngoại của MySQL, cùng index `_id` mặc định của MongoDB. Cấu hình tối ưu thêm hai index MongoDB trên `customers.customer_id` và `orders.customer_id`. Hai lượt đo dùng cùng dữ liệu và cấu hình MySQL.

## 1. Chuẩn bị trên Windows

Cài Docker Desktop đang chạy Linux containers, Python 3.10 trở lên và Node.js 20 trở lên. Mở PowerShell trong thư mục `query_processing_project` chứa `docker-compose.yml` và chạy các lệnh dưới đây. Nếu đến đây từ một thư mục khác, dùng `cd` để vào đúng thư mục đã giải nén.

```powershell
docker compose up -d --wait
docker compose ps
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r benchmark/requirements.txt
```

Cả hai dịch vụ cần ở trạng thái `healthy`. Nếu cổng 3306 hoặc 27017 đã được dùng, dừng dịch vụ đang chiếm cổng trước khi chạy lại Compose. Trên macOS hoặc Linux, thay `py -3` bằng `python3`, `.\.venv\Scripts\python.exe` bằng `./.venv/bin/python`, và `npm.cmd` bằng `npm`.

## 2. Nạp dữ liệu và đo cấu hình ban đầu

`setup.py` tạo lại bốn bảng MySQL và bốn collection MongoDB trong database demo `ecommerce`. Lệnh này xóa dữ liệu cũ của các bảng và collection đó. Chạy từ thư mục gốc của project.

```powershell
.\.venv\Scripts\python.exe benchmark/setup.py --orders 10000
.\.venv\Scripts\python.exe benchmark/run.py --phase baseline --runs 30 --warmups 5 --out runs/results_initial.csv --plans runs/plans_initial.json
.\.venv\Scripts\python.exe benchmark/plot.py runs/results_initial.csv --out runs/comparison_initial.png
```

Benchmark đối chiếu toàn bộ kết quả MySQL và MongoDB của từng truy vấn trước các lượt chạy làm nóng và đo. Với 10.000 đơn hàng, số dòng dự kiến lần lượt là **259, 10.000, 1.000 và 10** theo thứ tự trong bảng. JOIN ban đầu trên MongoDB có thể mất vài phút qua 35 lượt chạy, tùy máy.

## 3. Thêm index MongoDB và đo lần hai

Giữ dữ liệu đã nạp từ bước 2. Dùng `indexes.py` để thêm hai index trên database MongoDB hiện có.

```powershell
.\.venv\Scripts\python.exe benchmark/indexes.py
.\.venv\Scripts\python.exe benchmark/run.py --phase indexed --runs 30 --warmups 5 --out runs/results_indexed.csv --plans runs/plans_indexed.json
.\.venv\Scripts\python.exe benchmark/plot.py runs/results_indexed.csv --out runs/comparison_indexed.png
```

`run.py` kiểm tra danh sách index MongoDB phù hợp với `--phase`. Để chạy lại cả hai lượt từ đầu, quay lại bước 2. Cờ `setup.py --index` có thể dùng khi chỉ cần nạp mới dữ liệu và đo cấu hình tối ưu.

Mỗi CSV đầy đủ có **240 dòng đo**. Giá trị trung vị tính từ 30 lượt đo cho mỗi cặp truy vấn và DBMS. Thời gian đo bao gồm thực thi truy vấn, truyền dữ liệu và giải mã toàn bộ kết quả ở Python client. Hai file JSON lưu phiên bản DBMS, số dòng, danh sách index, `EXPLAIN ANALYZE` của MySQL và `executionStats` của MongoDB. Kế hoạch được thu sau lượt đo. Đối với Customer Filter, so sánh `queries.customer_filter.mongodb_explain` trong hai file, đặc biệt là `winningPlan`, `nReturned`, `totalDocsExamined` và `totalKeysExamined`. Với JOIN, xem thống kê của stage `$lookup` khi kết quả explain có stage này.

Để thử quy mô khác, chạy lại bước 2 và 3 với `--orders` mới, lưu đầu ra sang thư mục riêng và ghi lại cấu hình CPU, RAM, hệ điều hành và Docker đã dùng. Đóng các tác vụ nặng khi đo. Thời gian có thể khác kết quả đã lưu trong báo cáo.

## 4. Chạy web demo

Giữ hai container đang chạy và hoàn thành bước nạp dữ liệu. Mở PowerShell mới trong thư mục gốc của project.

```powershell
cd web
npm.cmd ci
npm.cmd start
```

Mở [http://localhost:3000](http://localhost:3000). Giao diện HTML/JavaScript gọi Express API, sau đó Express truy vấn MySQL.

| Thao tác demo | API | Kết quả |
|---|---|---|
| Nhập giá 500 và bấm **Filter products** | `GET /api/products?minPrice=500` | Tối đa 100 sản phẩm có giá lớn hơn 500 |
| Bấm **Recent orders (JOIN)** | `GET /api/orders` | 50 đơn mới nhất theo mã đơn hàng, kèm tên khách |
| Bấm **Top revenue (GROUP BY)** | `GET /api/revenue` | Tối đa 20 khách hàng có tổng doanh thu cao nhất |

Khi cần minh chứng web, chụp màn hình sau khi từng nút trả dữ liệu. Giữ tiêu đề thao tác và vài dòng kết quả trong ảnh để thấy truy vấn đã chạy.

Nếu web báo `Database unavailable`, chạy `docker compose ps` từ thư mục gốc và kiểm tra đã nạp dữ liệu ở bước 2. Để kết thúc, nhấn Ctrl+C trong cửa sổ chạy Node. Từ thư mục gốc, dùng `docker compose down` để dừng hai DBMS và giữ dữ liệu trong Docker volumes.

## 5. Kết quả tham chiếu

Đây là trung vị tính từ hai bộ CSV đi kèm báo cáo, đơn vị ms.

| Truy vấn | MySQL ban đầu | MongoDB ban đầu | MySQL lần hai | MongoDB thêm index |
|---|---:|---:|---:|---:|
| Filter | 2,61 | 1,74 | 3,12 | 2,12 |
| JOIN | 62,87 | 3.228,09 | 64,89 | 539,50 |
| Aggregation | 15,24 | 6,29 | 17,82 | 7,42 |
| Customer Filter | 1,13 | 3,85 | 1,43 | 1,04 |

Trong thí nghiệm 10.000 đơn, JOIN MongoDB giảm khoảng **83,3%** sau tối ưu index. MySQL vẫn nhanh hơn ở JOIN trong lần đo thứ hai. Kết luận áp dụng cho truy vấn, mô hình dữ liệu và quy mô đã thử.

## Tệp trong bản nộp

- [ReportQueryProcessing.docx](ReportQueryProcessing.docx) chứa báo cáo thực nghiệm.
- [report/evidence/](report/evidence/) chứa CSV và ảnh minh chứng của lần đo gốc.
- [benchmark/](benchmark/) chứa script tạo dữ liệu, quản lý index, đo và vẽ biểu đồ.
- [web/](web/) chứa mã nguồn web demo và tệp khóa dependency.
- Thư mục `runs/` được tạo khi chạy benchmark mới.

## Tài liệu tham khảo

- [MySQL 8.4 Reference Manual — EXPLAIN Statement](https://dev.mysql.com/doc/refman/8.4/en/explain.html)
- [MongoDB 8.0 Manual — Explain Results](https://www.mongodb.com/docs/v8.0/reference/explain-results/)
- [MongoDB 8.0 Manual — $lookup](https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/lookup/)
