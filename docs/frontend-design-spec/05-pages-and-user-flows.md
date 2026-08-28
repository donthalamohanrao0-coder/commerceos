# CommerceOS — Frontend Pages and User Flows

## 1. Customer Application

```text
/
├── Home
├── Chat
├── Products
│   └── [productId]
├── Cart
├── Checkout
├── Payment
├── Orders
│   └── [orderId]
└── Account
```

## 2. Merchant Application

```text
/dashboard
├── Overview
├── Products
│   └── [productId]
├── Orders
│   └── [orderId]
├── Customers
│   └── [customerId]
├── Campaigns
│   ├── List
│   ├── Create
│   └── [campaignId]
├── AI Agent
├── Agent Activity
│   └── [traceId]
├── Knowledge Base
├── Payments
│   └── [paymentId]
├── Audit Log
└── Settings
```

## 3. Customer Purchase Flow

```text
Home
 ↓
Chat
 ↓
Customer request
 ↓
Intent detection
 ↓
Product recommendations
 ↓
Product detail / compare
 ↓
Add to cart
 ↓
Upsell / cross-sell
 ↓
Campaign calculation
 ↓
Cart
 ↓
Checkout
 ↓
Payment approval
 ↓
Razorpay
 ↓
Payment confirmation
 ↓
Order confirmation
```

## 4. Customer Failure Flow

```text
Payment
 ↓
Provider timeout/failure
 ↓
Backend checks actual payment state
 ↓
State resolved
 ├── Paid → confirmation
 ├── Failed → safe retry
 └── Unknown → status check
```

## 5. Merchant Onboarding

```text
Sign up
 ↓
Create merchant
 ↓
Configure store
 ↓
Upload catalog
 ↓
Upload business documents
 ↓
Configure policies
 ↓
Configure agent limits
 ↓
Configure campaigns
 ↓
Test agent
 ↓
Publish
```

## 6. Knowledge Upload

```text
Knowledge Base
 ↓
Upload document
 ↓
Supabase Storage
 ↓
Processing
 ↓
Chunking
 ↓
OpenAI embeddings
 ↓
Pinecone
 ↓
Indexed
 ↓
Ready
```

## 7. Merchant Campaign Flow

```text
Dashboard
 ↓
Revenue opportunity
 ↓
View evidence
 ↓
Review recommendation
 ↓
Create campaign
 ↓
Configure rules
 ↓
Policy validation
 ↓
Merchant approval
 ↓
Activate
 ↓
Monitor performance
```

## 8. External AI Buyer Flow

```text
External AI
 ↓
Agent Commerce API
 ↓
Discover catalog
 ↓
Search products
 ↓
Select product
 ↓
Create cart
 ↓
Create order
 ↓
Policy check
 ↓
Customer approval
 ↓
Payment
 ↓
Webhook
 ↓
Order confirmed
```

## 9. Audit Flow

```text
Any important action
 ↓
Backend event
 ↓
Audit event
 ↓
Merchant Agent Activity
 ↓
Trace detail
```

## 10. Navigation Rules

Customer:
- Keep Chat as the primary destination.
- Cart and Orders always accessible.
- Avoid deep navigation during checkout.

Merchant:
- Sidebar remains persistent on desktop.
- Search and notifications remain accessible globally.
- Current workspace is always obvious.

## 11. Global States

Every page must account for:
- Initial loading
- Partial loading
- Empty
- Success
- Recoverable error
- Fatal error
- Permission denied
- Session expired

## 12. Deep Links

Every meaningful object should have a stable URL:
- Product
- Order
- Campaign
- Agent trace
- Payment
- Knowledge document

## 13. Browser Navigation

Customer checkout must preserve state across:
- Back
- Forward
- Refresh
- Temporary reconnect

Do not rely solely on in-memory React state.
