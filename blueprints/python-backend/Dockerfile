ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
USER 65532:65532
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
