# docsplit — 코드·정책·프롬프트만 담은 실행 이미지.
# 문서 PDF는 절대 굽지 않는다 (개인정보). data/ 는 실행 시 볼륨으로 붙인다.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# 의존성 먼저 — 소스만 바뀔 때 이 레이어를 재사용한다.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

# 볼륨이 붙기 전에도 경로가 존재하도록 만들어 두고, 비루트 실행에 대비해 열어 둔다.
RUN mkdir -p /app/data /app/outputs /app/results && chmod 777 /app/outputs /app/results

CMD ["docsplit", "run"]
