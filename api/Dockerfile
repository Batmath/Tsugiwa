FROM python:3.12.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN useradd -m userapp
WORKDIR /app

COPY --chown=userapp:userapp ./api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=userapp:userapp  ./shared/requirements.txt shared_requirements.txt
RUN pip install --no-cache-dir -r shared_requirements.txt

COPY --chown=userapp:userapp ./api /app/api
COPY --chown=userapp:userapp ./shared /app/shared

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "api.main"]