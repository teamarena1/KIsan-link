const http = require("http");
const fs = require("fs");
const path = require("path");

const port = Number(process.env.PORT || 3000);
const root = __dirname;
const dataDir = path.join(root, "data");
const dbFile = path.join(dataDir, "kisanlink.json");

const seed = {
	lots: [
		{ id: "LOT-1042", crop: "Tomato", qty: "5,000 kg", quality: "Grade A", offer: "₹27/kg", status: "Offer received" },
		{ id: "LOT-1038", crop: "Onion", qty: "3,000 kg", quality: "Grade A", offer: "₹33/kg", status: "Bidding" },
		{ id: "LOT-1021", crop: "Soybean", qty: "8,000 kg", quality: "FAQ", offer: "₹51/kg", status: "Sold" }
	],
	transactions: [
		["TXN-1002", "GreenHarvest Foods", "₹1,35,000", "Pending", "Pickup scheduled", "Today"],
		["TXN-0998", "CityMart Institutions", "₹98,000", "Paid ✓", "Delivered", "18 Aug"],
		["TXN-0984", "Vidarbha Foods", "₹4,08,000", "Paid ✓", "Delivered", "12 Aug"],
		["TXN-0971", "RuralLink Traders", "₹5,92,000", "Paid ✓", "Delivered", "08 Aug"]
	],
	bids: [],
	assays: [],
	grievances: [],
	fpoLots: [],
	nwrRequests: [],
	profile: { name: "Vansh Thakre", accountType: "Individual Farmer", district: "Nagpur", state: "Maharashtra", crops: "Tomato, Onion, Soybean" }
};

function readDb() {
	fs.mkdirSync(dataDir, { recursive: true });
	if (!fs.existsSync(dbFile)) fs.writeFileSync(dbFile, JSON.stringify(seed, null, 2));
	return JSON.parse(fs.readFileSync(dbFile, "utf8"));
}
function writeDb(db) { fs.writeFileSync(dbFile, JSON.stringify(db, null, 2)); }
function sendJson(res, status, body) { res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*" }); res.end(JSON.stringify(body)); }
function readBody(req) { return new Promise((resolve, reject) => { let body = ""; req.on("data", chunk => { body += chunk; if (body.length > 1e6) req.destroy(); }); req.on("end", () => { try { resolve(body ? JSON.parse(body) : {}); } catch { reject(new Error("Invalid JSON request")); } }); req.on("error", reject); }); }
function id(prefix) { return `${prefix}-${Date.now().toString(36).toUpperCase()}`; }
function today() { return new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }); }

async function api(req, res, pathname) {
	const db = readDb();
	if (req.method === "GET" && pathname === "/api/state") return sendJson(res, 200, db);
	if (req.method === "POST" && pathname === "/api/chat") {
		let input;
		try { input = await readBody(req); } catch (error) { return sendJson(res, 400, { error: error.message }); }
		if (!input.message || typeof input.message !== "string") return sendJson(res, 400, { error: "message is required" });
		return sendJson(res, 200, { reply: "KisanLink Assistant: I can help with market prices, verified buyers, lots, quality checks, bidding, logistics, transactions and grievances. The records in this prototype are stored in the local database." });
	}
	if (req.method !== "POST" && req.method !== "PUT") return sendJson(res, 405, { error: "Method not allowed" });
	let input;
	try { input = await readBody(req); } catch (error) { return sendJson(res, 400, { error: error.message }); }

	if (pathname === "/api/lots" && req.method === "POST") {
		const lot = { id: id("LOT"), crop: input.crop, qty: `${Number(input.qty).toLocaleString("en-IN")} kg`, quality: input.quality, offer: "Awaiting", status: "Published", expectedPrice: Number(input.price) || 0, deliveryDate: input.deliveryDate || "" };
		if (!lot.crop || !input.qty || !lot.quality) return sendJson(res, 400, { error: "crop, qty and quality are required" });
		db.lots.unshift(lot); writeDb(db); return sendJson(res, 201, lot);
	}
	if (pathname === "/api/transactions" && req.method === "POST") {
		const transaction = [id("TXN"), input.buyer || "Verified Buyer", input.amount || "₹0", "Pending", "Pickup scheduled", today()];
		db.transactions.unshift(transaction); writeDb(db); return sendJson(res, 201, transaction);
	}
	if (pathname === "/api/bids" && req.method === "POST") {
		if (!input.amount || Number(input.amount) < 1) return sendJson(res, 400, { error: "A valid bid amount is required" });
		const bid = { id: id("BID"), lotId: input.lotId || "LOT-1042", amount: Number(input.amount), createdAt: new Date().toISOString() };
		db.bids.unshift(bid); writeDb(db); return sendJson(res, 201, bid);
	}
	if (pathname === "/api/assays" && req.method === "POST") {
		const assay = { id: id("ASSAY"), lotId: input.lotId, crop: input.crop, grade: "A", confidence: 91, damage: 2, notes: input.notes || "", createdAt: new Date().toISOString() };
		db.assays.unshift(assay); writeDb(db); return sendJson(res, 201, assay);
	}
	if (pathname === "/api/grievances" && req.method === "POST") {
		const grievance = { id: id("GRV"), reference: input.reference, type: input.type, description: input.description, evidence: input.evidence || "No attachment", status: "SUBMITTED", createdAt: new Date().toISOString() };
		if (!grievance.reference || !grievance.description) return sendJson(res, 400, { error: "reference and description are required" });
		db.grievances.unshift(grievance); writeDb(db); return sendJson(res, 201, grievance);
	}
	if (pathname === "/api/fpo-lots" && req.method === "POST") {
		const lot = { id: id("FPO-LOT"), crop: input.crop || "Tomato", qty: input.qty || "5,000 kg", quality: "Grade A", offer: "Awaiting", status: "Aggregation open" };
		db.fpoLots.unshift(lot); db.lots.unshift(lot); writeDb(db); return sendJson(res, 201, lot);
	}
	if (pathname === "/api/nwr" && req.method === "POST") {
		const request = { id: id("NWR"), lotId: input.lotId || "LOT-1042", status: "REQUESTED", createdAt: new Date().toISOString() };
		db.nwrRequests.unshift(request); writeDb(db); return sendJson(res, 201, request);
	}
	if (pathname === "/api/profile" && req.method === "PUT") { db.profile = { ...db.profile, ...input }; writeDb(db); return sendJson(res, 200, db.profile); }
	return sendJson(res, 404, { error: "API route not found" });
}

const server = http.createServer(async (req, res) => {
	const parsed = new URL(req.url, `http://${req.headers.host || "localhost"}`);
	if (req.method === "OPTIONS") { res.writeHead(204, { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS", "Access-Control-Allow-Headers": "Content-Type" }); return res.end(); }
	if (parsed.pathname.startsWith("/api/")) return api(req, res, parsed.pathname).catch(error => sendJson(res, 500, { error: error.message }));
	if (req.method === "GET" && (parsed.pathname === "/" || parsed.pathname === "/index.html")) { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }); return fs.createReadStream(path.join(root, "index.html")).pipe(res); }
	res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }); res.end("Not found");
});
server.listen(port, () => console.log(`KisanLink running at http://localhost:${port}`));
