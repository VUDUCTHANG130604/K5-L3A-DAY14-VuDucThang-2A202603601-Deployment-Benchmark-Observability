# Benchmark & Observability Report — Day 14

- **Họ tên** Vũ Đức Thắng
- **Ngày chạy CP7** 25/11/2026
- **Môi trường CP7** Ubuntu 24.04 trên WSL2, Python 3.12.3, `mock-llm-small`. Agent v1 chạy trên cổng 8001, v2 trên cổng 8002. Số liệu chi phí là ước tính của mock LLM.

**Dữ liệu CP7:** [JSON load test và eval](06-lab-complete/benchmark-observability/develop/reports/)

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của `load_test.py`, theo dõi thời gian đáp ứng của 95% request thành công. |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của `load_test.py`, đo tỉ lệ request trả lỗi hoặc mất kết nối. |
| Accuracy trên golden dataset | ≥ 85% cho CI | Mức quality gate của bài tập. Lượt nghiệm thu bản v2 sau sửa yêu cầu 100% và 0 regression. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### Kiểm tra metrics

Sau khi gọi `POST /ask` với câu hỏi về Prometheus, `GET /metrics` có các dòng sau:

```text
# TYPE http_requests_total counter
# TYPE agent_in_flight_requests gauge
# TYPE http_request_duration_seconds histogram
# TYPE agent_question_length_chars histogram
agent_question_length_chars_count 1.0
agent_question_length_chars_sum 40.0
```

Counter đếm request HTTP. Gauge biểu diễn số request đang xử lý. Histogram ghi phân bố thời gian xử lý hoặc độ dài câu hỏi theo bucket. Gán URL thực tế cho label `route` có thể tạo hàng nghìn time series khi có URL lạ. Dùng route template và giá trị `unmatched` giữ số lượng label ổn định hơn. [Middleware và histogram mới](06-lab-complete/benchmark-observability/develop/app.py)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.28 | 195.0 | 222.7 | 1686.2 | 2.33% | FAIL · error rate |
| 10 | 37.23 | 189.8 | 219.9 | 1690.7 | 0.67% | PASS |
| 50 | 110.65 | 197.8 | 280.2 | 1704.7 | 1.33% | PASS |
| 100 | 145.27 | 206.7 | 336.9 | 1719.4 | 1.67% | PASS |

Mỗi lượt đo gửi 300 request sau một request warm-up, với `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`. RPS tăng dưới tuyến tính. Tăng concurrency từ 50 lên 100 chỉ nâng throughput từ 110.65 lên 145.27 req/s, khoảng 31%, và p95 tăng từ 280.2 lên 336.9 ms. Ở tải cao hơn, thời gian xử lý và chờ của các request làm giảm lợi ích từ việc gửi thêm lượt song song. Các phép đo này dùng chung một máy cho client lẫn server.

Lượt concurrency 1 vượt ngưỡng error rate vì ghi nhận 7 phản hồi `503` trên 300 request. p95 của lượt đó vẫn đạt ngưỡng. [Kết quả 1](06-lab-complete/benchmark-observability/develop/reports/load_v2_c1.json) · [10](06-lab-complete/benchmark-observability/develop/reports/load_v2_c10.json) · [50](06-lab-complete/benchmark-observability/develop/reports/load_v2_c50.json) · [100](06-lab-complete/benchmark-observability/develop/reports/load_v2_c100.json)

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 191.0 | 219.2 | 228.2 |
| 0.03 (mặc định) | 235.7 | 220.9 | 1687.3 |
| 0.1 | 346.6 | 1690.1 | 1705.3 |

Mỗi lượt gửi 300 request ở concurrency 20 và giữ `MOCK_ERROR_RATE=0.01`. Khi tăng tỉ lệ request chậm từ 0% lên 3%, p99 tăng từ 228.2 lên 1687.3 ms, trong khi p95 chỉ thay đổi 1.7 ms. Ở mức 10%, p95 lên 1690.1 ms và vượt SLO 500 ms, dù trung bình là 346.6 ms. Percentile giúp thấy nhóm người dùng phải chờ lâu mà số trung bình làm mờ đi. [Kết quả 0%](06-lab-complete/benchmark-observability/develop/reports/load_v2_slow_0.json) · [3%](06-lab-complete/benchmark-observability/develop/reports/load_v2_slow_0.03.json) · [10%](06-lab-complete/benchmark-observability/develop/reports/load_v2_slow_0.1.json)

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | **100% (23/23)** |
| Avg tokens / câu | 56.7 | 109.1 | 115.7 |
| Tổng cost (USD) | 0.000399 | 0.000762 | 0.000808 |
| Cost / câu đúng (USD) | 0.00039855 | 0.00003627 | 0.00003515 |
| Latency p95 (ms) | 192.8 | 223.9 | 208.2 |
| Quality gate | FAIL (80%) | PASS (80%, 0 regression so với v1) | **PASS (100%, 0 regression so với v2 trước sửa)** |

Các lượt eval dùng cùng bộ 23 câu và đặt `MOCK_ERROR_RATE=0` để đo chất lượng câu trả lời tách khỏi lỗi upstream giả lập. [Eval v1](06-lab-complete/benchmark-observability/develop/reports/eval_v1.json) · [Eval v2](06-lab-complete/benchmark-observability/develop/reports/eval_v2.json) · [Eval v2 sau sửa](06-lab-complete/benchmark-observability/develop/reports/eval_v2_fixed.json)

**Những câu v2 trả lời sai ban đầu và cách sửa**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm mục về JWT và API key, giải thích chữ ký và thời hạn của token. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm mục về Kubernetes HPA và các chỉ số điều chỉnh số replica. |

Retrieval của v2 làm tăng số token trung bình từ 56.7 lên 109.1 và p95 từ 192.8 lên 223.9 ms trong lượt eval đầu. Số câu đúng tăng từ 1 lên 21, nên chi phí trên mỗi câu đúng giảm từ 0.00039855 xuống 0.00003627 USD. Sau khi bổ sung hai mục knowledge base, v2 đạt 23 câu đúng và chi phí trên mỗi câu đúng giảm tiếp còn 0.00003515 USD. Chỉ số này phản ánh chi phí để có được một câu trả lời đạt yêu cầu trên cùng bộ eval.

**Quality gate trong CI**

Sau khi khởi động agent và chờ `/health` trả 200, CI chạy `run_eval.py` với `--min-accuracy 0.85` và `--baseline` trỏ tới report của bản đã duyệt. Script trả exit code 0 khi đạt ngưỡng và giữ được các câu baseline đã trả lời đúng. Khi trả exit code 1, bước CI thất bại. Đặt kiểm tra này là bắt buộc trước khi merge. Lượt thử thực tế dùng v1 so với baseline v2 trả **exit code 1** và đánh dấu **20 regression**. Lượt nghiệm thu v2 dùng `--min-accuracy 1.0 --baseline reports/eval_v2.json` trả **exit code 0**. [Script eval](06-lab-complete/benchmark-observability/develop/eval/run_eval.py)

---

## 4. Observability stack (production)

### 4.1 Dashboard và ảnh minh chứng

Chạy một lượt quan sát riêng với 30 người dùng Locust, tăng 5 người dùng mỗi giây, trên 3 replica v2. Số đo Prometheus lúc **20:30:27 (UTC+7)**, trước khi bật lỗi mô phỏng. [Grafana tại khoảng thời gian đo](http://localhost:3000/d/day14-agent-overview/day-14-e28094-ai-agent-overview?from=1795613352251&to=1795613427251)

| Chỉ số | Quan sát |
| --- | --- |
| Latency `POST /ask` | Trung bình **251.2 ms**, p95 **396.6 ms**. Khoảng chênh **145.4 ms** cho thấy nhóm request chậm phải chờ lâu hơn mức trung bình. |
| Phân tải qua Nginx | Ba replica nhận lần lượt **6.23**, **6.30** và **6.21 req/s** trong cửa sổ truy vấn 1 phút. Lưu lượng chia gần đều trong mẫu này. |
| Token | Input **1376.2 token/s**, output **731.9 token/s**. Đầu vào gồm câu hỏi, system prompt và ngữ cảnh v2 truy xuất. |
| `GET /metrics` qua Nginx | **HTTP 404**. Prometheus scrape trực tiếp từ các replica trong mạng Docker. |

- [x] [grafana-dashboard.png](screenshots/grafana-dashboard.png) — Golden Signals khi có tải.
- [x] [jaeger-slow-trace.png](screenshots/jaeger-slow-trace.png) — trace chậm và span LLM.
- [x] [jaeger-error-trace.png](screenshots/jaeger-error-trace.png) — trace lỗi và event `exception`.
- [x] [prometheus-alert-firing.png](screenshots/prometheus-alert-firing.png) — hai alert cùng `firing` trên [trang Alerts](http://localhost:9090/alerts).

Ảnh Grafana chụp tại khoảng thời gian chuẩn nêu trên. Panel p95 hiển thị điểm lấy mẫu cuối của biểu đồ, còn bảng ghi truy vấn tức thời tại 20:30:27. Ảnh Prometheus lấy từ lượt tái hiện A–B với 30 người dùng Locust. Thời gian tới firing ở mục 4.2 lấy từ lần đo đầu.

### 4.2 Thí nghiệm lỗi mô phỏng

Giữ tải 30 người dùng và áp dụng đồng thời A và B lúc **20:30:27 (UTC+7)**. Poll API Prometheus mỗi 2 giây và ghi lần đầu quan sát được `firing`, tính từ lúc chạy lệnh áp dụng cấu hình. Cả hai cùng `firing` lúc **20:32:51 (UTC+7)**.

| Thí nghiệm | Alert | Thời gian tới firing | Panel |
| --- | --- | ---: | --- |
| A · `MOCK_ERROR_RATE=0.20` | `AgentHighErrorRate` | **89.2 giây** · tỉ lệ 5xx 19.6% lúc quan sát | Error rate |
| B · `MOCK_SLOW_RATE=0.30` | `AgentHighLatencyP95` | **143.8 giây** · p95 1.89 giây lúc quan sát | Latency p95 |

`promtool test rules` báo `SUCCESS`. A vượt 5% lỗi 5xx trong ít nhất 1 phút. B vượt p95 1 giây trong ít nhất 2 phút. Khi chuyển sang v1, đo accuracy và regression trên golden dataset như CP7 để phát hiện câu trả lời sai dù các chỉ số hạ tầng vẫn nằm trong ngưỡng.

### 4.3 Trace và log

- **Trace chậm** `71c10c40841b41cf316c59f3c5b78e15` có tổng thời gian **1736.7 ms**. Span `chat mock-llm-small` mất **1709.8 ms**, tức **98.5%** tổng thời gian. [Mở trace chậm](http://localhost:16686/trace/71c10c40841b41cf316c59f3c5b78e15)
- **Trace lỗi** `696c6ceb4336b05db235e8b728bb33e1` có tổng thời gian **112.0 ms**. Span `chat mock-llm-small` mất **88.0 ms**, có status `ERROR` và event `exception` do mock upstream trả 503. [Mở trace lỗi](http://localhost:16686/trace/696c6ceb4336b05db235e8b728bb33e1)

Hai dòng log JSON lấy từ Docker có `trace_id` tương ứng:

```jsonl
{"ts": "2026-11-25T13:31:22.721491+00:00", "level": "INFO", "service": "observable-agent", "instance": "439c819fb9fa", "event": "http_request", "trace_id": "71c10c40841b41cf316c59f3c5b78e15", "span_id": "c5dcaabfc221f685", "request_id": "c8a4c840f3f8", "method": "POST", "route": "/ask", "status": 200, "ms": 1736.1}
{"ts": "2026-11-25T13:31:33.673858+00:00", "level": "INFO", "service": "observable-agent", "instance": "c52208f6c4c3", "event": "llm_error", "trace_id": "696c6ceb4336b05db235e8b728bb33e1", "span_id": "fb87914f86f8a3b6", "request_id": "455db6d5c806", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Dùng đúng dòng `POST /ask` trong mỗi CSV, gồm 100 người dùng, ramp-up 10 người dùng/giây và thời lượng 2 phút. Hai lượt dùng cấu hình mô phỏng mặc định, trước thí nghiệm A–B.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 62.69 | 190 | 260 | 1700 | 68/7169 (0.95%) |
| 3 | 60.77 | 190 | 400 | 1700 | 66/7070 (0.93%) |

Trong lượt đo này, RPS từ **62.69** xuống **60.77** và p95 từ **260** lên **400 ms**. p99 giữ **1700 ms**. Locust mô phỏng người dùng có khoảng nghỉ, nên tải gửi vào bị giới hạn bởi cả 100 người dùng lẫn thời gian chờ giữa request. Kết quả của một lượt mỗi cấu hình chưa đủ để kết luận về mức tải bão hòa. Ở trace chậm đã phân tích, thời gian nằm chủ yếu ở mock LLM, phần độ trễ mà thêm replica không rút ngắn cho từng request. [CSV 1 replica](benchmark-results/scale_1_stats.csv) · [CSV 3 replica](benchmark-results/scale_3_stats.csv)

## 6. Kết luận

1. Xem avg cùng p95 và p99 để biết nhóm request nào chịu độ trễ cao. Với tải 30 người dùng, p95 lớn hơn avg khoảng **145.4 ms**.
2. Nginx chia gần đều tải trên 3 replica trong mẫu xem dashboard. Benchmark vẫn cần số đo cùng điều kiện để đánh giá throughput và độ trễ khi scale.
3. Alert cho biết triệu chứng ở mức hệ thống. Trace và log cùng ID cho biết request cụ thể chậm ở span nào hoặc lỗi vì gì.

Khi triển khai thật, theo dõi thêm mã **502/504 ở Nginx** và cảnh báo khi tỉ lệ này tăng. Probe bên ngoài giúp phát hiện trường hợp request lỗi ở tầng proxy trước khi agent ghi metric.
