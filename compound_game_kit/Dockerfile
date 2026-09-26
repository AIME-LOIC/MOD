FROM node:20-alpine
WORKDIR /app
COPY game_server.js compound_game.html ./
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/api/health || exit 1
CMD ["node", "game_server.js"]
