FROM python:3.14-slim

WORKDIR /pis

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY . .
ENV PATH="/pis/.venv/bin:$PATH"
EXPOSE 8000

CMD [".venv/bin/python", "hospital_server/manage.py", "runserver", "0.0.0.0:8000"]