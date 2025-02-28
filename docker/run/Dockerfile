# Use the latest slim version of Debian
FROM debian:bookworm-slim

# Check if the argument is provided, else throw an error
ARG BRANCH
RUN if [ -z "$BRANCH" ]; then echo "ERROR: BRANCH is not set!" >&2; exit 1; fi
ENV BRANCH=$BRANCH

# Copy contents of the project to /a0
COPY ./fs/ /

# pre installation steps
RUN bash /ins/pre_install.sh $BRANCH

ENV LC_ALL="en_US.UTF-8"
ENV LC_CTYPE="en_US.UTF-8"

RUN dpkg-reconfigure locales

RUN python --version | grep 3.12

# install A0
RUN bash /ins/install_A0.sh $BRANCH

# install additional software
RUN bash /ins/install_additional.sh $BRANCH

# cleanup repo and install A0 without caching, this speeds up builds
ARG CACHE_DATE=none
RUN echo "cache buster $CACHE_DATE" && bash /ins/install_A02.sh $BRANCH

# post installation steps
RUN bash /ins/post_install.sh $BRANCH

RUN chmod +x /exe/*.sh

ENV SEARXNG_URL="http://127.0.0.1:8888"
ENV SEARXNG_BIND_ADDRESS="0.0.0.0"
ENV SEARXNG_PORT="8888"

# Expose ports
EXPOSE 22 80
EXPOSE 8888

# initialize runtime
CMD ["/bin/bash", "-c", "/bin/bash /exe/initialize.sh $BRANCH"]
