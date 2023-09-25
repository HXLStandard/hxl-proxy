FROM public.ecr.aws/unocha/python:3.9

WORKDIR /srv/www

COPY . .

RUN apk add \
        git \
        libffi-dev \
        unit \
        unit-python3 && \
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
        elastic-apm[flask] \
        newrelic && \
    apk del \
        git \
        libffi-dev && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/*

EXPOSE 5000
