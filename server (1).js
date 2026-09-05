const http = require("http");
const fs = require("fs");
const path = require("path");

const port = Number(process.env.PORT || 3000);

// Gemini configuration
const apiKey = process.env.GEMINI_API_KEY?.trim();
const model = process.env.GEMINI_MODEL || "gemini-3.6-flash";

const root = __dirname;


// -----------------------------
// Send JSON response
// -----------------------------
function sendJson(response, status, body) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8"
  });

  response.end(JSON.stringify(body));
}


// -----------------------------
// Read request body
// -----------------------------
function readBody(request) {
  return new Promise((resolve, reject) => {
    let body = "";

    request.on("data", chunk => {
      body += chunk;
    });

    request.on("end", () => {
      resolve(body);
    });

    request.on("error", reject);
  });
}


// -----------------------------
// Gemini Chat
// -----------------------------
async function chat(request, response) {

  // Check API key
  if (!apiKey) {
    sendJson(response, 503, {
      error: "GEMINI_API_KEY is not configured. Set it before starting the server."
    });
    return;
  }

  try {

    // Read user request
    const rawBody = await readBody(request);

    let input;

    try {
      input = JSON.parse(rawBody);
    } catch (error) {
      sendJson(response, 400, {
        error: "Invalid JSON request"
      });
      return;
    }


    // Validate message
    if (
      !input.message ||
      typeof input.message !== "string"
    ) {
      sendJson(response, 400, {
        error: "message is required"
      });
      return;
    }


    // KisanLink AI instructions
    const systemPrompt = `
You are KisanLink Assistant.

KisanLink is an agricultural marketplace platform designed for
Indian farmers, FPOs, processors, retailers and institutional buyers.

Help users understand and use KisanLink.

You can help with:

- Agricultural market prices
- Nearby buyers
- Buyer verification
- Quality assessment
- Live bidding
- Logistics
- Storage
- Payments
- Transactions
- Grievances
- FPO aggregation
- KisanLink marketplace features

Give concise, simple and practical answers.

Important:
Never claim that you have real-time market data unless the
application actually provides that data.

If the information shown in the website is demo/sample data,
clearly mention that it is demo data.

If the user asks something unrelated to KisanLink, you can still
answer briefly and helpfully.
`;


    // -----------------------------
    // Call Gemini API
    // -----------------------------
    const geminiUrl =
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;


    const result = await fetch(geminiUrl, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apiKey
      },

      body: JSON.stringify({

        systemInstruction: {
          parts: [
            {
              text: systemPrompt
            }
          ]
        },

        contents: [
          {
            role: "user",

            parts: [
              {
                text: input.message.trim()
              }
            ]
          }
        ],

        generationConfig: {
          temperature: 0.4
        }

      })
    });


    // -----------------------------
    // Read Gemini response safely
    // -----------------------------
    const responseText = await result.text();

    console.log("Gemini HTTP Status:", result.status);


    let data = {};

    if (responseText.trim()) {

      try {
        data = JSON.parse(responseText);

      } catch (parseError) {

        console.error(
          "Gemini returned invalid JSON:",
          responseText
        );

        sendJson(response, 502, {
          error:
            "Gemini returned an invalid response."
        });

        return;
      }
    }


    // -----------------------------
    // Handle Gemini API error
    // -----------------------------
    if (!result.ok) {

      console.error(
        "Gemini API Error:",
        data
      );

      sendJson(response, 502, {
        error:
          data?.error?.message ||
          `Gemini API request failed (${result.status})`
      });

      return;
    }


    // -----------------------------
    // Extract Gemini answer
    // -----------------------------
    const reply =
      data?.candidates?.[0]?.content?.parts
        ?.map(part => part.text || "")
        .join("")
        .trim();


    if (!reply) {

      console.error(
        "Gemini returned no text:",
        JSON.stringify(data, null, 2)
      );

      sendJson(response, 502, {
        error:
          "Gemini returned no text response."
      });

      return;
    }


    // -----------------------------
    // Send answer to frontend
    // -----------------------------
    sendJson(response, 200, {
      reply: reply
    });


  } catch (error) {

    console.error(
      "KisanLink Chat Error:",
      error
    );

    sendJson(response, 500, {
      error:
        error.message ||
        "Unable to process chat request"
    });
  }
}


// -----------------------------
// HTTP Server
// -----------------------------
const server = http.createServer(
  async (request, response) => {
        // CORS - allow GitHub Pages
    response.setHeader(
      "Access-Control-Allow-Origin",
      "https://anshthakre.github.io"
    );
    response.setHeader(
      "Access-Control-Allow-Methods",
      "GET, POST, OPTIONS"
    );
    response.setHeader(
      "Access-Control-Allow-Headers",
      "Content-Type"
    );

    if (request.method === "OPTIONS") {
      response.writeHead(204);
      response.end();
      return;
    }
    
    // Chat API
    if (
      request.method === "POST" &&
      request.url === "/api/chat"
    ) {

      await chat(request, response);
      return;
    }


    // Homepage
    if (
      request.method === "GET" &&
      (
        request.url === "/" ||
        request.url === "/index.html"
      )
    ) {

      response.writeHead(200, {
        "Content-Type":
          "text/html; charset=utf-8"
      });

      fs
        .createReadStream(
          path.join(root, "index.html")
        )
        .pipe(response);

      return;
    }


    // Not found
    response.writeHead(404, {
      "Content-Type":
        "text/plain; charset=utf-8"
    });

    response.end("Not found");
  }
);


// -----------------------------
// Start server
// -----------------------------
server.listen(port, () => {

  console.log(
    `KisanLink running at http://localhost:${port}`
  );

  console.log(
    `Gemini model: ${model}`
  );

});