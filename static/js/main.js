// const API_BASE =
//   location.hostname === "localhost" || location.hostname === "127.0.0.1"
//     ? "http://127.0.0.1:5000"
//     : "";
// const apiUrl = (path) => `${API_BASE}${path}`;

// const resultsDiv = document.getElementById("results");
// const AGENT_ID = "agent_0001k7sbyc2teqkbaqks5j3ehxej";
// const WIDGET_POSITION = "bottom-right";
// const DEFAULT_TOPIC = "London";

// const input = document.getElementById("users_name");

// let widget; // hoist so listeners can see it
// let first_message = "";

// // ADDED: tiny helper
// const randomFrom = (...xs) => xs[Math.floor(Math.random() * xs.length)];

// // ADDED: compute + set first_message based on name + fetched "realtion"
// async function updateFirstMessage() {
//   const full = (input.value || "").trim().replace(/\s+/g, " ");
//   const [first_name = "", ...rest] = full.split(" ");
//   const last_name = rest.join(" ");

//   // default for all cases: "Hi, {FirstName}"
//   let computed = `Hi, ${first_name || ""}`;

//   // fetch only the "realtion" field (if available)
//   if (first_name || last_name) {
//     const qs = new URLSearchParams({ first_name, last_name }).toString();
//     const url = `/get_info?${qs}`;
//     // const url = apiUrl(`/get_info?${qs}`);

//     try {
//       const resp = await fetch(url, { method: "GET" });
//       if (resp.ok) {
//         const ct = resp.headers.get("content-type") || "";
//         if (ct.includes("application/json")) {
//           const data = await resp.json();
//           const r = String(data['person']['relation']).toLowerCase();
//           if (r === "wife") {
//             computed = randomFrom("Hi honey", "Hi, my love");
//           } else if (r === "brother") {
//             computed = randomFrom("Hi Bro", "Hi, Brother!");
            
            
//           }
//         }
//       }
//     } catch (_) {
//       // on any failure, just keep the default computed greeting
//     }
//   }

//   first_message = computed;
//   if (widget) {
//     // put this first_message into the widget
//     widget.setAttribute("override-first-message", first_message);
//   }
// }

// function injectElevenLabsWidget() {
//   // Load the widget script
//   const script = document.createElement("script");
//   script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed";
//   script.async = true;
//   script.type = "text/javascript";
//   document.head.appendChild(script);

//   // Container
//   const wrapper = document.createElement("div");
//   wrapper.className = `convai-widget ${WIDGET_POSITION}`;

//   // Widget element
//   widget = document.createElement("elevenlabs-convai");
//   widget.id = "elevenlabs-convai-widget";
//   widget.setAttribute("agent-id", AGENT_ID);
//   widget.setAttribute("variant", "full");

//   widget.setAttribute("override-first-message", ""); 

//   const updateDynVars = () => {
//     const name_lastname = input.value || "";
//     widget.setAttribute(
//       "dynamic-variables",
//       JSON.stringify({ name_lastname }) // ensures valid JSON and proper escaping
//     );
//   };

//   // Set initial values and keep them in sync as the user types
//   updateDynVars();
//   input.addEventListener("input", () => {
//     updateDynVars();
//     // ADDED: recompute first message whenever the name changes
//     updateFirstMessage();
//   });

//   updateFirstMessage();

//   // Ensure freshest value right before a call starts
//   widget.addEventListener("elevenlabs-convai:call", async (event) => {
//     updateDynVars(); // refresh just-in-time

//     event.detail.config.clientTools = {
//       ShowImage: async ({ topic }) => {
//         const prompt = (topic && String(topic).trim()) || DEFAULT_TOPIC;
//         resultsDiv.innerHTML = "<p>Searching...</p>";
//         try {
//           const response = await fetch(API_URL, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ prompt, top_k: 3 }),
//           });
//           const data = await response.json();

//           if (data.error) {
//             resultsDiv.innerHTML = `<p style="color:red">Error: ${data.error}</p>`;
//             return;
//           }
//           if (!data.results || data.results.length === 0) {
//             resultsDiv.innerHTML = "<p>No similar images found.</p>";
//             return;
//           }

//           resultsDiv.innerHTML = "";
//           data.results.forEach((item) => {
//             const card = document.createElement("div");
//             card.className = "result-item";

//             const resultImg = document.createElement("img");
//             resultImg.src = item.path;
//             resultImg.alt = item.id;

//             const score = document.createElement("div");
//             score.className = "score";
//             score.textContent = `Score: ${item.score.toFixed(3)}`;

//             card.appendChild(resultImg);
//             card.appendChild(score);
//             resultsDiv.appendChild(card);
//           });

//           const jsonPath = "test.one";
//           const value = 123;
//           return `${jsonPath}=${value}`;
//         } catch (err) {
//           resultsDiv.innerHTML = `<p style="color:red">Request failed: ${err.message}</p>`;
//         }
//       },
//     };

//     await updateFirstMessage(); 

//   });

//   wrapper.appendChild(widget);
//   document.body.appendChild(wrapper);
// }

// // Inject once DOM is ready
// if (document.readyState === "loading") {
//   document.addEventListener("DOMContentLoaded", injectElevenLabsWidget);
// } else {
//   injectElevenLabsWidget();
// }

// const fetchBtn = document.createElement("button");
// fetchBtn.id = "fetchUserBtn";
// fetchBtn.textContent = "Fetch data about user";
// fetchBtn.style.display = "none"; 

// const userInfoDiv = document.createElement("div");
// userInfoDiv.id = "userInfo";

// input.insertAdjacentElement("afterend", fetchBtn);
// fetchBtn.insertAdjacentElement("afterend", userInfoDiv);

// const escapeHtml = (s) =>
//   String(s).replace(/[&<>"']/g, (ch) => ({
//     "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
//   }[ch]));

// const toggleBtnVisibility = () => {
//   fetchBtn.style.display = input.value.trim() ? "" : "none";
// };
// toggleBtnVisibility();

// input.addEventListener("input", (event) => {
//   userNameLastName = event.target.value;
//   toggleBtnVisibility();
// });

// // (unchanged) demo fetch button to show the raw data back to the user
// fetchBtn.addEventListener("click", async () => {
//   const full = input.value.trim().replace(/\s+/g, " ");
//   const [first_name = "", ...rest] = full.split(" ");
//   const last_name = rest.join(" ");

//   const qs = new URLSearchParams({ first_name, last_name }).toString();
//   const url = `/get_info?${qs}`; 
//   // const url = apiUrl(`/get_info?${qs}`);
  
//   try {
//     fetchBtn.disabled = true;
//     const originalText = fetchBtn.textContent;
//     fetchBtn.textContent = "Fetching...";
//     userInfoDiv.innerHTML = "<p>Loading…</p>";

//     const resp = await fetch(url, { method: "GET" });
//     if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

//     const ct = resp.headers.get("content-type") || "";
//     if (ct.includes("application/json")) {
//       const data = await resp.json();
//       userInfoDiv.innerHTML = `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
//     } else {
//       const text = await resp.text();
//       userInfoDiv.innerHTML = `<pre>${escapeHtml(text)}</pre>`;
//     }

//     fetchBtn.textContent = originalText;
//     fetchBtn.disabled = false;
//   } catch (err) {
//     userInfoDiv.innerHTML = `<p style="color:red">Request failed: ${escapeHtml(err.message)}</p>`;
//     fetchBtn.disabled = false;
//     fetchBtn.textContent = "Fetch data about user";
//   }
// });


// Keep same-origin by default; if you serve pages from Flask, this is "" (relative).
const API_BASE =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:5000"
    : "";

const THUMB_SIZE = 140;

// Helper to join paths safely
const apiUrl = (path) => `${API_BASE}${path}`;

// ---- NEW: define concrete endpoints up front
const SEARCH_URL = apiUrl("/search");
const GET_INFO_URL = apiUrl("/get_info");

const resultsDiv = document.getElementById("results");
const AGENT_ID = "agent_0001k7sbyc2teqkbaqks5j3ehxej";
const WIDGET_POSITION = "bottom-right";
const DEFAULT_TOPIC = "London";

const input = document.getElementById("users_name");

let widget; // hoist so listeners can see it
let first_message = "";
let userNameLastName = ""; // <-- FIX: avoid implicit global

// Helper
const randomFrom = (...xs) => xs[Math.floor(Math.random() * xs.length)];

// Compute + set first_message based on name + fetched relation
async function updateFirstMessage() {
  const full = (input.value || "").trim().replace(/\s+/g, " ");
  const [first_name = "", ...rest] = full.split(" ");
  const last_name = rest.join(" ");

  // default for all cases: "Hi, {FirstName}"
  let computed = `Hi, ${first_name || ""}`;

  if (first_name || last_name) {
    const qs = new URLSearchParams({ first_name, last_name }).toString();
    const url = `${GET_INFO_URL}?${qs}`;

    try {
      const resp = await fetch(url, { method: "GET", credentials: "same-origin" });
      if (resp.ok && (resp.headers.get("content-type") || "").includes("application/json")) {
        const data = await resp.json();
        const rel = (data?.person?.relation ?? "").toLowerCase();
        if (rel === "wife") {
          computed = randomFrom("Hi honey", "Hi, my love");
        } else if (rel === "brother") {
          computed = randomFrom("Hi Bro", "Hi, Brother!");
        }
      }
    } catch {
      /* keep default greeting */
    }
  }

  first_message = computed;
  if (widget) widget.setAttribute("override-first-message", first_message);
}

function injectElevenLabsWidget() {
  // Load the widget script
  const script = document.createElement("script");
  script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed";
  script.async = true;
  script.type = "text/javascript";
  document.head.appendChild(script);

  // Container
  const wrapper = document.createElement("div");
  wrapper.className = `convai-widget ${WIDGET_POSITION}`;

  // Widget element
  widget = document.createElement("elevenlabs-convai");
  widget.id = "elevenlabs-convai-widget";
  widget.setAttribute("agent-id", AGENT_ID);
  widget.setAttribute("variant", "full");
  widget.setAttribute("override-first-message", ""); 

  const updateDynVars = () => {
    const name_lastname = input.value || "";
    widget.setAttribute("dynamic-variables", JSON.stringify({ name_lastname }));
  };

  // Initialize + keep in sync
  updateDynVars();
  input.addEventListener("input", () => {
    updateDynVars();
    updateFirstMessage();
  });

  updateFirstMessage();

  // Ensure freshest value right before a call starts
  widget.addEventListener("elevenlabs-convai:call", async (event) => {
    updateDynVars();

    event.detail.config.clientTools = {
      ShowImage: async ({ topic }) => {
        const prompt = (topic && String(topic).trim()) || DEFAULT_TOPIC;
        resultsDiv.innerHTML = "<p>Searching...</p>";
        try {
          // ---- CHANGED: use SEARCH_URL (was missing / using undefined API_URL)
          const response = await fetch(SEARCH_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ prompt, top_k: 3 }),
          });
          const data = await response.json();

          if (data.error) {
            resultsDiv.innerHTML = `<p style="color:red">Error: ${data.error}</p>`;
            return;
          }
          if (!data.results || data.results.length === 0) {
            resultsDiv.innerHTML = "<p>No similar images found.</p>";
            return;
          }

          resultsDiv.innerHTML = "";
          data.results.forEach((item) => {
            const card = document.createElement("div");
            card.className = "result-item"; // This card needs 'position: relative' in your CSS

            const resultImg = document.createElement("img");
            resultImg.className = "result-thumb";
            resultImg.src = item.path;
            resultImg.alt = item.id || "result";
            resultImg.loading = "lazy";
            resultImg.decoding = "async";
            resultImg.width = THUMB_SIZE;   // intrinsic size
            resultImg.height = THUMB_SIZE;

            // Score badge (fixed position; won’t change card height)
            const s = Number(item.score) || 0;
            const badge = document.createElement("span");
            badge.textContent = s.toFixed(3);       // e.g., "0.812"
            badge.title = `Similarity score: ${s}`;     // tooltip for exact value
            badge.setAttribute("aria-label", `Score ${s.toFixed(3)}`);

            const downloadLink = document.createElement("a");
            downloadLink.href = item.path; 
            
            const filename = (item.id || 'image') + '.jpg'; 
            downloadLink.download = filename; // This attribute triggers the download
            
            downloadLink.className = "download-btn"; // For styling
            downloadLink.innerHTML = `
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M6 17h12M12 5v8m0 0 4-4m-4 4-4-4" />
              </svg>`;
            downloadLink.title = "Download image";
            downloadLink.setAttribute("aria-label", "Download image");

            card.appendChild(resultImg);
            card.appendChild(badge);
            card.appendChild(downloadLink); // Add the new download button to the card
            resultsDiv.appendChild(card);
          });

          // Example return value for clientTools
          const jsonPath = "test.one";
          const value = 123;
          return `${jsonPath}=${value}`;
        } catch (err) {
          resultsDiv.innerHTML = `<p style="color:red">Request failed: ${err.message}</p>`;
        }
      },
    };

    await updateFirstMessage();
  });

  wrapper.appendChild(widget);
  document.body.appendChild(wrapper);
}

// Inject once DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", injectElevenLabsWidget);
} else {
  injectElevenLabsWidget();
}

// --- Optional helper UI to fetch raw person JSON ---
const fetchBtn = document.createElement("button");
fetchBtn.id = "fetchUserBtn";
fetchBtn.textContent = "Fetch data about user";
fetchBtn.style.display = "none";

const userInfoDiv = document.createElement("div");
userInfoDiv.id = "userInfo";

input.insertAdjacentElement("afterend", fetchBtn);
fetchBtn.insertAdjacentElement("afterend", userInfoDiv);

const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));

const toggleBtnVisibility = () => {
  fetchBtn.style.display = input.value.trim() ? "" : "none";
};
toggleBtnVisibility();

input.addEventListener("input", (event) => {
  userNameLastName = event.target.value; // now declared
  toggleBtnVisibility();
});

fetchBtn.addEventListener("click", async () => {
  const full = input.value.trim().replace(/\s+/g, " ");
  const [first_name = "", ...rest] = full.split(" ");
  const last_name = rest.join(" ");

  const qs = new URLSearchParams({ first_name, last_name }).toString();
  const url = `${GET_INFO_URL}?${qs}`;

  try {
    fetchBtn.disabled = true;
    const originalText = fetchBtn.textContent;
    fetchBtn.textContent = "Fetching...";
    userInfoDiv.innerHTML = "<p>Loading…</p>";

    const resp = await fetch(url, { method: "GET", credentials: "same-origin" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const data = await resp.json();
      userInfoDiv.innerHTML = `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
    } else {
      const text = await resp.text();
      userInfoDiv.innerHTML = `<pre>${escapeHtml(text)}</pre>`;
    }

    fetchBtn.textContent = originalText;
    fetchBtn.disabled = false;
  } catch (err) {
    userInfoDiv.innerHTML = `<p style="color:red">Request failed: ${escapeHtml(err.message)}</p>`;
    fetchBtn.disabled = false;
    fetchBtn.textContent = "Fetch data about user";
  }
});
