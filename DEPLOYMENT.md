# Triển khai agent Day 14

## URL public

[https://agent-production-9e5053df.up.railway.app](https://agent-production-9e5053df.up.railway.app)

## Nền tảng

Railway Trial, môi trường `production`. Dịch vụ `agent` build từ Dockerfile trong `06-lab-complete/` và kết nối Redis qua mạng riêng của project. Đường dẫn health check trong cấu hình dịch vụ là `/health`. Endpoint `/ready` kiểm tra kết nối Redis. [Dashboard Railway](https://railway.com/project/47d2e6ea-7e8a-41d6-8089-f5d325390ad7)

Railway ghi startup health check là tắt trong metadata của bản chạy Trial VM. Bốn kết quả dưới đây được xác minh qua HTTPS trên bản triển khai Active.

## Biến môi trường

| Biến | Cấu hình trên Railway |
| --- | --- |
| `PORT` | `8000`, cũng là cổng đích của domain |
| `ENVIRONMENT` | `production` |
| `REDIS_URL` | Tham chiếu `${{Redis.REDIS_URL}}` đến địa chỉ nội bộ của Redis |
| `AGENT_API_KEY` | Lấy giá trị từ mục Variables của dịch vụ `agent` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `DAILY_BUDGET_USD` | `1.0` |

## Tự kiểm

Chạy bằng Bash hoặc WSL. Nhập API key khi terminal yêu cầu. Lệnh chỉ in mã HTTP.

```bash
BASE='https://agent-production-9e5053df.up.railway.app'
read -r -s -p 'API key: ' AGENT_API_KEY
printf '\n'

curl -sS -o /dev/null -w 'GET /health → %{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w 'GET /ready → %{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w 'POST /ask thiếu key → %{http_code}\n' \
  -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w 'POST /ask có key → %{http_code}\n' \
  -X POST "$BASE/ask" -H 'Content-Type: application/json' \
  -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
unset AGENT_API_KEY
```

Kết quả kiểm tra URL public ngày 25/11/2026

| Yêu cầu | HTTP |
| --- | ---: |
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` thiếu API key | 401 |
| `POST /ask` có API key | 200 |

## Ảnh minh chứng

- [Dashboard với agent và Redis Online](screenshots/dashboard.png)
- [Bản triển khai Active trên Railway](screenshots/running.png)
- [Ảnh báo cáo kết quả bốn yêu cầu HTTP thực tế](screenshots/test.png)
