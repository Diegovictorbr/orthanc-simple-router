FROM jodogne/orthanc:1.11.0

RUN apt-get -y clean && apt-get -y update

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python3.7 libpython3.7 python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3.7 -m pip install requests

COPY download-plugins.sh orthanc.json script.py /root/conf/
RUN mkdir -p /root/orthanc-index/ /root/orthanc-cache/
RUN chmod 777 /root/conf/download-plugins.sh && /root/conf/download-plugins.sh && rm /root/conf/download-plugins.sh

ARG ORIGIN
ARG DICOM_AET
ARG ORTHANC_ADMIN
ARG ORTHANC_ADMIN_PASSWORD
ARG ORTHANC_USER
ARG ORTHANC_USER_PASSWORD

RUN sed -i "s|###ORTHANC_ADMIN###|$ORTHANC_ADMIN|g" /root/conf/script.py && \
    sed -i "s|###ORTHANC_ADMIN_PASSWORD###|$ORTHANC_ADMIN_PASSWORD|g" /root/conf/script.py && \
    sed -i "s|###ORTHANC_USER###|$ORTHANC_USER|g" /root/conf/script.py && \
    sed -i "s|###ORTHANC_USER_PASSWORD###|$ORTHANC_USER_PASSWORD|g" /root/conf/script.py && \
    sed -i "s|###ORIGIN###|$ORIGIN|g" /root/conf/script.py && \
    sed -i "s|###DICOM_AET###|$DICOM_AET|g" /root/conf/orthanc.json && \
    sed -i "s|###ORTHANC_ADMIN###|$ORTHANC_ADMIN|g" /root/conf/orthanc.json && \
    sed -i "s|###ORTHANC_ADMIN_PASSWORD###|$ORTHANC_ADMIN_PASSWORD|g" /root/conf/orthanc.json && \
    sed -i "s|###ORTHANC_USER###|$ORTHANC_USER|g" /root/conf/orthanc.json && \
    sed -i "s|###ORTHANC_USER_PASSWORD###|$ORTHANC_USER_PASSWORD|g" /root/conf/orthanc.json

ENTRYPOINT [ "Orthanc" ]