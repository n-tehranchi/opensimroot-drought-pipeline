FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    dpkg-dev \
    g++ \
    make \
    git \
    ca-certificates \
    python3-dev \
    && python3 --version \
    && apt-cache search python | grep dev \
    && find /usr/include -name 'Python.h' \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --branch master https://github.com/n-tehranchi/OpenSimRoot.git

WORKDIR /build/OpenSimRoot
RUN find /usr/include -name 'Python.h'
RUN ln -s /usr/include/python3.10 /usr/include/python3.12
RUN find /usr/lib -name 'libpython3*'
RUN MULTIARCH=$(dpkg-architecture -qDEB_HOST_MULTIARCH) \
    && ln -s /usr/lib/${MULTIARCH}/libpython3.10.so /usr/lib/${MULTIARCH}/libpython3.12.so \
    && ln -s /usr/lib/${MULTIARCH}/libpython3.10.a /usr/lib/${MULTIARCH}/libpython3.12.a
RUN make clean && make -j$(nproc) release

# --- Runtime stage ---
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    libpython3.10 \
    && rm -rf /var/lib/apt/lists/*

# Copy the compiled binary
COPY --from=builder /build/OpenSimRoot/release_build/OpenSimRoot /usr/local/bin/OpenSimRoot

# Copy the bundled InputFiles (templates, environments, plant parameters)
COPY --from=builder /build/OpenSimRoot/OpenSimRoot/InputFiles /opt/opensimroot/InputFiles

# Copy entrypoint
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Bundle input XML files into the image
COPY inputs/ /opt/inputs/

# Allow users to mount custom input files here
VOLUME ["/sim/input", "/sim/output"]

WORKDIR /sim

ENV PHENOTYPE="" \
    LOCATION="" \
    WATER_REGIME="" \
    OUTPUT_PATH="/sim/output"

ENTRYPOINT ["entrypoint.sh"]
