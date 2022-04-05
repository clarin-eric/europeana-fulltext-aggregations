FROM registry.gitlab.com/clarin-eric/docker-alpine-supervisor-java-base:openjdk11-2.1.7

ENV SAXON_HE_VERSION=10.8
ENV SAXON_JAR_SHA512=a7b91ddfbefa4cab5d0c1df92e5cf2473ec5638338bb84e20fb18ad128410a7eb2e4a3a05c0b373e77ae0ea9e29ee05c7ad92f294117e594ede3a1ad6cd26ffd

ENV APP_DIR=/app
ENV DATA_DIR=/data
ENV SAXON_JAR_PATH=/app/saxon.jar
ENV EDM2TXT_XSLT_PATH=/app/edm2txt.xsl 

RUN \
  apk add --no-cache \
    p7zip=16.02-r4 \
  && mkdir -p /app \
  && wget -O "${SAXON_JAR_PATH}" \
    "https://search.maven.org/remotecontent?filepath=net/sf/saxon/Saxon-HE/${SAXON_HE_VERSION}/Saxon-HE-${SAXON_HE_VERSION}.jar" \
  && echo "${SAXON_JAR_SHA512}  ${SAXON_JAR_PATH}" | sha512sum -c

COPY script/entrypoint.sh /app/entrypoint.sh
COPY script/edm2txt.xsl $EDM2TXT_XSLT_PATH

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []

RUN mkdir /data
WORKDIR /data
