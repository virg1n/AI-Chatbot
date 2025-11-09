const API_URL = "/search";
const resultsDiv = document.getElementById("results");
const AGENT_ID = "agent_0001k7sbyc2teqkbaqks5j3ehxej";
const WIDGET_POSITION = "bottom-right";
const DEFAULT_TOPIC = "London";

const input = document.getElementById("users_name");

let widget; // hoist so listeners can see it

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

  // Helper: set dynamic vars from the current input value
  const updateDynVars = () => {
    const name_lastname = input.value || "";
    widget.setAttribute(
      "dynamic-variables",
      JSON.stringify({ name_lastname }) // ensures valid JSON and proper escaping
    );
  };

  // Set initial value and keep it in sync as the user types
  updateDynVars();
  input.addEventListener("input", updateDynVars);

  // Ensure freshest value right before a call starts
  widget.addEventListener("elevenlabs-convai:call", (event) => {
    updateDynVars(); // refresh just-in-time

    // your client tool as before
    event.detail.config.clientTools = {
      ShowImage: async ({ topic }) => {
        const prompt = (topic && String(topic).trim()) || DEFAULT_TOPIC;
        resultsDiv.innerHTML = "<p>Searching...</p>";
        try {
          const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
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
            card.className = "result-item";

            const resultImg = document.createElement("img");
            resultImg.src = item.path;
            resultImg.alt = item.id;

            const score = document.createElement("div");
            score.className = "score";
            score.textContent = `Score: ${item.score.toFixed(3)}`;

            card.appendChild(resultImg);
            card.appendChild(score);
            resultsDiv.appendChild(card);
          });

          const jsonPath = "test.one";
          const value = 123;
          return `${jsonPath}=${value}`;
        } catch (err) {
          resultsDiv.innerHTML = `<p style="color:red">Request failed: ${err.message}</p>`;
        }
      },
    };
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
  userNameLastName = event.target.value;
  toggleBtnVisibility();
});

fetchBtn.addEventListener("click", async () => {
  const full = input.value.trim().replace(/\s+/g, " ");
  const [first_name = "", ...rest] = full.split(" ");
  const last_name = rest.join(" ");

  const qs = new URLSearchParams({ first_name, last_name }).toString();
  const url = `/get_info?${qs}`; 
  

  try {
    fetchBtn.disabled = true;
    const originalText = fetchBtn.textContent;
    fetchBtn.textContent = "Fetching...";
    userInfoDiv.innerHTML = "<p>Loading…</p>";

    const resp = await fetch(url, { method: "GET" });
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
