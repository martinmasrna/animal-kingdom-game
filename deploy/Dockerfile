# The web server on Fly.io, built from a clean export of HEAD (deploy/deploy.sh), never the working tree.
#
# The rules engine (engine_rs/, Rust) is compiled as a wheel in its own stage, so a change that leaves it alone reuses
# that layer. The next stage installs that very wheel and runs the engine's fuzz and the Python tests on it; a failure
# never deploys.
FROM python:3.14-slim AS rust
WORKDIR /rs
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && rm -rf /var/lib/apt/lists/* \
    && curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable \
    && pip install --no-cache-dir "maturin>=1.5,<2"
ENV PATH="/root/.cargo/bin:$PATH"
COPY engine_rs ./engine_rs
RUN cd engine_rs && maturin build --release -o /wheels

FROM python:3.14-slim AS test
WORKDIR /app
COPY --from=rust /wheels /wheels
RUN pip install --no-cache-dir "aiohttp>=3.9" "pytest>=7.0" /wheels/*.whl
COPY animal_kingdom ./animal_kingdom
COPY tools/engine_rs ./tools/engine_rs
RUN python tools/engine_rs/fuzz.py --games 300 --jobs 2 --stop \
    && AK_NO_GAME_LOGS=1 python -m pytest -q -p no:cacheprovider animal_kingdom/tests

FROM python:3.14-slim
WORKDIR /app
COPY --from=rust /wheels /wheels
RUN pip install --no-cache-dir "aiohttp>=3.9" /wheels/*.whl && rm -rf /wheels
COPY --from=test /app/animal_kingdom ./animal_kingdom
# the runtime image imports the engine it will serve
RUN rm -rf animal_kingdom/tests animal_kingdom/web/test && python -c "import animal_kingdom.web.match"
# results/ is the Fly volume: profiles (web.db), saved matches, player decks and the human game logs.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "animal_kingdom.web.server", "--host", "0.0.0.0", "--port", "8080", "--no-open"]
