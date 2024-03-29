FROM registry.gitlab.com/clarin-eric/docker-alpine-base:2.2.7

ENV OUTPUT_DIR=/output/result
ENV TEMP_OUTPUT_DIR=/output/temp
ENV INPUT_DIR=/input

# Install python & pip; upgrade pip
RUN apk add --no-cache \
    python3=3.9.13-r1 \
    py3-pip=20.3.4-r1 \
    p7zip=16.02-r4 \
    zip=3.0-r9 \
    py3-lxml=4.6.5-r0 \
    && python3 -m pip install --no-cache-dir pip==22.0.4

# set up worker user
RUN adduser -D worker \
    && mkdir -p ${INPUT_DIR} ${OUTPUT_DIR} ${TEMP_OUTPUT_DIR} \
    && chown worker ${INPUT_DIR} ${OUTPUT_DIR} ${TEMP_OUTPUT_DIR} \
    && chmod og+r ${INPUT_DIR} ${OUTPUT_DIR} ${TEMP_OUTPUT_DIR}

USER worker

# copy script
COPY --chown=worker:worker src/requirements.txt /app/requirements.txt
WORKDIR /app

# install script requirements
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY --chown=worker:worker src/ /app/

ENTRYPOINT [ "script/entrypoint.sh" ]

VOLUME /input
