FROM registry.gitlab.com/clarin-eric/docker-alpine-base:2.2.7

ENV OUTPUT_DIR=/output

# set up worker user
RUN adduser -D worker \
    && mkdir -p ${OUTPUT_DIR} && chown worker ${OUTPUT_DIR} && chmod og+r ${OUTPUT_DIR}

# copy script
COPY --chown=worker:worker src/requirements.txt /app/requirements.txt
WORKDIR /app

COPY --chown=worker:worker src/requirements.txt /app/requirements.txt

# install packages and required python libraries
RUN apk add --no-cache \
    python3=3.9.5-r2 \
    py3-pip=20.3.4-r1 \
    py3-lxml=4.6.3-r1 \
    gcc=10.3.1_git20210424-r2 \
    musl-dev=1.2.2-r3 \
    && python3 -m pip install --no-cache-dir pip==22.0.4 \
    && python3 -m pip install --no-cache-dir -r requirements.txt \
    && apk del gcc musl-dev

COPY --chown=worker:worker src/ /app/

USER worker
ENTRYPOINT [ "script/entrypoint.sh" ]
CMD []
