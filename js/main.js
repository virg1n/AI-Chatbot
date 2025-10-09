// const API_URL = "http://localhost:5000/search"; 

// const input = document.getElementById("promptInput");
// const button = document.getElementById("searchBtn");
// const resultsDiv = document.getElementById("results");

// const AGENT_ID = 'agent_6301k71gqjvheebste5gnwxbz4v2';
// const OPEN_IN_NEW_TAB = true;
// const WIDGET_POSITION = 'bottom-right'; 
// const img = document.querySelector('.image_to_show_1');

// // Fixed, unchangeable topic variable
// const topic = "London";

// function injectElevenLabsWidget() {
//   const ID = 'elevenlabs-convai-widget';

//   const script = document.createElement('script');
//   script.src = 'https://unpkg.com/@elevenlabs/convai-widget-embed';
//   script.async = true;
//   script.type = 'text/javascript';
//   document.head.appendChild(script);

//   const wrapper = document.createElement('div');
//   wrapper.className = `convai-widget ${WIDGET_POSITION}`;

//   const widget = document.createElement('elevenlabs-convai');
//   widget.id = ID;
//   widget.setAttribute('agent-id', AGENT_ID);
//   widget.setAttribute('variant', 'full');

//   const img = document.querySelector('.image_to_show_1');

//   widget.addEventListener('elevenlabs-convai:call', (event) => {
//     event.detail.config.clientTools = {
//       ShowImage: async ({ topic }) => {
//       const prompt = topic
//       console.log(prompt)

//       // resultsDiv.innerHTML = "<p>Searching...</p>";

//       try {
//         const response = await fetch(API_URL, {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json",
//           },
//           body: JSON.stringify({ prompt: prompt, top_k: 3 }),
//         });

//         console.log(response)

//         const data = await response.json();
//         console.log(data)

//         if (data.error) {
//           resultsDiv.innerHTML = `<p style="color:red">Error: ${data.error}</p>`;
//           return;
//         }

//         if (!data.results || data.results.length === 0) {
//           resultsDiv.innerHTML = "<p>No similar images found.</p>";
//           return;
//         }

//         // resultsDiv.innerHTML = "";
//         data.results.forEach(item => {
//           const div = document.createElement("div");
//           div.className = "result-item";

//           const img = document.createElement("img");
//           img.src = item.path;
//           img.alt = item.id;

//           const score = document.createElement("div");
//           score.className = "score";
//           score.textContent = `Score: ${item.score.toFixed(3)}`;

//           div.appendChild(img);
//           div.appendChild(score);
//           resultsDiv.appendChild(div);
//         });

//       } catch (err) {
//         resultsDiv.innerHTML = `<p style="color:red">Request failed: ${err.message}</p>`;
//       }
//       },
//     };
//   });

//   wrapper.appendChild(widget);
//   document.body.appendChild(wrapper);
// }

// if (document.readyState === 'loading') {
//   document.addEventListener('DOMContentLoaded', injectElevenLabsWidget);
// } else {
//   injectElevenLabsWidget();
// }

const API_URL = "http://localhost:5000/search";

const resultsDiv = document.getElementById("results");
const AGENT_ID = "agent_6301k71gqjvheebste5gnwxbz4v2";
const WIDGET_POSITION = "bottom-right";

// Optional: a default topic if your tool calls without one
const DEFAULT_TOPIC = "London";

function injectElevenLabsWidget() {
  const ID = "elevenlabs-convai-widget";

  // Load the widget script
  const script = document.createElement("script");
  script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed";
  script.async = true;
  script.type = "text/javascript";
  document.head.appendChild(script);

  // Create widget container
  const wrapper = document.createElement("div");
  wrapper.className = `convai-widget ${WIDGET_POSITION}`;

  // Create the widget element
  const widget = document.createElement("elevenlabs-convai");
  widget.id = ID;
  widget.setAttribute("agent-id", AGENT_ID);
  widget.setAttribute("variant", "full");

  // When the widget initiates a call, register the client tool
  widget.addEventListener("elevenlabs-convai:call", (event) => {
    event.detail.config.clientTools = {
      ShowImage: async ({ topic }) => {
        const prompt = (topic && String(topic).trim()) || DEFAULT_TOPIC;

        // Optional: clear results each invocation
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
        } catch (err) {
          resultsDiv.innerHTML = `<p style="color:red">Request failed: ${err.message}</p>`;
        }
      },
    };
  });

  wrapper.appendChild(widget);
  document.body.appendChild(wrapper);
}

// Ensure DOM exists before we query or inject
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", injectElevenLabsWidget);
} else {
  injectElevenLabsWidget();
}
