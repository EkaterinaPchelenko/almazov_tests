function initTimer(timerId) {
  const timer = document.getElementById(timerId);
  if (!timer) return;

  const startedAt = new Date(timer.dataset.startedAt);

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function renderTimer() {
    const now = new Date();
    const diffSeconds = Math.max(Math.floor((now - startedAt) / 1000), 0);

    const hours = Math.floor(diffSeconds / 3600);
    const minutes = Math.floor((diffSeconds % 3600) / 60);
    const seconds = diffSeconds % 60;

    timer.textContent = hours > 0
      ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
      : `${pad(minutes)}:${pad(seconds)}`;
  }

  renderTimer();
  setInterval(renderTimer, 1000);
}

document.addEventListener("DOMContentLoaded", function () {
  initTimer("test-timer");
  initTimer("diagnostic-timer");
});

document.body.addEventListener("htmx:afterSwap", function () {
  initTimer("test-timer");
  initTimer("diagnostic-timer");
});