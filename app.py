# streamlit_app.py
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Snake en Streamlit", layout="centered")
st.title("🐍 Snake (embebido en Streamlit)")

html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; }
  .wrap { display:flex; flex-direction:column; align-items:center; gap:12px; padding:12px; }
  canvas { background:#111; border-radius:12px; box-shadow:0 6px 24px rgba(0,0,0,.25); }
  .row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; justify-content:center; }
  button { padding:8px 12px; border-radius:10px; border:1px solid #ddd; cursor:pointer; }
  .pill { background:#f3f3f3; padding:6px 10px; border-radius:999px; font-size:14px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="row">
    <span class="pill">Controles: flechas ←↑→↓  ·  Pausa: Barra espaciadora</span>
    <button id="btnReset">Reiniciar</button>
    <span class="pill">Puntaje: <b id="score">0</b></span>
  </div>
  <canvas id="game" width="420" height="420"></canvas>
</div>

<script>
(() => {
  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const btnReset = document.getElementById("btnReset");

  const CELL = 20;
  const GRID = Math.floor(canvas.width / CELL); // 21x21
  let snake, dir, apple, score, playing, tickMs, lastTick, queuedDir;

  function init() {
    snake = [{x:10,y:10},{x:9,y:10},{x:8,y:10}];
    dir = {x:1,y:0};
    queuedDir = null;
    score = 0;
    scoreEl.textContent = score;
    playing = true;
    tickMs = 120; // velocidad
    placeApple();
    lastTick = performance.now();
    requestAnimationFrame(loop);
  }

  function placeApple() {
    while (true) {
      const a = {x:Math.floor(Math.random()*GRID), y:Math.floor(Math.random()*GRID)};
      if (!snake.some(s => s.x===a.x && s.y===a.y)) { apple = a; return; }
    }
  }

  function setDir(nx, ny) {
    // Evita reversa inmediata
    if (snake.length>1 && nx === -dir.x && ny === -dir.y) return;
    queuedDir = {x:nx, y:ny};
  }

  window.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") setDir(-1,0);
    else if (e.key === "ArrowRight") setDir(1,0);
    else if (e.key === "ArrowUp") setDir(0,-1);
    else if (e.key === "ArrowDown") setDir(0,1);
    else if (e.code === "Space") playing = !playing;
  });

  btnReset.addEventListener("click", init);

  function loop(ts) {
    if (playing && ts - lastTick >= tickMs) {
      lastTick = ts;
      if (queuedDir) { dir = queuedDir; queuedDir = null; }
      step();
    }
    draw();
    requestAnimationFrame(loop);
  }

  function step() {
    const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };
    // Colisiones con pared
    if (head.x<0 || head.x>=GRID || head.y<0 || head.y>=GRID) { gameOver(); return; }
    // Colisión con cuerpo
    if (snake.some(s => s.x===head.x && s.y===head.y)) { gameOver(); return; }
    snake.unshift(head);
    // Comer manzana
    if (head.x===apple.x && head.y===apple.y) {
      score += 1; scoreEl.textContent = score;
      if (tickMs > 70) tickMs -= 2; // acelera un poco
      placeApple();
    } else {
      snake.pop();
    }
  }

  function gameOver() {
    playing = false;
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle = "#fff";
    ctx.font = "bold 22px system-ui, Arial";
    ctx.textAlign = "center";
    ctx.fillText("GAME OVER", canvas.width/2, canvas.height/2 - 8);
    ctx.font = "16px system-ui, Arial";
    ctx.fillText("Click 'Reiniciar' para jugar de nuevo", canvas.width/2, canvas.height/2 + 16);
  }

  function draw() {
    // Fondo cuadriculado leve
    ctx.fillStyle = "#111";
    ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    for (let i=0;i<=GRID;i++) {
      ctx.beginPath(); ctx.moveTo(i*CELL,0); ctx.lineTo(i*CELL,canvas.height); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0,i*CELL); ctx.lineTo(canvas.width,i*CELL); ctx.stroke();
    }
    // Manzana
    ctx.fillStyle = "#e74c3c";
    ctx.fillRect(apple.x*CELL+2, apple.y*CELL+2, CELL-4, CELL-4);
    // Serpiente
    for (let i=0;i<snake.length;i++) {
      ctx.fillStyle = i===0 ? "#2ecc71" : "#27ae60";
      const s = snake[i];
      ctx.fillRect(s.x*CELL+2, s.y*CELL+2, CELL-4, CELL-4);
    }
    // Pausa
    if (!playing) {
      ctx.fillStyle = "rgba(0,0,0,0.3)";
      ctx.fillRect(0,0,canvas.width,canvas.height);
    }
  }

  init();
})();
</script>
</body>
</html>
"""

# Altura suficiente para que quepa todo el HTML
components.html(html, height=520, scrolling=False)
