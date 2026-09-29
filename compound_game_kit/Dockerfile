FROM node:20-alpine
WORKDIR /app
COPY game_server.js compound_game.html warzone_city.glb sos_technical_school_v3.glb character_human.glb car_sedan.glb car_van.glb car_pickup.glb house_small.glb house_duplex.glb skyscraper.glb hotel.glb ./
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/api/health || exit 1
CMD ["node", "game_server.js"]
