FROM registry.gitlab.com/clarin-eric/docker-alpine-supervisor-java-base:openjdk11-2.1.6 as java

ENV SAXON_HE_VERSION=10.8
ENV SAXON_JAR_SHA512=a7b91ddfbefa4cab5d0c1df92e5cf2473ec5638338bb84e20fb18ad128410a7eb2e4a3a05c0b373e77ae0ea9e29ee05c7ad92f294117e594ede3a1ad6cd26ffd
ENV SAXON_JAR_PATH=/app/saxon.jar
ENV APP_DIR=/app
ENV DATA_DIR=/data

RUN mkdir -p /app

FROM java as base 

RUN wget -O "${SAXON_JAR_PATH}" \
 "https://search.maven.org/remotecontent?filepath=net/sf/saxon/Saxon-HE/${SAXON_HE_VERSION}/Saxon-HE-${SAXON_HE_VERSION}.jar" \
 && echo "${SAXON_JAR_SHA512}  ${SAXON_JAR_PATH}" | sha512sum -c

FROM java

ENV EDM2TXT_XSLT_PATH=/app/edm2txt.xsl

COPY --from=base $SAXON_JAR_PATH $SAXON_JAR_PATH

COPY script/entrypoint.sh /app/entrypoint.sh
COPY script/edm2txt.xsl $EDM2TXT_XSLT_PATH

RUN mkdir /data

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []

WORKDIR /data
