FROM python:3.12.13-slim

RUN useradd -m userapp
WORKDIR /app

COPY --chown=userapp:userapp ./ui/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=userapp:userapp  ./shared/requirements.txt shared_requirements.txt
RUN pip install --no-cache-dir -r shared_requirements.txt

COPY --chown=userapp:userapp ./ui /app/ui
COPY --chown=userapp:userapp ./shared /app/shared

USER userapp
CMD ["python", "-m", "ui.app"]