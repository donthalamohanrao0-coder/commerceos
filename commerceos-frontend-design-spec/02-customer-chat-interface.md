# CommerceOS — Customer AI Chat Interface

## 1. Goal

The customer interface is the hero experience.

It should combine:
- Conversational AI
- Product discovery
- Rich product cards
- Cart interaction
- Upsell/cross-sell
- Campaigns
- Checkout
- Payment approval
- Order status

The user should never feel that they are chatting with a plain chatbot.

## 2. Main Layout

Desktop:

```text
┌─────────────────────────────────────────────────────────────┐
│ CommerceOS                         Orders   Cart   Account  │
├───────────────────────┬─────────────────────────────────────┤
│                       │                                     │
│ Conversation history  │        Active AI conversation       │
│                       │                                     │
│ New conversation      │                                     │
│ Recent conversations  │        Rich commerce responses      │
│                       │                                     │
│                       │                                     │
│                       │                                     │
│                       ├─────────────────────────────────────┤
│                       │ Ask anything...               Send  │
└───────────────────────┴─────────────────────────────────────┘
```

Mobile:
- Header
- Conversation
- Composer fixed near bottom
- Cart accessible from header
- Conversation history in drawer

## 3. Welcome State

Show:
- Short product-oriented greeting
- Example prompts
- Optional featured products

Example prompts:
- "Find a laptop for coding under ₹80,000"
- "Show me running shoes under ₹5,000"
- "What are today's best offers?"
- "Help me choose a wireless headset"

Example prompt chips should be clickable.

## 4. Message Types

The chat renderer should support:

```text
TextMessage
ProductCarousel
ProductGrid
ProductComparison
RecommendationCard
UpsellCard
CrossSellCard
CampaignCard
CartPreview
OrderPreview
PaymentApprovalCard
PaymentStatusCard
KnowledgeCitation
AgentActivity
ErrorRecoveryCard
```

This is one of the most important frontend architectural decisions.

## 5. AI Streaming

AI responses should stream.

During streaming:
- Show subtle typing indicator
- Render text progressively
- Keep scroll anchored intelligently
- Do not jump the user to the bottom if they are reading older content

## 6. Agent Activity

For tool execution, show a compact expandable activity panel.

Example:

```text
✦ Working on your request

✓ Understanding requirements
✓ Searching merchant catalog
● Comparing matching products
○ Checking available offers
```

After completion:

```text
3 products found · 1 offer available
```

The detailed technical trace remains in the merchant Agent Activity page.

## 7. Product Cards

Product cards shown inside chat must support:
- Image
- Brand
- Name
- Price
- Discount
- Key specs
- Stock
- Recommendation reason
- View details
- Add to cart

Example:

```text
┌──────────────────────────────┐
│                              │
│        Product Image         │
│                              │
├──────────────────────────────┤
│ Apple                        │
│ MacBook Air                  │
│                              │
│ ₹74,999                      │
│ 16GB · 512GB · M-series     │
│                              │
│ Best match for coding        │
│                              │
│ [View]        [Add to cart] │
└──────────────────────────────┘
```

## 8. Product Carousel

Desktop:
- 3 cards visible where space permits
- Horizontal scrolling for additional results

Mobile:
- One primary card
- Horizontal swipe

The first card should be clearly marked as "Best match" only when the recommendation engine has a reason.

## 9. Product Comparison

For comparison requests, use a compact comparison table/card.

Example rows:
- Price
- RAM
- Storage
- Processor
- Battery
- Warranty
- Availability

Highlight the recommended option.

## 10. Recommendation Explanation

Every strong recommendation should have an expandable "Why this?" explanation.

Example:

```text
Why this product?

✓ Within your ₹80,000 budget
✓ 16GB RAM
✓ 512GB SSD
✓ Suitable for development workloads
✓ In stock
```

## 11. Upsell

Upsells must feel helpful, not manipulative.

Example:

```text
Complete your setup

Wireless Mouse
₹1,499

Customers buying this laptop often add this.

[Add to cart]  [No thanks]
```

## 12. Cross-Sell

Use complementary product language.

Do not falsely claim popularity unless the backend has supporting data.

If the reason is model-generated rather than historical:
- Say "Recommended as a complement"
- Do not say "Most customers buy this"

## 13. Campaign UI

Campaigns must show:
- Original amount
- Discount
- Eligibility reason
- Final amount

Example:

```text
Offer applied

Order value             ₹76,498
Campaign discount      -₹1,000
──────────────────────────────
New total               ₹75,498

✓ Eligibility verified
```

## 14. Cart Preview

Show cart inline after meaningful cart changes.

Include:
- Products
- Quantity
- Price
- Discount
- Total
- View cart
- Checkout

## 15. Payment Approval

This is a high-trust component.

```text
Review your purchase

Laptop                         ₹74,999
Wireless Mouse                  ₹1,499
Campaign                      -₹1,000
────────────────────────────────────
Total                          ₹75,498

✓ Product availability verified
✓ Price verified
✓ Campaign verified
✓ Payment policy verified

[Cancel]                 [Confirm & Pay]
```

Do not initiate money movement merely because the AI inferred intent.

## 16. Payment Processing

Show:
- Processing indicator
- Order reference
- Clear "do not refresh" guidance only if genuinely needed
- Provider state is not exposed as raw technical errors

## 17. Payment Success

Use a restrained success animation.

Show:
- Success indicator
- Amount
- Order ID
- Product summary
- Estimated next step
- View order

## 18. Payment Failure

Example:

```text
Payment couldn't be completed

No duplicate charge was created.

We could not confirm the payment because
the payment provider timed out.

[Check payment status]   [Try again]
```

Never blindly create another payment attempt.

## 19. RAG Citations

When an answer uses merchant knowledge, optionally show:

```text
According to the merchant's return policy,
this product can be returned within 7 days.

Source: Return Policy · Section 4
```

Citation should be expandable.

## 20. Composer

Composer supports:
- Text
- Send
- Stop generation
- Disabled state
- Error retry
- Optional attachment button later

The send button should be an obvious, compact icon button.

## 21. Chat Persistence

Conversation state should survive:
- Page refresh
- Navigation
- Temporary network reconnect

Use backend session IDs, not only browser memory.

## 22. Safety UX

If an action requires approval:

```text
This action requires your confirmation.
```

If policy blocks it:

```text
I can't complete that automatically because
it exceeds the merchant's transaction policy.
```

Never expose internal policy implementation details that could help bypass controls.
