# Development container for Lenny
# Includes Python 3.11, Node.js 20, PDM, Just, Docker CLI, and Starship

FROM python:3.11-slim

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies, Docker CLI, and Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    vim \
    sudo \
    gnupg2 \
    net-tools \
    iputils-ping \
    procps \
    # For Python native extensions
    build-essential \
    htop \
    # For psycopg2, the Python PostgreSQL adapter
    libpq-dev \
    ca-certificates \
    lsb-release \
    # Install Docker GPG key
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    # Install Node.js GPG key and add repo
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    # Install packages
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin nodejs \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Install development tools: Just, PDM, and Starship
RUN curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin \
    && pip install --no-cache-dir --upgrade pip pdm \
    && curl -fsSL https://starship.rs/install.sh | sh -s -- -y

# Create non-root user for development
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && mkdir -p /home/$USERNAME/.vscode-server /home/$USERNAME/.vscode-server-insiders /home/$USERNAME/.config \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Add user to docker group (for docker socket access)
RUN groupadd -f docker && usermod -aG docker $USERNAME

# Copy Starship configuration
COPY starship.toml /home/$USERNAME/.config/starship.toml
RUN chown $USERNAME:$USERNAME /home/$USERNAME/.config/starship.toml

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER $USERNAME

# Configure user environment
RUN pdm config python.use_venv true \
    && echo 'eval "$(starship init bash)"' >> /home/$USERNAME/.bashrc

# Set environment variables
ENV PATH="/home/vscode/.local/bin:/workspace/.venv/bin:/workspace/node_modules/.bin:$PATH"
ENV PYTHONPATH="/workspace/backend"
ENV NODE_ENV=development
