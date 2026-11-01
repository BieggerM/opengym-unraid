# Repackage upstream images without changing the application or media.
# Build context is the repository root.
ARG OPENGYM_VERSION=latest
ARG OPENGYM_WEB_IMAGE=ghcr.io/duartesantos8/opengym-web:${OPENGYM_VERSION}
ARG OPENGYM_API_IMAGE=ghcr.io/duartesantos8/opengym-api:${OPENGYM_VERSION}
FROM ${OPENGYM_WEB_IMAGE} AS web
# Keep the CSP in step with the upstream frontend's inline-script hash.
RUN printf '%s\n' "$CONTENT_SECURITY_POLICY" > /tmp/opengym-csp

FROM ${OPENGYM_API_IMAGE}
ARG OPENGYM_VERSION
ARG OPENGYM_WEB_IMAGE
ARG OPENGYM_API_IMAGE
ARG VERSION=dev
ARG VCS_REF=unknown
ARG SOURCE_URL=https://github.com/BieggerM/opengym-unraid

USER root
RUN apk add --no-cache bash nginx gettext-envsubst tini \
 && mkdir -p /run/nginx /etc/opengym /usr/share/opengym

COPY --from=web /usr/share/nginx/html/ /usr/share/nginx/html/
COPY --from=web /etc/nginx/templates/default.conf.template /etc/opengym/default.conf.template
COPY --from=web /docker-entrypoint.d/05-check-base-path.sh /etc/opengym/check-base-path.sh
COPY --from=web /tmp/opengym-csp /etc/opengym/content-security-policy
COPY LICENSE NOTICE.md /usr/share/opengym/
COPY unraid/nginx.conf /etc/nginx/nginx.conf
COPY --chmod=755 unraid/entrypoint.sh /usr/local/bin/opengym-unraid

LABEL org.opencontainers.image.title="openGym for Unraid" \
    org.opencontainers.image.description="openGym API and web UI in one container for Unraid Community Apps" \
    org.opencontainers.image.source="${SOURCE_URL}" \
    org.opencontainers.image.documentation="${SOURCE_URL}#readme" \
    org.opencontainers.image.licenses="AGPL-3.0-or-later" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    io.opengym.upstream.version="${OPENGYM_VERSION}" \
    io.opengym.upstream.api="${OPENGYM_API_IMAGE}" \
    io.opengym.upstream.web="${OPENGYM_WEB_IMAGE}"

# The API retains upstream's root/coach privilege separation. nginx workers use nginx.
# Unraid needs no privileged mode, host network, Docker socket or extra capabilities.
ENV DATA_DIR=/data \
    RP_ID=localhost \
    ORIGIN=http://localhost:8080 \
    PASSWORD_LOGIN=1 \
    FIRST_USER_ADMIN=1 \
    BASE_PATH="" \
    CF_CONNECTING_IP="" \
    MEDIA_UPLOAD_MAX=48m

VOLUME ["/data"]
EXPOSE 8080
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -q -O /dev/null "http://127.0.0.1:8080${BASE_PATH}/" \
     && wget -q -O /dev/null "http://127.0.0.1:8080${BASE_PATH}/api/health" || exit 1
ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/opengym-unraid"]
CMD []
