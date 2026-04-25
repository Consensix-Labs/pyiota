FROM python:3.12-slim

WORKDIR /app

# Install the project with dev dependencies
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir -e ".[dev]"

# Copy tests and examples
COPY tests/ tests/
COPY examples/ examples/

# Default: run unit tests
CMD ["pytest", "tests/unit/", "-v"]
