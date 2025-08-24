# Use the pre-built image for A0

FROM agent-zero-run-local
#agent0ai/agent-zero:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=root

ENV VNCEXPOSE=1
ENV VNCPORT=5900
ENV VNCPWD=changeme
ENV VNCDISPLAY=1024x1024
ENV VNCDEPTH=24
ENV DISPLAY=:0
ENV CUDA_VISIBLE_DEVICES=""

ENV NOVNCPORT=8080

ADD fs/ /

RUN chmod +x /ins/* /exe/*

RUN /ins/install-operator.sh
