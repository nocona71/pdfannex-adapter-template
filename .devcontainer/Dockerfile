FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Create mount targets before Docker mounts the named volumes. Otherwise Docker
# can create their parent directories as root, preventing VS Code from starting.
RUN mkdir -p /home/vscode/.bash-history \
        /home/vscode/.vscode-server/data/User \
        /home/vscode/.vscode-server/data/agentSessionData \
        /home/vscode/.copilot/chats \
        /home/vscode/.copilot/session-state \
        /home/vscode/.config/gh \
        /home/vscode/.ssh \
    && chown -R vscode:vscode /home/vscode/.bash-history \
        /home/vscode/.vscode-server /home/vscode/.copilot \
        /home/vscode/.config /home/vscode/.ssh \
    && chmod 700 /home/vscode/.config/gh /home/vscode/.ssh

RUN printf '\nshopt -s histappend\nPROMPT_COMMAND="history -a${PROMPT_COMMAND:+; $PROMPT_COMMAND}"\n' \
    >> /home/vscode/.bashrc

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        latexmk \
        make \
        poppler-utils \
        python3 \
        shellcheck \
        texlive-binaries \
        texlive-extra-utils \
        texlive-fonts-recommended \
        texlive-latex-base \
        texlive-latex-extra \
        texlive-luatex \
        texlive-xetex \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    version="1.7.12"; \
    case "$(dpkg --print-architecture)" in \
      amd64) archive="actionlint_${version}_linux_amd64.tar.gz"; checksum="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8" ;; \
      arm64) archive="actionlint_${version}_linux_arm64.tar.gz"; checksum="325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6" ;; \
      *) echo "unsupported actionlint architecture: $(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    cd /tmp; \
    curl -fsSLO "https://github.com/rhysd/actionlint/releases/download/v${version}/${archive}"; \
    printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c -; \
    tar -xzf "$archive" -C /usr/local/bin actionlint; \
    rm -f "$archive"
