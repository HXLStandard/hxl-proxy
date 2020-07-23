FROM unocha/alpine-base-s6-python3:3.11.6

WORKDIR /srv/www

COPY . .

# RUN apk update && \
#     apk upgrade && \
RUN apk add \
        sqlite && \
    apk add libffi-dev && \
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
    pip3 --no-cache-dir install --upgrade pip \
        wheel gunicorn && \
    pip3 install --upgrade -r requirements.txt && \
    pip3 install newrelic && \
    apk add --virtual .gevent-deps \
        build-base \
        python3-dev && \
    pip3 install gevent && \
    apk del \
        .gevent-deps \
        libffi-dev && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/*

EXPOSE 5000
