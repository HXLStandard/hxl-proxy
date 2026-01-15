FROM public.ecr.aws/unocha/python:3.9-stable

ARG UNITD_VERSION=1.32.1-1

WORKDIR /srv/www

COPY . .

# when we use the same python as the latest alpine distro, sure
#unit \
#unit-python3 && \

RUN apk add --no-cache --upgrade --virtual .build-deps \
    build-base \
    git \
    libffi-dev \
    pcre-dev && \
    mkdir -p \
    /etc/services.d/hxl \
    /srv/cache \
    /srv/config \
    /srv/output \
    /var/log/proxy && \
    mv config.py.TEMPLATE /srv/config/config.py && \
    mv docker_files/hxl_run /etc/services.d/hxl/run && \
    mv docker_files/app.py docker_files/app_nr.py docker_files/app_elastic.py . && \
    pip3 --no-cache-dir install --upgrade \
    pip \
    wheel && \
    pip3 install --upgrade -r requirements.txt && \
    pip3 install \
    elastic-apm[flask] && \
    cd /tmp && \
    git clone https://github.com/nginx/unit && \
    cd /tmp/unit && \
    git checkout ${UNITD_VERSION} && \
    ./configure && make && make install && \
    ./configure python && make python && make python-install && \
    apk del .build-deps && \
    apk add pcre && \
    addgroup unit -g 4001 && \
    adduser -D -H unit -u 4001 -G unit && \
    mkdir -p /var/lib/unit/ && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/*

EXPOSE 5000

ENTRYPOINT [ "/init" ]
