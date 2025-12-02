FROM ghcr.io/zhayujie/chatgpt-on-wechat:latest

# 为 gateway / dashboard 补充轻量依赖（避免全量 requirements 构建过慢）
USER root
RUN pip install --no-cache-dir "fastapi==0.121.3" "uvicorn[standard]==0.38.0"
USER noroot

ENTRYPOINT ["/entrypoint.sh"]
