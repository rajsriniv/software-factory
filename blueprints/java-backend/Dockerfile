ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /app
COPY target/java-backend-*.jar app.jar
USER 65532:65532
ENTRYPOINT ["java","-jar","/app/app.jar"]
