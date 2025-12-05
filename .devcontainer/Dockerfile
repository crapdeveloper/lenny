# Development container for Lenny
# Includes Python 3.11, Node.js 20, PDM, Just, Docker CLI, and Starship

FROM python:3.11-slim

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    vim \
    sudo \
    gnupg2 \
    build-essential \
    libpq-dev \
    ca-certificates \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for docker compose logs, etc.)
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (LTS)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Just (cross-platform command runner)
RUN curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# Install PDM for Python dependency management
RUN pip install --upgrade pip && pip install pdm

# Install Starship prompt
RUN curl -fsSL https://starship.rs/install.sh | sh -s -- -y

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
COPY .devcontainer/starship.toml /home/$USERNAME/.config/starship.toml
RUN chown $USERNAME:$USERNAME /home/$USERNAME/.config/starship.toml

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER $USERNAME

# Configure PDM to use venv in project directory
RUN pdm config python.use_venv true

# Configure Starship prompt for bash
RUN echo 'eval "$(starship init bash)"' >> /home/$USERNAME/.bashrc

# Set environment variables
ENV PATH="/workspace/.venv/bin:/workspace/node_modules/.bin:$PATH"
ENV PYTHONPATH="/workspace/backend"
ENV NODE_ENV=development
