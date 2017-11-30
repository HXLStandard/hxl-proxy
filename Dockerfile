FROM alpine:3.6

ARG APPUSER_GID=4000
ARG APPUSER_UID=4000
ARG S6_VERSION=1.21.2.1
# ARG VERSION=1.4

WORKDIR /srv/www

COPY . .

# RUN mkdir -p \
#         /srv/db \
#         /srv/config \
#         /srv/cache \
#         /srv/output \
#         /var/log/proxy

# COPY config.py.TEMPLATE hxl_proxy/schema.sql hooks/docker_files/* /srv/config/

RUN addgroup -g $APPUSER_GID -S appuser && \
    adduser -u $APPUSER_UID -s /sbin/nologin -g 'Docker App User' -h /home/appuser -D -G appuser appuser && \
    apk update && \
    apk upgrade && \
    apk add \
        curl \
        nano \
        python3 \
        sqlite && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    rm -r /root/.cache && \
    curl -sL https://github.com/just-containers/s6-overlay/releases/download/v1.21.2.1/s6-overlay-amd64.tar.gz -o /tmp/s6.tgz && \
    tar xzf /tmp/s6.tgz -C / && \
    rm -f /tmp/s6.tgz && \
    mkdir -p \
        /etc/services.d/hxl \
        /srv/db \
        /srv/cache \
        /srv/config \
        /srv/output \
        /var/log/proxy && \
    mv config.py.TEMPLATE docker_files/config.py docker_files/gunicorn.py hxl_proxy/schema.sql /srv/config/ && \
    mv docker_files/hxl_run /etc/services.d/hxl/run && \
    mv docker_files/app.py . && \
    pip3 install --upgrade \
        pip && \
    pip3 install --upgrade \
        gunicorn \
        requests-cache && \
    pip3 install --upgrade -r requirements.txt && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/*

ENTRYPOINT ["/init"]

CMD []
