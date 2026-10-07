FROM ubuntu:24.04

ENV PATH="/opt/texlive/2025/bin/x86_64-linux:${PATH}"

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl perl poppler-utils python3 unzip xz-utils \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    curl -fsSL \
      https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/tlnet-final/install-tl-unx.tar.gz \
      -o /tmp/install-tl.tar.gz; \
    echo "311df9f1477fd90c520159d1feddc2d6270f010d8349d1f6bdb9461a93b48a5c  /tmp/install-tl.tar.gz" \
      | sha256sum -c -; \
    mkdir /tmp/install-tl; \
    tar -xzf /tmp/install-tl.tar.gz -C /tmp/install-tl

RUN set -eux; \
    printf '%s\n' \
      'selected_scheme scheme-basic' \
      'TEXDIR /opt/texlive/2025' \
      'TEXMFCONFIG ~/.texlive2025/texmf-config' \
      'TEXMFHOME ~/texmf' \
      'TEXMFLOCAL /opt/texlive/texmf-local' \
      'TEXMFSYSCONFIG /opt/texlive/2025/texmf-config' \
      'TEXMFSYSVAR /opt/texlive/2025/texmf-var' \
      'TEXMFVAR ~/.texlive2025/texmf-var' \
      'option_doc 0' \
      'option_src 0' \
      'option_autobackup 0' \
      'option_path 0' \
      'option_symlinks 0' \
      'collection-basic 1' \
      'collection-latex 1' \
      'collection-latexrecommended 1' \
      'collection-fontsrecommended 1' \
      'collection-luatex 1' \
      'collection-xetex 1' \
      > /tmp/texlive.profile
RUN /tmp/install-tl/install-tl-20260301/install-tl \
      --profile=/tmp/texlive.profile \
      --repository=https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/tlnet-final \
      --no-interaction \
 && rm -rf /tmp/install-tl /tmp/install-tl.tar.gz /tmp/texlive.profile

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends latexmk \
 && rm -rf /var/lib/apt/lists/*
