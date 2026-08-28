# CommerceOS as a ChatGPT Custom GPT (Actions)

Lets ChatGPT act as an **external AI buyer** against the live CommerceOS backend,
using the Agent Commerce API.

Requires ChatGPT **Plus/Pro/Team** (the GPT builder) and the backend deployed at a
public HTTPS URL (`https://commerceos.onrender.com`).

## 1. Issue a buyer key

Merchant console → **AI buyers → Issue a key** (leave every scope checked). Copy
the `ack_live_…` value — shown once.

## 2. Create the GPT

1. ChatGPT → left sidebar → **GPTs → + Create** → **Configure** tab.
2. Name it e.g. *NovaTech Buyer*. Give it instructions (see §4).
3. **Actions → Create new action.**
4. **Schema** → **Import from URL**:
   `https://commerceos.onrender.com/api/v1/agent-commerce/openapi.json`
   (or paste the contents of [`openapi.json`](openapi.json) in this folder — same thing,
   generated from the backend).
5. **Authentication** → **API Key** → Auth Type **Bearer** → paste your
   `ack_live_…` key → Save.
6. The Available actions list should show: `listCatalog`, `getProduct`,
   `searchCatalog`, `createQuote`, `createOrder`, `getOrder`, `requestPayment`.

## 3. Test

In the GPT preview:

> Find a wireless mouse under ₹2,000 from the catalog, quote 1 unit, and tell me the total.

then

> Place the order, then request payment.

`requestPayment` with `confirmed=false` returns `approval_required` + the amount.
Approve, and it calls again with `confirmed=true` → a real Razorpay **test‑mode**
order id.

Check the merchant console → Overview → Audit trail (actor `external_agent`) and
AI buyers (key "last used").

## 4. Suggested GPT instructions

```
You are a purchasing agent that buys from the NovaTech merchant through its
Agent Commerce API. Rules:
- Prices are in paise (₹1 = 100 paise). Always show ₹.
- Never invent prices or totals — call createQuote and use its numbers.
- Order flow: searchCatalog/listCatalog → createQuote → createOrder → requestPayment.
- Call requestPayment with confirmed=false FIRST. Show the user the amount and ask
  for explicit confirmation. Only if they say yes, call requestPayment again with
  confirmed=true.
- If a call returns an error object, explain it plainly (e.g. a 403 means the key
  lacks that scope; "policy_denied" means the merchant blocked it).
- You do not need to send an Idempotency-Key; the server handles it.
```

## Notes

- The key is a **bearer credential** — anyone with it can place test orders on
  this merchant. Revoke it from the console when done.
- Render free tier sleeps after ~15 min idle; the first call may take ~50s.
- `openapi.json` is generated from the backend
  (`app/api/v1/agent_commerce.py`); regenerate if the API changes.
