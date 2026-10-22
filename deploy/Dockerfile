# The web server on Fly.io. Built from a clean export of HEAD (deploy/deploy.sh), never the working tree.
#
# The engine and the search ship compiled (mypyc, 2026-10-20): about 1.5x faster Expert moves, so a stronger Expert in the
# same thinking time. Compiled code is code no local test ran, and it differs where plain Python is lenient: it enforces
# type annotations at runtime and pickles frozen dataclasses differently. So the first stage compiles the engine and the
# search, then runs the fast test tier against the compiled modules; a failure never deploys (2026-10-22, replacing 22
# recorded bot games, which saw only the common cards' paths and needed a committed recording kept current).
#
# Three trees (deploy.sh): code/ (the Python), data/ (cards, decks, maps), ui/ (the client's static files, the news, the
# studies), and the paintings from their own image (deploy.sh pushes it when they change). The compile depends on code/
# alone, so a card or client change reuses it and pays only the tests.
ARG ART
FROM ${ART} AS art

FROM python:3.14-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "aiohttp>=3.9" "mypy>=1.19" setuptools \
        "pytest>=7.0" "pytest-xdist>=3.5" "rich>=13.7" "textual>=8.2,<9" "numpy>=1.26"
COPY code/animal_kingdom ./animal_kingdom
RUN python -m mypyc --ignore-missing-imports \
        animal_kingdom/engine/maps.py animal_kingdom/engine/strength.py animal_kingdom/engine/state.py \
        animal_kingdom/engine/rules.py animal_kingdom/engine/statics.py animal_kingdom/engine/effects.py \
        animal_kingdom/bots/features.py animal_kingdom/bots/greedy_bot.py animal_kingdom/bots/turn_search.py \
        animal_kingdom/bots/turn_bot.py animal_kingdom/bots/referee_bot.py animal_kingdom/bots/determinize.py \
    && rm -rf build
COPY data ./animal_kingdom/data
COPY ui/animal_kingdom/web ./animal_kingdom/web
COPY --from=art /art ./animal_kingdom/web/static/art
COPY --from=art /kit2 ./animal_kingdom/web/static/kit2
# Left out, for what the image doesn't carry: the deck docs (docs/), Martin's logged games (results/), the features
# file's own source text, and parallel simulation, which pickles the bot's frozen weights (the server never does).
RUN python -c "import animal_kingdom.engine.rules as r, animal_kingdom.bots.referee_bot as b; assert r.__file__.endswith('.so') and b.__file__.endswith('.so')" \
    && python -m pytest -q -m "not slow" -o markers=slow -n auto -p no:cacheprovider animal_kingdom/tests \
        --ignore=animal_kingdom/tests/test_deck_docs.py \
        --deselect animal_kingdom/tests/test_features.py::test_features_source_has_no_card_deck_or_tag_literals \
        --deselect animal_kingdom/tests/test_features.py::test_features_source_allows_flight_keyword_literal \
        --deselect animal_kingdom/tests/test_sim.py::test_run_pairs_parallel_matches_serial_with_weights \
        --deselect animal_kingdom/tests/test_web_match.py::test_a_study_lists_its_positions_from_the_logs \
        --deselect animal_kingdom/tests/test_web_match.py::test_play_from_here_seats_you_in_the_other_chair_at_that_round

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
