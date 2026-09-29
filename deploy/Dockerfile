# The web server on Fly.io. Built from a clean export of HEAD (deploy/deploy.sh), never the working tree.
FROM python:3.14-slim
WORKDIR /app
RUN pip install --no-cache-dir "aiohttp>=3.9"
COPY animal_kingdom ./animal_kingdom
# results/ is the Fly volume: profiles (web.db), saved matches, player decks and the human game logs.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "animal_kingdom.web.server", "--host", "0.0.0.0", "--port", "8080", "--no-open"]
