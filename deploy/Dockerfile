# The web server on Fly.io. Built from a clean export of HEAD (deploy/deploy.sh), never the working tree.
#
# The engine ships compiled (mypyc, 2026-10-20): the first stage compiles its hot modules to C extensions and then proves
# them, by playing the 22 recorded games of tools/engine_speed and comparing every move with the committed baseline. A
# compiled engine that plays one move differently, or crashes, never deploys. The working tree stays pure Python; only
# the image carries the compiled modules (about 1.5x faster Expert moves, the same play).
FROM python:3.14-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "aiohttp>=3.9" "mypy>=1.19" setuptools
COPY animal_kingdom ./animal_kingdom
COPY tools/engine_speed ./tools/engine_speed
RUN python -m mypyc --ignore-missing-imports \
        animal_kingdom/engine/maps.py animal_kingdom/engine/strength.py animal_kingdom/engine/state.py \
        animal_kingdom/engine/rules.py animal_kingdom/engine/statics.py animal_kingdom/bots/features.py \
    && rm -rf build \
    && python -c "import animal_kingdom.engine.rules as r; assert r.__file__.endswith('.so'), r.__file__" \
    && python tools/engine_speed/record.py /tmp/compiled.json \
    && python tools/engine_speed/compare.py tools/engine_speed/baseline.json /tmp/compiled.json | tee /tmp/gate.txt \
    && grep -q "^22/22 identical" /tmp/gate.txt

FROM python:3.14-slim
WORKDIR /app
RUN pip install --no-cache-dir "aiohttp>=3.9"
COPY --from=build /app/animal_kingdom ./animal_kingdom
# results/ is the Fly volume: profiles (web.db), saved matches, player decks and the human game logs.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "animal_kingdom.web.server", "--host", "0.0.0.0", "--port", "8080", "--no-open"]
