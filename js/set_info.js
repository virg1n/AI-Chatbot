const API_BASE = "https://mindxium.net/";

/** Collect non-empty fields from the form */
function buildPayload(form) {
  const fd = new FormData(form);
  const entries = Object.fromEntries(fd.entries());

  // Trim all strings
  for (const k in entries) {
    if (typeof entries[k] === "string") entries[k] = entries[k].trim();
  }

  // Prepare payload (omit empty values)
  const allowed = [
    "phone_number",
    "first_name",
    "last_name",
    "age",
    "relation",
    "memory_about",
    "last_conversation",
    "stories_for",
    "questions_for",
  ];

  const payload = {};
  for (const key of allowed) {
    const v = entries[key];
    if (v !== undefined && v !== "") {
      payload[key] = key === "age" ? Number(v) : v;
    }
  }
  // Drop NaN for age
  if ("age" in payload && Number.isNaN(payload.age)) {
    delete payload.age;
  }

  return payload;
}

/** Validate identifier: phone OR (first + last) */
function validateIdentifier(payload) {
  const hasPhone = !!payload.phone_number;
  const hasBothNames = !!payload.first_name && !!payload.last_name;
  return hasPhone || hasBothNames;
}

function setBusy(isBusy) {
  const btn = document.getElementById("submitBtn");
  const busy = document.getElementById("busy");
  btn.disabled = isBusy;
  busy.style.display = isBusy ? "inline" : "none";
}

function showStatus(message, type = "info") {
  const status = document.getElementById("status");
  status.textContent = message;
  status.className = ""; // reset
  status.classList.add(type); // you can style .info/.success/.error in your CSS
}

function showResult(json) {
  const pre = document.getElementById("result");
  pre.textContent = JSON.stringify(json, null, 2);
}

async function jsonFetch(url, options) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });

  // Try to parse JSON whether or not res.ok
  let data = null;
  try {
    data = await res.json();
  } catch {
    // ignore parse errors
  }

  if (!res.ok) {
    const msg =
      (data && (data.error || data.hint)) ||
      `Request failed with status ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("setInfoForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showResult({});
    showStatus("", "info");

    const payload = buildPayload(form);
    if (!validateIdentifier(payload)) {
      showStatus(
        "Provide phone_number OR (first_name and last_name).",
        "error"
      );
      return;
    }

    setBusy(true);
    try {
      const data = await jsonFetch(`${API_BASE}/set_info`, {
        body: JSON.stringify(payload),
      });

      // Example success summary
      const summary = (() => {
        const st = data.status ? `status: ${data.status}` : "ok";
        const p = data.person || {};
        const who =
          p.first_name || p.last_name || p.phone_number
            ? ` · person: ${[p.first_name, p.last_name]
                .filter(Boolean)
                .join(" ")}${p.phone_number ? ` (${p.phone_number})` : ""}`
            : "";
        return `${st}${who}`;
      })();

      showStatus(summary, "success");
      showResult(data);
    } catch (err) {
      showStatus(err.message || "Request failed", "error");
      showResult(err.data || { error: err.message || "Unknown error" });
    } finally {
      setBusy(false);
    }
  });

  form.addEventListener("reset", () => {
    showStatus("", "info");
    showResult({});
  });
});
