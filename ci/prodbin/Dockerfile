# syntax=docker/dockerfile:1
FROM zenoss/product-deps:dev

USER zenoss

COPY etc /opt/zenoss/etc

USER root

RUN apt-get update && apt-get install -y gosu

COPY entrypoint.sh /
RUN chmod 500 /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "bash" ]
