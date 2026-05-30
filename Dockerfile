# philter-mcp container image.
#
# Default transport is stdio, so MCP clients can launch the server with:
#   docker run -i --rm -e PHILTER_BASE_URL=https://host:8080 -e PHILTER_VERIFY_SSL=false philterd/philter-mcp
#
# Set PHILTER_MCP_TRANSPORT=streamable-http (see docker-compose.yaml) to run it as a
# networked service instead.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PHILTER_BASE_URL=http://localhost:8080

WORKDIR /app

# Copy only what the build needs, then install the package and its dependencies.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 philter
USER philter

# Port used only when PHILTER_MCP_TRANSPORT is streamable-http or sse.
EXPOSE 8000

ENTRYPOINT ["philter-mcp"]
