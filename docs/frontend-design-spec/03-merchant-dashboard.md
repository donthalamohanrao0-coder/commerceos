# CommerceOS — Merchant Dashboard

## 1. Goal

The merchant dashboard should answer one question immediately:

> "Is AI actually helping my business?"

The dashboard should feel like a premium financial/commerce operations product.

## 2. Global Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ CommerceOS     Search...                 Notifications  User │
├───────────────┬──────────────────────────────────────────────┤
│ Overview      │                                              │
│ Products      │              Page content                    │
│ Orders        │                                              │
│ Customers     │                                              │
│ Campaigns     │                                              │
│ AI Agent      │                                              │
│ Agent Activity│                                              │
│ Knowledge     │                                              │
│ Payments      │                                              │
│ Audit Log     │                                              │
│ Settings      │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

Sidebar:
- Collapsible
- Icon + label
- Active state
- Tooltips when collapsed

## 3. Overview

Top metrics:
- Total revenue
- AI-assisted revenue
- Conversion rate
- Average order value

Secondary metrics:
- Upsell revenue
- Cross-sell revenue
- AI-assisted orders
- Payment success rate

Use clear period selectors:
- Today
- 7 days
- 30 days
- Custom

## 4. Revenue Chart

Show:
- Revenue
- AI-assisted revenue
- Orders

Hover state:
- Exact timestamp
- Amount
- Order count

Avoid visual clutter.

## 5. AI Revenue Opportunities

This is a hero feature.

Example:

```text
Revenue opportunity

Customers purchasing laptops have a strong
cross-sell opportunity for accessories.

Estimated monthly opportunity
₹42,000

Confidence
High

[View analysis] [Create campaign]
```

Every insight should explain:
- What was detected
- Evidence
- Expected impact
- Recommended action

## 6. Campaigns

Campaign table:
- Name
- Status
- Type
- Eligibility
- Redemptions
- Revenue
- Last updated

Campaign detail:
- Rules
- Products
- Discount
- Limits
- Performance
- Agent recommendation

## 7. Products

Product management:
- Search
- Filters
- Category
- Stock status
- Price
- Sales
- AI recommendations

Product detail:
- Images
- Variants
- Inventory
- Description
- Policies
- AI sales performance

## 8. Orders

Columns:
- Order ID
- Customer
- Amount
- Payment status
- Order status
- Created
- Source

Source can include:
- Customer
- AI-assisted
- External AI buyer

## 9. Customers

Show:
- Customer name
- Orders
- Revenue
- AOV
- Last order
- AI interaction count

Do not expose unnecessary personal information.

## 10. AI Agent

Configuration page:
- Agent status
- Allowed actions
- Transaction limit
- Auto-discount limit
- Refund limit
- Approval requirements

Show a readable policy summary.

## 11. Agent Activity

This should be a first-class page.

Timeline:

```text
Payment completed
₹75,498
2 minutes ago

Campaign applied
₹1,000 discount

Cross-sell accepted
Wireless Mouse

Recommendation generated
Laptop #102
```

Click an event to open:
- Input
- Agent decision
- Tools used
- Evidence
- Policy result
- Outcome

## 12. Agent Trace Detail

Use a split layout:

Left:
- Timeline / graph

Right:
- Selected step details

Example:

```text
Recommendation
────────────────────
Input:
Coding laptop under ₹80k

Evidence:
16GB RAM
512GB SSD
₹74,999

Policy:
Passed

Result:
Product #102
```

## 13. Knowledge Base

Show:
- Documents
- Status
- Version
- Indexed chunks
- Last indexed
- Errors

Upload flow:
1. Select file
2. Upload
3. Processing
4. Chunking
5. Embedding
6. Pinecone indexing
7. Ready

## 14. Payments

Show:
- Total payment volume
- Successful
- Failed
- Pending
- Refunds

Payment detail:
- Order
- Attempts
- Razorpay reference
- Webhook events
- Current state

## 15. Audit Log

Filters:
- Actor
- Action
- Order
- Payment
- Date
- Status

Each audit event should be immutable in the UI.

## 16. Notifications

Use notifications for:
- Failed payment
- Agent policy block
- Knowledge ingestion failure
- Campaign recommendation
- Refund requiring approval

## 17. Responsive Dashboard

Desktop is primary.

Tablet:
- Collapsible sidebar
- Responsive tables

Mobile:
- Important metrics
- Orders
- Alerts
- Agent activity
- Approvals

Complex configuration can remain desktop-oriented.

## 18. Dashboard Empty States

Examples:
- No orders yet
- No campaigns
- No knowledge documents
- No AI activity

Each should provide an actionable next step.

## 19. Dashboard Loading

Use skeletons preserving final layout dimensions.

Avoid page-wide spinners.

## 20. Dashboard Visual Quality

Use:
- Consistent card density
- Strong alignment
- Restrained borders
- High information clarity
- Minimal decorative elements

The dashboard should look operational, not marketing-heavy.
