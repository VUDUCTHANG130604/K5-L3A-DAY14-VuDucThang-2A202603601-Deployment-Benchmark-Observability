# Day 14 Lab · Mission Answers

## Part 1 · Localhost vs Production

### Exercise 1.1 · Anti-pattern trong bản develop

1. [Đặt thông tin xác thực trong mã nguồn](01-localhost-vs-production/develop/app.py#L17). API key và URL cơ sở dữ liệu có mật khẩu mẫu được khai báo trực tiếp. Nếu dùng thông tin thật, người có quyền xem repo hoặc lịch sử Git có thể đọc được.
2. [Ghi dữ liệu nhạy cảm ra log](01-localhost-vs-production/develop/app.py#L33). App in câu hỏi, API key và câu trả lời bằng `print()`. Log tập trung có thể lưu lại dữ liệu người dùng và key. Các dòng này cũng thiếu trường sự kiện để lọc một cách nhất quán.
3. [Cấu hình ứng dụng bằng hằng số](01-localhost-vs-production/develop/app.py#L20). Các giá trị mẫu như `DEBUG` và `MAX_TOKENS` nằm trong mã, nên khó quản lý cấu hình riêng cho từng môi trường.
4. [Chỉ lắng nghe trên localhost và cố định cổng](01-localhost-vs-production/develop/app.py#L49). App bind vào `localhost:8000`. Proxy bên ngoài container không thể kết nối qua loopback của container, và app không dùng được cổng do nền tảng cấp qua `PORT`.
5. [Luôn bật chế độ tự nạp lại mã](01-localhost-vs-production/develop/app.py#L53). `reload=True` khởi chạy trình theo dõi file, hữu ích khi sửa code trên máy cá nhân nhưng tạo thêm tiến trình khi triển khai.
6. [Thiếu endpoint health và readiness](01-localhost-vs-production/develop/app.py#L42). Hệ thống điều phối không có điểm kiểm tra riêng để biết process còn sống và đã sẵn sàng nhận traffic hay chưa.

### Exercise 1.2 · Chạy bản develop

Chạy `python app.py` trong `01-localhost-vs-production/develop/` bằng Python trong WSL2. Gọi API với tham số `question` trên URL.

```bash
curl -i -X POST 'http://localhost:8000/ask?question=Hello'
```

Kết quả thực tế từ lượt kiểm tra.

```text
HTTP/1.1 200 OK
content-type: application/json

{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

Đây là văn bản do mock LLM trả về khi gọi ứng dụng local.

### Exercise 1.3 · So sánh với bản production

| Tính năng | Develop | Production | Vì sao quan trọng |
| --- | --- | --- | --- |
| Cấu hình | API key, host và cổng nằm trong mã. | [Đọc cấu hình từ môi trường](01-localhost-vs-production/production/config.py#L17). `HOST` mặc định là `0.0.0.0`, `PORT` có thể thay đổi và reload chỉ bật khi `DEBUG=true`. [Điểm khởi chạy](01-localhost-vs-production/production/app.py#L192) | Cùng một bản build có thể chạy trên máy cá nhân, trong container và trên cloud với cấu hình riêng. |
| Health và readiness | Chỉ có `/` và `/ask`. | [`/health`](01-localhost-vs-production/production/app.py#L135) trả trạng thái, uptime và phiên bản. [`/ready`](01-localhost-vs-production/production/app.py#L152) trả `503` khi cờ `is_ready` tắt. | Liveness giúp phát hiện tiến trình gặp sự cố. Readiness giúp load balancer chỉ chuyển traffic tới instance sẵn sàng. |
| Logging | Dùng `print()` và in giá trị API key mẫu. | [Log sự kiện request và response](01-localhost-vs-production/production/app.py#L109) chứa trường như `event`, `question_length` và `response_length`. | Có thể lọc theo sự kiện và quan sát độ dài dữ liệu mà không cần ghi API key hoặc toàn bộ nội dung câu hỏi. |
| Shutdown | Không có bước dọn tài nguyên riêng trong app. | [FastAPI lifespan](01-localhost-vs-production/production/app.py#L39) đánh dấu app chưa sẵn sàng khi bắt đầu tắt và có chỗ để dọn tài nguyên. | Khi thay container, server có thể hoàn tất yêu cầu đang xử lý và app có thể đóng kết nối trước khi thoát. |

Chạy `python app.py` trong `01-localhost-vs-production/production/`. Bản này dùng mock LLM khi chưa đặt `OPENAI_API_KEY`. Các lệnh đã chạy và kết quả quan sát được:

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/ask \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
```

| Request | Mã HTTP thực tế | Phản hồi quan sát được |
| --- | --- | --- |
| `GET /health` | `200 OK` | `status: ok`, `version: 1.0.0`, `environment: development` và `uptime_seconds: 31.1` tại thời điểm gọi. |
| `GET /ready` | `200 OK` | `{"ready":true}`. |
| `POST /ask` | `200 OK` | Trả lại `question: Hello` và câu trả lời từ mock LLM. |

## Part 2 · Docker Containerization

### Exercise 2.1 · Dockerfile cơ bản

1. **Base image.** `FROM python:3.11` cung cấp Python 3.11 cùng môi trường hệ điều hành để cài và chạy ứng dụng. [Dockerfile](02-docker/develop/Dockerfile#L8)
2. **Working directory.** `WORKDIR /app` đặt thư mục làm việc cho các chỉ thị tiếp theo. Đích tương đối của `COPY` và lệnh chạy ứng dụng được tính từ `/app`. [Dockerfile](02-docker/develop/Dockerfile#L11)
3. **Thứ tự `COPY`.** Dockerfile chép `requirements.txt` rồi chạy `pip install` trước khi chép mã ứng dụng. Khi chỉ sửa `app.py`, Docker có thể dùng lại lớp cài thư viện. Khi danh sách thư viện đổi, Docker chạy lại bước cài đặt. [Dockerfile](02-docker/develop/Dockerfile#L14)
4. **`CMD` và `ENTRYPOINT`.** `CMD` cung cấp lệnh mặc định hoặc đối số mặc định, có thể thay bằng đối số sau tên image trong `docker run`. `ENTRYPOINT` đặt chương trình chính mà container chạy. Khi dùng dạng exec với cả hai, các đối số của `CMD` được truyền vào `ENTRYPOINT`. Bản develop dùng `CMD ["python", "app.py"]`. [Dockerfile](02-docker/develop/Dockerfile#L30)

### Exercise 2.2 · Build và chạy bản develop

Build từ thư mục gốc để Dockerfile đọc được cả `02-docker/develop/` và `utils/`. Trong lượt thử này, cổng 8000 trên Windows đã có listener nên Docker cấp một cổng localhost riêng cho container.

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -d --rm --name day14-cp2-dev -p 127.0.0.1::8000 my-agent:develop
docker port day14-cp2-dev 8000/tcp
```

Docker cấp `127.0.0.1:56361` trong lượt đo này. Chờ `GET /health` trả `200 OK` trước khi gọi `POST /ask`. `docker run -d` trả về ID container trước khi Uvicorn sẵn sàng nhận request.

```text
GET  http://127.0.0.1:56361/health                     -> HTTP/1.1 200 OK
{"status":"ok","uptime_seconds":1.0,"container":true}

POST http://127.0.0.1:56361/ask?question=What%20is%20Docker%3F -> HTTP/1.1 200 OK
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3 · Multi-stage build và kích thước image

```bash
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent
```

| Image | `SIZE` hiển thị bởi Docker | Quy đổi sang MB |
| --- | ---: | ---: |
| `my-agent:develop` | 1.67 GB | khoảng 1.670 MB |
| `my-agent:advanced` | 240 MB | 240 MB |

Từ cột `SIZE` đã làm tròn, bản advanced nhỏ hơn khoảng **1.430 MB**, tức **85,6%** theo công thức `(1670 - 240) / 1670 × 100`.

- Stage `builder` cài `gcc`, `libpq-dev` và các gói Python vào `/root/.local`. [Stage builder](02-docker/production/Dockerfile#L16)
- Stage `runtime` dùng `python:3.11-slim`, chép các gói đã cài và mã ứng dụng, rồi chạy Uvicorn dưới user `appuser`. Base image slim và việc để công cụ build ở stage đầu giúp giảm kích thước image cuối. [Stage runtime](02-docker/production/Dockerfile#L36)

### Exercise 2.4 · Compose stack và test qua Nginx

```text
Client (host)
    │ HTTP :80
    ▼
nginx ── HTTP :8000 ──► agent (FastAPI, mock LLM)
                           ├── REDIS_URL  ──► redis:6379
                           └── QDRANT_URL ──► qdrant:6333
```

Bốn service cùng nằm trên mạng Compose `internal`. Nginx là điểm vào từ host và chuyển request đến agent theo tên service. Compose đợi Redis và Qdrant qua health check trước khi khởi động agent. Hai URL được truyền vào agent qua môi trường. Request `/ask` của ví dụ gọi mock LLM trực tiếp. [Compose](02-docker/production/docker-compose.yml) · [Endpoint `/ask`](02-docker/production/main.py#L57)

```bash
# Chạy trong 02-docker/production/ sau khi tạo .env.local
docker compose -p k5-day14-docker up -d --build --wait --wait-timeout 120
docker compose -p k5-day14-docker ps
curl -i http://127.0.0.1/health
curl -i http://127.0.0.1/ask \
  -H 'Content-Type: application/json' -d '{"question":"Explain microservices"}'
```

Kết quả thực tế từ Docker Desktop:

| Kiểm tra | Kết quả |
| --- | --- |
| `docker compose ps` | Cả bốn service đều `Up`. Agent, Redis và Qdrant hiển thị `healthy`. |
| `GET /health` qua cổng 80 | `HTTP/1.1 200 OK`, header `Server: nginx`, body có `status: ok` và `version: 2.0.0`. |
| `POST /ask` qua cổng 80 | `HTTP/1.1 200 OK`, header `Server: nginx`, body chứa câu trả lời JSON từ mock LLM. |

## Part 3 · Cloud Deployment

### Exercise 3.1 · Railway

Agent triển khai từ `06-lab-complete/`. Dockerfile build image Python và chạy Uvicorn trên `0.0.0.0:$PORT`. Redis chạy cùng project qua mạng riêng. Agent nhận `REDIS_URL` qua tham chiếu đến dịch vụ Redis và nhận `AGENT_API_KEY` qua biến môi trường của Railway.

- **URL public** — [Agent Part 6 trên Railway](https://agent-production-9e5053df.up.railway.app).
- **Tự kiểm** — `GET /health` và `GET /ready` trả `200`. `POST /ask` trả `401` khi thiếu API key và `200` khi có API key đúng. [Cấu hình và lệnh kiểm tra](DEPLOYMENT.md) · [Ảnh kết quả](screenshots/test.png)

### Exercise 3.2 · So sánh Railway với Render

| Nội dung | Railway | Render |
| --- | --- | --- |
| Phạm vi file | [`railway.toml`](06-lab-complete/railway.toml) của bài lab khai báo builder Dockerfile và health check `/health` cho một service. Với service Railway mới, đặt các thông số tương ứng trong Settings vì Railway đã ngừng cho service mới bật Config as Code dạng TOML/JSON. | [`render.yaml` mẫu](03-cloud-deployment/render/render.yaml) là Blueprint có thể khai báo web service và kho Redis trong cùng file. Bản mẫu dùng Python runtime, lệnh cài thư viện và lệnh khởi động. Nếu triển khai agent Part 6 bằng Docker, Blueprint sẽ dùng `runtime: docker` và trỏ `rootDir` tới `06-lab-complete`. |
| Redis và secret | Tạo Redis trong project Railway, gán `REDIS_URL` bằng tham chiếu tới biến của Redis và đặt `AGENT_API_KEY` ở Variables. | Blueprint có thể nối `REDIS_URL` qua `fromService` với `property: connectionString` và yêu cầu Render tạo hoặc nhập `AGENT_API_KEY` qua `generateValue` hoặc `sync: false`. |

Thiết lập Railway trong bài này chia phần build, health check và phần cấp phát Redis qua các thiết lập của project. Blueprint Render có thể khai báo các dịch vụ và liên kết giữa chúng trong cùng một file để tái tạo môi trường từ repo. [Railway Config as Code](https://docs.railway.com/config-as-code) · [Render Blueprint](https://render.com/docs/blueprint-spec)

### Exercise 3.3 · Pipeline Cloud Run

1. Cloud Build cài thư viện và chạy `pytest` ở bước `test`.
2. Khi bước test thành công, Docker build image với hai tag `$COMMIT_SHA` và `latest`, sau đó push cả hai tag lên registry.
3. Bước deploy dùng tag commit để triển khai lên Cloud Run ở `asia-southeast1`, cấu hình tài nguyên, giới hạn scale và đọc secret từ Secret Manager.
4. Manifest `service.yaml` mô tả thêm cổng 8000, concurrency 80, timeout 60 giây, liveness probe `/health` và startup probe `/ready`. [Pipeline](03-cloud-deployment/production-cloud-run/cloudbuild.yaml) · [Manifest](03-cloud-deployment/production-cloud-run/service.yaml)

## Part 4 · API Security

### Exercise 4.1 · X-API-Key

`POST /ask` gọi dependency `verify_api_key` để đọc header `X-API-Key` và đối chiếu với `AGENT_API_KEY`. Trong bản develop, thiếu key trả `401`, key sai trả `403` và key hợp lệ cho phép xử lý câu hỏi. Để đổi key của bản mẫu, đặt giá trị mới cho biến môi trường, khởi động lại app và cập nhật các client. [Mã xác thực](04-api-gateway/develop/app.py#L39)

Trích phản hồi `curl -i` trong hai lượt thử với body `{"question":"Hello"}`:

```text
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

```text
HTTP/1.1 200 OK
content-type: application/json

{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

### Exercise 4.2 · JWT

Đăng nhập bằng tài khoản demo `student` qua `POST /auth/token`. Log của Uvicorn xác nhận endpoint trả `200 OK`. App ký JWT có thông tin tài khoản, role và thời hạn 60 phút. Client gửi `Authorization: Bearer <JWT>` vào `POST /ask`. App kiểm tra chữ ký và thời hạn trước khi dùng role để chọn rate limiter. Token được giữ trong biến shell `TOKEN` trong lúc thử nghiệm. [Endpoint cấp token](04-api-gateway/production/app.py#L105) · [Mã kiểm tra JWT](04-api-gateway/production/auth.py#L46)

### Exercise 4.3 · Rate limiting

Rate limiter lưu thời điểm các lượt gọi đã được chấp nhận trong một `deque` theo tài khoản. Mỗi lần gọi, app bỏ các thời điểm ngoài cửa sổ 60 giây rồi kiểm tra số lượt còn lại. Role `user` có 10 lượt/phút, role `admin` có 100 lượt/phút. Khi đạt giới hạn, app trả `429` và `Retry-After` dựa vào thời điểm lượt cũ nhất hết hạn. [Mã rate limiter](04-api-gateway/production/rate_limiter.py#L30)

Thử liên tiếp 12 request bằng JWT của `student`. Lượt **1–10 trả 200**, lượt **11–12 trả 429**. Một request tiếp theo dùng `curl -i` cho phản hồi sau:

```text
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795596922
retry-after: 59
content-type: application/json

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4 · Cost guard

- Trước mỗi lượt gọi LLM, `check_budget()` đối chiếu chi phí đã dùng với ngưỡng của tài khoản và toàn hệ thống. Bản mẫu đặt ngưỡng **1 USD/ngày mỗi tài khoản** và **10 USD toàn hệ thống**. Khi chạm ngưỡng, app trả `402` cho tài khoản hoặc `503` khi hết ngân sách toàn hệ thống. [Kiểm tra ngân sách](04-api-gateway/production/cost_guard.py#L60)
- Sau khi có phản hồi, `record_usage()` cộng token đầu vào, token đầu ra và chi phí theo đơn giá mỗi 1.000 token. Bản mẫu lưu số liệu trong bộ nhớ của tiến trình. Nếu triển khai nhiều replica và dùng ngân sách tháng theo đề, có thể duy trì một bộ đếm Redis theo tài khoản và tháng, đặt TTL và cập nhật số tiền bằng thao tác nguyên tử. [Ghi nhận token và chi phí](04-api-gateway/production/cost_guard.py#L93)
- Rate limit bảo vệ tốc độ gọi. Cost guard bảo vệ ngân sách vì hai request có thể dùng số token và chi phí khác nhau. Các mã `402` và `503` ở mục này được đối chiếu từ mã nguồn.

## Part 5 · Scaling & Reliability

### Exercise 5.1 · Health và readiness

| Endpoint | Vai trò | Kết quả quan sát được trên bản develop |
| --- | --- | --- |
| `GET /health` | Liveness cho biết tiến trình còn phản hồi. Body cung cấp thêm uptime, phiên bản và tình trạng bộ nhớ. | `HTTP/1.1 200 OK`, `status: ok`, kiểm tra bộ nhớ `ok`. |
| `GET /ready` | Readiness cho biết agent có thể nhận traffic. Bản develop bật cờ sau startup và trả `503` khi cờ sẵn sàng tắt. | `HTTP/1.1 200 OK`, `ready: true`. |

[Health](05-scaling-reliability/develop/app.py#L104) · [Readiness](05-scaling-reliability/develop/app.py#L147)

### Exercise 5.2 · Graceful shutdown

Trong WSL2, chạy bản develop dưới dạng background job. Gửi `POST /ask?question=Long%20task` rồi gửi `SIGTERM` sau 0,5 giây khi mock LLM đang xử lý. Log ghi nhận theo thứ tự:

```text
INFO:     Shutting down
INFO:     127.0.0.1:53344 - "POST /ask?question=Long%20task HTTP/1.1" 200 OK
INFO:     Waiting for application shutdown.
2026-11-25 16:01:15,210 INFO ✅ Shutdown complete
INFO:     Application shutdown complete.
INFO:     Finished server process [2993]
```

Request đang chạy vẫn nhận câu trả lời JSON và `200 OK` trước khi Uvicorn thoát. Khi chạy phần shutdown của FastAPI lifespan, app hạ cờ readiness, kiểm tra các request đang xử lý và ghi log kết thúc. [FastAPI lifespan](05-scaling-reliability/develop/app.py#L42)

### Exercise 5.3 · Thiết kế stateless

Nếu mỗi agent lưu hội thoại trong RAM, một request chuyển sang replica khác sẽ đọc một bộ nhớ riêng. Khi agent khởi động lại, state trong RAM của tiến trình cũng mất. Trong stack mẫu, mỗi replica dùng `session_id` để đọc và ghi lịch sử qua Redis. Nhờ đó request sau có thể được chuyển đến bất kỳ replica nào trong cụm. [Lưu và đọc session](05-scaling-reliability/production/app.py#L59) · [Endpoint chat](05-scaling-reliability/production/app.py#L128)

### Exercise 5.4 · Nginx load balancing

Chạy từ `05-scaling-reliability/production/` với file `.env.local` đã tạo:

```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3 --wait --wait-timeout 120
docker compose -p k5-day14-scaling ps
curl -i http://localhost:8080/health
```

Compose liệt kê ba container agent ở trạng thái `healthy`, cùng Redis `healthy` và Nginx `Up`. `GET /health` qua cổng 8080 trả `HTTP/1.1 200 OK`, có header `X-Served-By`, body chứa `"storage":"redis"` và `"redis_connected":true`. Nginx chuyển request đến các agent qua upstream `agent:8000`. [Docker Compose](05-scaling-reliability/production/docker-compose.yml) · [Nginx upstream](05-scaling-reliability/production/nginx.conf#L7)

### Exercise 5.5 · Kiểm tra lịch sử qua nhiều instance

Chạy `python test_stateless.py`. Script gửi năm request `POST /chat` với cùng một session rồi đọc lịch sử:

| Lượt | Instance xử lý |
| ---: | --- |
| 1 | `instance-1d9677` |
| 2 | `instance-0dcbdb` |
| 3 | `instance-70b807` |
| 4 | `instance-1d9677` |
| 5 | `instance-0dcbdb` |

Kết quả thực tế là **5 request qua 3 instance**, lịch sử có **10 tin nhắn** gồm 5 câu hỏi và 5 câu trả lời. Khi Nginx chuyển các lượt gọi sang các replica khác nhau, Redis vẫn cung cấp đầy đủ lịch sử đã lưu của session cho request đọc cuối cùng. [Script kiểm tra](05-scaling-reliability/production/test_stateless.py)

## Part 6 · Final Project

Agent đọc cấu hình từ môi trường, nhận `POST /ask` với body JSON, kiểm tra API key và giữ state rate limit cùng chi phí theo ngày UTC trong Redis. Redis sorted set và một thao tác Lua nguyên tử chia sẻ cửa sổ 60 giây giữa các worker. Uvicorn nhận `SIGTERM` trực tiếp, hoàn tất request đang xử lý rồi gọi FastAPI lifespan để đóng Redis client. [Agent](06-lab-complete/app/main.py) · [Dockerfile](06-lab-complete/Dockerfile)

### Checklist Deliverable · CP5

Chạy `python check_production_ready.py` trong `06-lab-complete/` bằng Python WSL2 và dùng CLI Docker Desktop trên Windows để thực hiện các lệnh Docker. Trích phần kết quả của script chấm đầy đủ:

```text
📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 41/41 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

- Script đo image **63 MB**. Khi Redis mất kết nối, `/health` vẫn trả `200` và `/ready` trả `503`.
- Với ngưỡng 5 lượt/phút, request thứ sáu nhận `429`. Sau khi khởi động lại agent, request dùng cùng key vẫn nhận `429`.
- Khi script đặt ngân sách rất thấp, agent trả `402`. Phép thử log đọc được 12 dòng JSON.
- Request đang xử lý vẫn nhận `200` khi script gửi `SIGTERM`. `docker stop` hoàn tất trong **0,6 giây**, exit code **0**.
- Kiểm tra thêm bằng Compose tại cổng local `18000`: `/health` và `/ready` trả `200`. `/ask` trả `200` với key đúng, `401` khi thiếu key và `422` khi câu hỏi chỉ gồm khoảng trắng.

## AI log

- **CP1 · 25/11/2026.** Học viên hỏi cách chạy các bước CP1 và cách xử lý lỗi cài thư viện trong WSL. Codex tạo môi trường Python trong home Ubuntu, cài thư viện CP1, đối chiếu mã hai bản và soạn phần trả lời. Học viên tự kích hoạt môi trường, chạy cả hai bản trong WSL và gửi log Uvicorn. Codex gọi các endpoint trên ứng dụng học viên đang chạy để ghi kết quả HTTP thực tế vào bài.
- **CP2 · 25/11/2026.** Học viên yêu cầu thực hiện checkpoint tiếp theo. Codex đọc Dockerfile và Compose, build hai image trên Docker Desktop, chạy container và stack, gọi API local, ghi kích thước từ `docker images` và soạn câu trả lời. Các số đo và mã HTTP ở Part 2 lấy từ phiên chạy này. Học viên tự chạy lại lệnh kiểm tra trong PowerShell, xác nhận kích thước hai image, gọi thành công container develop và hai endpoint qua Nginx, rồi dừng stack bằng `docker compose down`.
- **CP3 · 25/11/2026.** Học viên hỏi cách chạy xác thực API key, JWT và rate limit. Codex đối chiếu mã nguồn, đưa lệnh cho hai terminal và xử lý job Uvicorn bị tạm dừng chiếm cổng 8000. Học viên tự chạy hai app trong WSL, lấy JWT, gửi request và cung cấp log có các mã `401`, `200` và `429`. Codex ghi lại bằng chứng và giải thích cơ chế rate limit, cost guard từ mã nguồn.
- **CP4 · 25/11/2026.** Học viên hỏi các bước kiểm tra health, graceful shutdown và stateless. Codex đối chiếu ứng dụng, stack và script kiểm thử rồi đưa lệnh WSL2 và PowerShell. Học viên tự gửi `SIGTERM` trong lúc request đang chạy, khởi động ba replica, chạy `test_stateless.py` và cung cấp log. Codex ghi kết quả và giải thích từ log cùng mã nguồn.
- **CP5 · 25/11/2026.** Học viên yêu cầu hướng dẫn rồi yêu cầu Codex hoàn thiện CP5. Học viên tự tạo venv, chỉnh cấu hình, Redis client, `/health`, `/ready` và `.env.example`, rồi cung cấp log xác nhận `/health` trả 200 và `/ready` trả 503 khi Redis mất kết nối. Codex tiếp tục viết xác thực, rate limit, cost guard, log JSON, graceful shutdown và cấu hình Docker, Railway. Codex chạy script chấm gốc trong WSL2 với Docker Desktop và lưu kết quả `PASS 12/12` ở trên.
- **CP6 · 25/11/2026.** Học viên yêu cầu làm CP6 và tự đăng nhập để cấp quyền Railway CLI. Codex tạo project Railway Trial, triển khai agent Part 6 cùng Redis, cấu hình biến môi trường và xác minh bốn mã HTTP `200`, `200`, `401`, `200` trên URL public. Codex lưu ảnh dashboard, bản triển khai Active và kết quả kiểm tra, đồng thời viết phần so sánh Render và mô tả pipeline Cloud Run.
- **CP7 · 25/11/2026.** Học viên yêu cầu tiếp tục CP7. Codex thêm và kiểm tra histogram độ dài câu hỏi, chạy load test và eval v1/v2 trên WSL2, lưu baseline, bổ sung hai mục knowledge base, rồi chạy lại quality gate. Kết quả lấy từ 10 JSON do script tạo và được đối chiếu với các bảng trong `BENCHMARK_REPORT.md`.
- **CP8 · 25/11/2026.** Học viên tự chạy lượt Locust 1 replica trong WSL. Codex chẩn đoán và sửa Dockerfile để agent dùng đúng virtualenv, chạy lượt 3 replica, đo hai alert firing đồng thời và đối chiếu hai trace với log Docker. Codex gom JSON/CSV và điền báo cáo bằng số đo thực tế. Codex chụp đủ bốn ảnh trên Grafana, Jaeger và Prometheus. Ảnh alert lấy từ lượt tái hiện A–B.
