FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install system dependencies including Rust and build tools
RUN apt-get update && \
    apt-get install -y \
        git \
        curl \
        build-essential \
        pkg-config \
        libssl-dev \
        ca-certificates && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . ~/.cargo/env && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set PATH to include cargo
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with Rust environment
RUN . ~/.cargo/env && uv sync --frozen --no-install-project

# Copy application code
COPY app ./app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]