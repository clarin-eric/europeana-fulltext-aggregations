FROM registry.gitlab.com/clarin-eric/docker-alpine-base:2.1.0-rc3

ENV OUTPUT_DIR=/output

# Install python & pip; upgrade pip
RUN apk add --no-cache \
    python3=3.9.5-r2 \
    py3-pip=20.3.4-r1 \
    && python3 -m pip install --no-cache-dir pip==21.3.1

# set up worker user
RUN adduser -D worker
USER worker

# copy script
COPY --chown=worker:worker src/ /app/
WORKDIR /app

# install script requirements
RUN python3 -m pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python3", "./__main__.py" ]

VOLUME /output
