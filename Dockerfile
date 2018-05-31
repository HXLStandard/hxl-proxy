FROM unocha/alpine-base-s6-python3:latest

WORKDIR /srv/www

COPY . .

RUN apk update && \
    apk upgrade && \
    apk add \
        sqlite && \
    mkdir -p \
        /etc/services.d/hxl \
        /srv/db \
        /srv/cache \
        /srv/config \
        /srv/output \
        /var/log/proxy && \
    mv config.py.TEMPLATE docker_files/config.py docker_files/gunicorn.py hxl_proxy/schema-mysql.sql hxl_proxy/schema-sqlite3.sql /srv/config/ && \
    mv docker_files/hxl_run /etc/services.d/hxl/run && \
    mv docker_files/app.py . && \
    pip3 install --upgrade \
        gunicorn && \
    pip3 install --upgrade -r requirements.txt && \
    apk add --virtual .gevent-deps \
        build-base \
        python3-dev && \
    pip3 install gevent && \
    apk del \
        .gevent-deps && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/*

EXPOSE 5000
