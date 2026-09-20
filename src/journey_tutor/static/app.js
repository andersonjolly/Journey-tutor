(() => {
  const form = document.getElementById("lesson-form");
  const statusEl = document.getElementById("status");
  const errorEl = document.getElementById("error");
  const resultEl = document.getElementById("result");
  const submitBtn = document.getElementById("submit-btn");

  function showError(message) {
    errorEl.hidden = false;
    errorEl.textContent = message;
  }

  function clearFeedback() {
    errorEl.hidden = true;
    errorEl.textContent = "";
    statusEl.hidden = true;
    statusEl.textContent = "";
  }

  function renderLesson(data) {
    document.getElementById("lesson-title").textContent = data.title;
    const totalWords = (data.sections || []).reduce(
      (sum, s) => sum + (s.estimated_word_count || 0),
      0,
    );
    document.getElementById("lesson-meta").textContent =
      `${data.difficulty} · ${data.duration_minutes} min · ` +
      `budget ${data.word_budget} words · sections total ${totalWords}`;

    const objectives = document.getElementById("objectives");
    objectives.innerHTML = "";
    for (const obj of data.learning_objectives || []) {
      const li = document.createElement("li");
      li.textContent = obj;
      objectives.appendChild(li);
    }

    const sections = document.getElementById("sections");
    sections.innerHTML = "";
    for (const section of data.sections || []) {
      const block = document.createElement("div");
      block.className = "section";
      block.innerHTML = `
        <h3></h3>
        <p class="words"></p>
        <p class="narration"></p>
      `;
      block.querySelector("h3").textContent = section.title;
      block.querySelector(".words").textContent =
        `~${section.estimated_word_count} words`;
      block.querySelector(".narration").textContent = section.narration_script;
      sections.appendChild(block);
    }

    resultEl.hidden = false;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFeedback();
    resultEl.hidden = true;

    const topic = document.getElementById("topic").value.trim();
    const duration = Number(document.getElementById("duration").value);
    const difficulty = document.getElementById("difficulty").value;

    if (!topic) {
      showError("Please enter a topic.");
      return;
    }

    submitBtn.disabled = true;
    statusEl.hidden = false;
    statusEl.textContent = "Generating lesson…";

    try {
      const response = await fetch("/lessons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          duration_minutes: duration,
          difficulty,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail =
          (typeof payload.detail === "string" && payload.detail) ||
          (Array.isArray(payload.detail) &&
            payload.detail.map((d) => d.msg).join("; ")) ||
          `Request failed (${response.status})`;
        throw new Error(detail);
      }
      renderLesson(payload);
      statusEl.hidden = true;
    } catch (err) {
      statusEl.hidden = true;
      showError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
