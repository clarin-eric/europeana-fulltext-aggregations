FROM registry.gitlab.com/clarin-eric/docker-alpine-base:2.1.0

ENV OUTPUT_DIR=/output
ENV INPUT_DIR=/input

# Install python & pip; upgrade pip
RUN apk add --no-cache \
    python3=3.9.5-r2 \
    py3-pip=20.3.4-r1 \
    p7zip=16.02-r4 \
    && python3 -m pip install --no-cache-dir pip==21.3.1

# set up worker user
RUN adduser -D worker \
    && mkdir -p /input \
    && chown worker /input \
    && chmod og+r /input

USER worker

# copy script
COPY --chown=worker:worker src/requirements.txt /app/requirements.txt
WORKDIR /app

# install script requirements
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY --chown=worker:worker src/ /app/

ENTRYPOINT [ "script/entrypoint.sh" ]

VOLUME /input
