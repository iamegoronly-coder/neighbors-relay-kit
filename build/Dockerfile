# Ubuntu 24.04; immutable multi-platform image, build with linux/amd64.
FROM ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55 AS builder
ENV DEBIAN_FRONTEND=noninteractive
COPY build/packages.lock /tmp/packages.lock
RUN apt-get update && \
    awk '{print $1 "=" $2}' /tmp/packages.lock | xargs apt-get install -y --no-install-recommends --allow-downgrades && \
    dpkg-query -W | LC_ALL=C sort > /tmp/actual-packages && \
    LC_ALL=C sort /tmp/packages.lock > /tmp/expected-packages && \
    diff -u /tmp/expected-packages /tmp/actual-packages
COPY . /kit
ARG BUILD_RUN=1
RUN test -n "$BUILD_RUN" && sh /kit/scripts/build-canonical.sh /out
FROM scratch AS artifact
COPY --from=builder /out/ /
