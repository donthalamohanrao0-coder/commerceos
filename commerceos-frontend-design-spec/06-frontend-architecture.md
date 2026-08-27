# CommerceOS — Frontend Architecture

## 1. Technology

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Motion
- TanStack Query
- React Hook Form
- Zod
- Supabase Auth client
- SSE for agent streaming

## 2. Directory Structure

```text
apps/web/
├── app/
│   ├── (customer)/
│   │   ├── chat/
│   │   ├── products/
│   │   ├── cart/
│   │   ├── checkout/
│   │   └── orders/
│   │
│   ├── (merchant)/
│   │   └── dashboard/
│   │       ├── overview/
│   │       ├── products/
│   │       ├── orders/
│   │       ├── customers/
│   │       ├── campaigns/
│   │       ├── agent/
│   │       ├── activity/
│   │       ├── knowledge/
│   │       ├── payments/
│   │       ├── audit/
│   │       └── settings/
│   │
│   ├── auth/
│   └── layout.tsx
│
├── components/
│   ├── ui/
│   ├── navigation/
│   ├── chat/
│   ├── commerce/
│   ├── product/
│   ├── cart/
│   ├── checkout/
│   ├── payment/
│   ├── agent/
│   ├── dashboard/
│   ├── analytics/
│   ├── audit/
│   └── knowledge/
│
├── features/
│   ├── chat/
│   ├── catalog/
│   ├── cart/
│   ├── checkout/
│   ├── orders/
│   ├── dashboard/
│   ├── campaigns/
│   ├── agent/
│   └── knowledge/
│
├── hooks/
├── lib/
│   ├── api/
│   ├── auth/
│   ├── analytics/
│   └── validation/
│
├── stores/
├── types/
├── styles/
└── tests/
```

## 3. Component Architecture

Prefer feature-owned components.

Example:

```text
features/chat/
├── components/
│   ├── ChatShell.tsx
│   ├── ChatMessage.tsx
│   ├── ProductCarousel.tsx
│   ├── ProductComparison.tsx
│   ├── AgentActivity.tsx
│   ├── UpsellCard.tsx
│   ├── CampaignCard.tsx
│   ├── CartPreview.tsx
│   └── PaymentApprovalCard.tsx
├── hooks/
├── api/
└── types.ts
```

## 4. API Boundary

The frontend should not contain commerce business logic.

Bad:

```text
Frontend calculates payment amount
```

Good:

```text
Frontend requests order summary
Backend calculates authoritative total
Frontend displays it
```

## 5. Data Fetching

Use TanStack Query for server state:
- Products
- Orders
- Dashboard metrics
- Campaigns
- Knowledge documents
- Agent traces

Use local state only for:
- UI toggles
- Composer drafts
- Temporary selections

## 6. Authentication

Supabase Auth manages identity.

The frontend sends authenticated requests to FastAPI.

Backend remains responsible for authorization.

## 7. Agent Streaming

Use SSE initially.

Example events:

```text
agent.started
agent.message.delta
agent.tool.started
agent.tool.completed
agent.approval.required
agent.completed
agent.failed
```

The UI maps events to rich components.

## 8. Rich Message Rendering

Do not store rendered HTML as the agent response.

Use typed message blocks.

Example:

```ts
type AgentMessage =
  | { type: "text"; content: string }
  | { type: "product_carousel"; products: Product[] }
  | { type: "comparison"; products: Product[] }
  | { type: "upsell"; product: Product; reason: string }
  | { type: "campaign"; discount: number; reason: string }
  | { type: "cart_preview"; cart: Cart }
  | { type: "approval"; action: ApprovalAction }
  | { type: "payment_status"; status: PaymentStatus };
```

This makes the frontend deterministic and safe.

## 9. Images

Product images should:
- Use Next.js Image
- Have fixed aspect-ratio containers
- Include meaningful alt text
- Use optimized sizes
- Avoid layout shift
- Have graceful fallback images

## 10. Error Boundary Strategy

Use route-level and component-level error boundaries.

An error in one dashboard card should not destroy the entire dashboard.

## 11. Performance

Priorities:
- Server-render stable content
- Lazy-load heavy charts
- Optimize images
- Avoid unnecessary client components
- Stream AI responses
- Cache read-heavy data where appropriate
- Keep initial JavaScript small

## 12. Security

Never expose:
- OpenAI API key
- Razorpay secret
- Supabase service-role key
- Pinecone secret
- Internal prompts
- Private customer information

All sensitive operations go through FastAPI.

## 13. Frontend Observability

Capture:
- Page errors
- API failures
- Web vitals
- Important user flows
- Payment UI failures

Sentry handles application errors/performance.
Langfuse handles AI traces.

## 14. Testing

Use:
- Vitest/React Testing Library for UI behavior where appropriate
- Playwright for critical end-to-end flows

Critical E2E paths:

```text
Customer search
Product add-to-cart
Checkout
Payment approval
Payment success
Payment failure recovery
Merchant dashboard
Campaign creation
Knowledge upload
Agent trace viewing
```

## 15. Definition of Done

A frontend feature is complete only when:
- Desktop works
- Mobile works where required
- Loading state exists
- Empty state exists
- Error state exists
- Accessibility checked
- API failure handled
- Keyboard navigation works
- Analytics/observability added where appropriate
- No console errors
- No visible layout shift
- Tests cover critical behavior
