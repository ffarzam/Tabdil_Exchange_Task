# fluentd/Dockerfile

FROM fluent/fluentd:v1.17.1-1.1
USER root
ADD ./fluent.conf /fluentd/etc/fluent.conf

RUN ["gem", "install", "fluent-plugin-elasticsearch", "--no-document"]
USER fluent