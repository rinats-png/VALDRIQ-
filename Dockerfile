FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN useradd --system --uid 10001 --create-home valdriq && mkdir -p /app/data && chown -R valdriq:valdriq /app/data
USER valdriq
ENV PYTHONUNBUFFERED=1 VALDRIQ_HOST=0.0.0.0 VALDRIQ_DB=/app/data/valdriq.db
EXPOSE 8765
CMD ["python", "-m", "valdriq"]
