# The web server on Fly.io, built from a clean export of HEAD (deploy/deploy.sh), never the working tree. The build runs
# the Python tests; a failure never deploys.
FROM python:3.14-slim AS test
WORKDIR /app
RUN pip install --no-cache-dir "aiohttp>=3.9" "pytest>=7.0"
COPY animal_kingdom ./animal_kingdom
RUN AK_NO_GAME_LOGS=1 python -m pytest -q -p no:cacheprovider animal_kingdom/tests

FROM python:3.14-slim
WORKDIR /app
RUN pip install --no-cache-dir "aiohttp>=3.9"
COPY --from=test /app/animal_kingdom ./animal_kingdom
RUN rm -rf animal_kingdom/tests animal_kingdom/web/test
# results/ is the Fly volume: profiles (web.db), saved matches, player decks and the human game logs.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "animal_kingdom.web.server", "--host", "0.0.0.0", "--port", "8080", "--no-open"]
