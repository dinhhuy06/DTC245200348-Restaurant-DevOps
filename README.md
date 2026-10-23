# DTC245200348-Restaurant-DevOps

Triển khai hệ thống quản lý nhà hàng bằng Docker Compose

\## Các thành phần



\- Ứng dụng quản lý nhà hàng.

\- PostgreSQL: lưu trữ dữ liệu.

\- pgAdmin: quản trị cơ sở dữ liệu.

\- Nginx: reverse proxy.

\- Prometheus: thu thập metrics.

\- Nginx exporter và PostgreSQL exporter: cung cấp metrics.

\- cAdvisor: giám sát CPU và RAM container.

\- Grafana: hiển thị dashboard và truy vấn log.

\- Loki và Promtail: lưu trữ và thu thập log Nginx.



\## Khởi động hệ thống đã cấu hình



Yêu cầu Docker Desktop đang chạy và file `.env` đã được điền.



Kiểm tra cấu hình:



```powershell

docker compose -f compose.yaml -f compose.override.yaml -f compose.monitoring.yaml -f compose.logging.yaml config --quiet

```



Khởi động:



```powershell

docker compose -f compose.yaml -f compose.override.yaml -f compose.monitoring.yaml -f compose.logging.yaml up -d

```



Kiểm tra trạng thái:



```powershell

docker compose -f compose.yaml -f compose.override.yaml -f compose.monitoring.yaml -f compose.logging.yaml ps

```



Dừng các dịch vụ, giữ nguyên container và volume:



```powershell

docker compose -f compose.yaml -f compose.override.yaml -f compose.monitoring.yaml -f compose.logging.yaml stop

```



\## Địa chỉ truy cập



| Dịch vụ | Địa chỉ |

|---|---|

| Website | http://localhost:8080 |

| Prometheus | http://localhost:9090 |

| Grafana | http://localhost:3000 |



Grafana sử dụng tài khoản `admin`, mật khẩu được cấu hình bằng

`GRAFANA\_PASSWORD` trong `.env`.



Không đưa file `.env` chứa mật khẩu thật lên GitHub.



\## Giám sát



Trong Prometheus Targets, kiểm tra các job:

`prometheus`, `nginx`, `postgres`, `containers` đều UP.



Dashboard Grafana được lưu tại:

`grafana/restaurant-dashboard.json`.



Các biểu đồ gồm trạng thái PostgreSQL, trạng thái Nginx,

lưu lượng truy cập, CPU và RAM container.



Datasource trong Grafana:



\- Prometheus: `http://prometheus:9090`

\- Loki: `http://loki:3100`



\## Ba truy vấn LogQL



Chạy trong Grafana Explore, chọn datasource Loki.



\### 1. Xem access log Nginx



```logql

{job="nginx", filename="/var/log/restaurant/access.log"}

```



Minh chứng: `screenshots/logql-01-access.png`.



\### 2. Lọc request trả về HTTP 404



```logql

{job="nginx", filename="/var/log/restaurant/access.log"} |= "\\" 404 "

```



Minh chứng: `screenshots/logql-02-404.png`.



\### 3. Đếm request trong 1 giờ



Chọn Type: Instant.



```logql

sum(count\_over\_time({job="nginx", filename="/var/log/restaurant/access.log"}\[1h]))

```



Minh chứng: `screenshots/logql-03-count.png`.



Các truy vấn được lưu trong `loki/queries.logql`.

