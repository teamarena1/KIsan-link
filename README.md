# KisanLink — Smart Agricultural Marketplace

A full-stack agricultural marketplace for farmers, FPOs, processors, retailers and institutional buyers.

## Run
1. Start the application with Python 3: `python server.py`.
2. Open `http://localhost:3000`.
3. The server creates and synchronizes separate stores: `data/farmers.json`, `data/buyers.json`, and `data/transactions.json`. The legacy `data/kisanlink.json` aggregate is retained for compatibility.

Login accounts for local testing:
- Farmer: `farmer@kisanlink.local` / `farmer123`
- Admin: `admin@kisanlink.local` / `admin123`

On the login screen, users choose **Farmer**, **Buyer**, or **Administrator**. Farmer and buyer accounts can select **Create account** with a full name, unique email, and password of at least 6 characters. New accounts are automatically signed in with their selected role. Administrator accounts are created separately and cannot be self-registered.

Farmers get the produce marketplace, lots, quality, bidding, FPO and logistics tools. Buyers get a separate buyer dashboard, available farmer lots, buyer bids and purchase records. Administrators get the protected operations dashboard and all customer records.

The Python server includes the authenticated API and admin console. The older Node server remains available for environments that require Node.js, but use Python for the complete local experience.

## Permanent public hosting
The GitHub repository is source code only; GitHub Pages cannot run the Python API and will cause login POST requests to fail. For a permanent public service, create a Render Web Service from `teamarena1/KIsan-link`, choose the `render.yaml` blueprint, and deploy. Render will provide a URL such as `https://kisanlink.onrender.com`. Add `GEMINI_API_KEY` in the Render environment settings, then share that Render URL. The service must be awake for the free plan to respond.

Backend resources include `/api/markets`, `/api/buyers`, `/api/lots`, `/api/transactions`, `/api/bids`, `/api/assays`, `/api/grievances`, `/api/fpo-lots`, `/api/nwr`, `/api/profile`, `/api/chat`, and the admin-only `/api/admin/overview`. Existing data is migrated automatically into the separate JSON stores when the server starts.

Administrators see a separate **Administrator Dashboard** with live tables for customer accounts, farmer lots, transactions, bids, quality assessments, grievances, FPO lots and e-NWR requests. The dashboard and `/api/admin/data` endpoint are restricted to users with the `admin` role.

Run the server to use authentication, AI and server-backed saving. Opening `index.html` directly is not supported for the connected application.

## AI chatbot
The KisanLink Assistant is authenticated, uses the signed-in user's current lots, transactions and grievances, and supports follow-up questions. It uses Gemini for free-form answers when a key is configured and automatically falls back to a useful local assistant when no key or network is available.

For Gemini answers, set the API key in the terminal before starting the server:

```powershell
$env:GEMINI_API_KEY="your-gemini-key"
npm start
```

Then open `http://localhost:3000`. The key stays on the server and is never placed in the webpage. `GEMINI_MODEL` can optionally select another compatible Gemini model. The default local assistant works without a key.

## Implemented flows
- Farmer dashboard
- Market price comparison and sorting
- AI-style sell/wait recommendation
- Price trend and forecast UI
- Verified buyer marketplace
- Buyer reliability and payment history
- Digital lot creation
- Offer viewing/acceptance
- Digital quality assay with image-based AI pre-assessment
- Live bidding and bid history
- FPO aggregation and smart lot formation
- Logistics and storage screen
- Net realization calculator comparing sale, transport and storage costs
- Warehouse and e-NWR requests
- Transaction/payment tracking
- Evidence-linked grievance/dispute submission
- Farmer/FPO profile
- English/Hindi hero-language toggle
- Responsive mobile layout

## Important
AI recommendations and quality pre-assessment use the configured AI service or the local assistant fallback. For deployment, configure production authentication, secure file storage, verified warehouse/payment integrations, live market data and operational ML services.
