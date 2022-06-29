FROM public.ecr.aws/unocha/python3-base-s6:3.9

WORKDIR /srv/www

COPY . .

RUN apk add \
        git \
        sqlite \
        libffi-dev \
        unit \
        unit-python3 && \
    mkdir -p \
        /etc/services.d/hxl \
        /srv/db \
        /srv/cache \
        /srv/config \
        /srv/output \
        /var/log/proxy && \
    mv config.py.TEMPLATE /srv/config/config.py && \
    mv hxl_proxy/schema-mysql.sql hxl_proxy/schema-sqlite3.sql /srv/config/ && \
    mv docker_files/hxl_run /etc/services.d/hxl/run && \
    mv docker_files/app.py docker_files/app_nr.py . && \
    pip3 --no-cache-dir install --upgrade \
        pip \
        wheel && \
    pip3 install --upgrade -r requirements.txt && \
    pip3 install newrelic && \
    apk del \
        git \
        libffi-dev && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/*

EXPOSE 5000
