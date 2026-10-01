FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY line_shop_bot ./line_shop_bot
COPY menu.example.json ./
RUN pip install --no-cache-dir .
RUN useradd --create-home bot && chown bot /app
USER bot
EXPOSE 8000
CMD ["uvicorn", "line_shop_bot.app:main", "--factory", "--host", "0.0.0.0", "--port", "8000"]
