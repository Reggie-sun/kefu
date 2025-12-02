# Build Caddy with Cloudflare DNS plugin for DNS-01
FROM caddy:2.7-builder AS builder
# 加速 Go 模块下载，避免访问 proxy.golang.org 超时
RUN go env -w GOPROXY=https://goproxy.cn,direct && \
    go env -w GO111MODULE=on && \
    xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2.7
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
