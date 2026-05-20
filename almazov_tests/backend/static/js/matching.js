(function () {
  function resetMatchingState() {
    window.selectedMatchingCell = null;
    window.matchingPairs = {};
  }

  function selectCell(button) {
    window.selectedMatchingCell = button.dataset.cell;

    document.querySelectorAll("[data-cell]").forEach((item) => {
      item.classList.remove("selected");
    });

    button.classList.add("selected");
  }

  function selectImage(button) {
    if (!window.selectedMatchingCell) {
      alert("Сначала выберите клетку");
      return;
    }

    const cellId = window.selectedMatchingCell;
    const imageId = button.dataset.image;

    Object.keys(window.matchingPairs).forEach((existingCellId) => {
      if (window.matchingPairs[existingCellId] === imageId) {
        delete window.matchingPairs[existingCellId];
      }
    });

    window.matchingPairs[cellId] = imageId;
    window.selectedMatchingCell = null;

    redrawMatchingState();
    drawLines();
  }

  function redrawMatchingState() {
    document.querySelectorAll("[data-cell]").forEach((item) => {
      item.classList.remove("selected", "matched");
    });

    document.querySelectorAll("[data-image]").forEach((item) => {
      item.classList.remove("matched");
    });

    Object.entries(window.matchingPairs || {}).forEach(([cellId, imageId]) => {
      const cell = document.getElementById(`cell-${cellId}`);
      const image = document.getElementById(`image-${imageId}`);

      if (cell) cell.classList.add("matched");
      if (image) image.classList.add("matched");
    });
  }

  function drawLines() {
    const svg = document.getElementById("matching-lines");
    const wrapper = document.querySelector(".matching-wrapper");

    if (!svg || !wrapper) return;

    svg.innerHTML = "";

    const wrapperRect = wrapper.getBoundingClientRect();

    Object.entries(window.matchingPairs || {}).forEach(([cellId, imageId]) => {
      const cell = document.getElementById(`cell-${cellId}`);
      const image = document.getElementById(`image-${imageId}`);

      if (!cell || !image) return;

      const cellRect = cell.getBoundingClientRect();
      const imageRect = image.getBoundingClientRect();

      const x1 = cellRect.right - wrapperRect.left;
      const y1 = cellRect.top + cellRect.height / 2 - wrapperRect.top;
      const x2 = imageRect.left - wrapperRect.left;
      const y2 = imageRect.top + imageRect.height / 2 - wrapperRect.top;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const curve = 70;

      const d = `
        M ${x1} ${y1}
        C ${x1 + curve} ${y1},
          ${x2 - curve} ${y2},
          ${x2} ${y2}
      `;

      path.setAttribute("d", d);
      path.setAttribute("stroke", "#2563eb");
      path.setAttribute("stroke-width", "4");
      path.setAttribute("fill", "none");
      path.setAttribute("stroke-linecap", "round");

      svg.appendChild(path);
    });
  }

  function initMatching() {
    const form = document.getElementById("matching-form");
    if (!form) return;

    resetMatchingState();

    document.querySelectorAll("[data-cell]").forEach((button) => {
      button.addEventListener("click", function () {
        selectCell(button);
      });
    });

    document.querySelectorAll("[data-image]").forEach((button) => {
      button.addEventListener("click", function () {
        selectImage(button);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", initMatching);

  document.addEventListener("htmx:afterSwap", function () {
    initMatching();
    drawLines();
  });

  document.addEventListener("htmx:configRequest", function (event) {
    const form = event.target;

    if (!form || form.id !== "matching-form") return;

    const answer = JSON.stringify(window.matchingPairs || {});
    event.detail.parameters.answer = answer;

    const input = document.getElementById("matching-answer");
    if (input) {
      input.value = answer;
    }
  });

  window.addEventListener("resize", drawLines);
})();