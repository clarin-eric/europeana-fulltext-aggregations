FROM python:3.10.0-alpine3.14

ENV OUTPUT_DIR=/output

# upgrade pip
RUN python3 -m pip install --no-cache-dir pip==21.3.1

# set up worker user
RUN adduser -D worker
USER worker

# copy script
COPY --chown=worker:worker src/ /app/
WORKDIR /app

# install script requirements
RUN python3 -m pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "./__main__.py" ]

VOLUME /output
