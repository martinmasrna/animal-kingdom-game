# The web server on Fly.io. Built from a clean export of HEAD (deploy/deploy.sh), never the working tree.
#
# The engine and the search ship compiled (mypyc, 2026-10-20): the first stage compiles them to C extensions and then proves
# them, by playing the 22 games of tools/engine_speed with the plain engine and with the compiled one and comparing every
# move. A compiled engine that plays one move differently, or crashes, never deploys. Both sides are recorded here, from the
# same cards, so no committed recording has to be kept current (2026-10-22). The working tree stays pure Python; only the
# image carries the compiled modules (about 1.5x faster Expert moves, the same play).
#
# Three trees (deploy.sh): code/ (the Python), data/ (cards, decks, maps), ui/ (the client's static files, the news, the
# studies). The compile depends on code/ alone, so a card change reuses it and pays only the gate; a client change reuses both.
FROM python:3.14-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "aiohttp>=3.9" "mypy>=1.19" setuptools
COPY code/animal_kingdom ./animal_kingdom
COPY code/tools/engine_speed ./tools/engine_speed
# /pure keeps the plain Python beside the compiled tree, for the gate's other side.
RUN mkdir /pure && cp -r animal_kingdom tools /pure/ \
    && python -m mypyc --ignore-missing-imports \
        animal_kingdom/engine/maps.py animal_kingdom/engine/strength.py animal_kingdom/engine/state.py \
        animal_kingdom/engine/rules.py animal_kingdom/engine/statics.py animal_kingdom/engine/effects.py \
        animal_kingdom/bots/features.py animal_kingdom/bots/greedy_bot.py animal_kingdom/bots/turn_search.py \
        animal_kingdom/bots/turn_bot.py animal_kingdom/bots/referee_bot.py animal_kingdom/bots/determinize.py \
    && rm -rf build
COPY data ./animal_kingdom/data
COPY data /pure/animal_kingdom/data
RUN cd /pure && PYTHONPATH=/pure python -c "import animal_kingdom.engine.rules as r; assert r.__file__.endswith('.py'), r.__file__" \
    && PYTHONPATH=/pure python tools/engine_speed/record.py /tmp/plain.json \
    && cd /app && PYTHONPATH=/app python -c "import animal_kingdom.engine.rules as r; assert r.__file__.endswith('.so'), r.__file__" \
    && PYTHONPATH=/app python tools/engine_speed/record.py /tmp/compiled.json \
    && python tools/engine_speed/compare.py /tmp/plain.json /tmp/compiled.json | tee /tmp/gate.txt \
    && grep -qE "^([0-9]+)/\1 identical" /tmp/gate.txt
COPY ui/animal_kingdom/web ./animal_kingdom/web

FROM python:3.14-slim
WORKDIR /app
RUN pip install --no-cache-dir "aiohttp>=3.9"
COPY --from=build /app/animal_kingdom ./animal_kingdom
# mypyc links the compiled modules into one shared library beside the package (<hash>__mypyc.*.so); without it they fail to import.
COPY --from=build /app/*__mypyc*.so ./
RUN python -c "import animal_kingdom.engine.effects as e, animal_kingdom.bots.referee_bot as b; assert e.__file__.endswith('.so') and b.__file__.endswith('.so')"   # the runtime image imports the compiled engine and search
# results/ is the Fly volume: profiles (web.db), saved matches, player decks and the human game logs.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "animal_kingdom.web.server", "--host", "0.0.0.0", "--port", "8080", "--no-open"]
