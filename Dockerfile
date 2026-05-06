FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY polymarket_bot ./polymarket_bot

ARG INSTALL_EXTRAS=""
RUN python -m pip install --upgrade pip \
    && if [ -n "$INSTALL_EXTRAS" ]; then \
        python -m pip install ".[$INSTALL_EXTRAS]"; \
    else \
        python -m pip install .; \
    fi

RUN useradd --create-home --shell /usr/sbin/nologin botuser
USER botuser

ENTRYPOINT ["polymarket-btc-bot"]
CMD ["--optimized-profile"]
