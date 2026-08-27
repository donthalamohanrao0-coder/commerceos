# CommerceOS — Frontend Design System

## 1. Product Vision

CommerceOS should feel like a premium, trustworthy AI-native commerce platform.

Visual references in spirit:
- Apple: simplicity and restraint
- Linear: precision and density
- Stripe: financial clarity
- Vercel: modern technical polish
- Premium AI products: conversational and responsive

Do not make the UI look like a generic AI dashboard.

## 2. Design Principles

1. Clarity over decoration.
2. Commerce actions must always be obvious.
3. Money-related actions must feel trustworthy.
4. AI reasoning should be visible without overwhelming the user.
5. Product imagery should be high quality and consistent.
6. Every screen needs polished loading, empty, success, and failure states.
7. Motion should communicate state changes, not exist for decoration.
8. Desktop-first for merchant operations, responsive-first for customer commerce.
9. Accessibility is a requirement, not a final polish task.
10. Use one coherent visual language across customer and merchant surfaces.

## 3. Visual Language

### Colors

Use semantic tokens rather than hard-coded colors.

- Background: warm/cool neutral near-white
- Foreground: deep neutral
- Muted foreground: secondary neutral
- Border: subtle neutral
- Surface: white / elevated neutral
- Primary: restrained dark/brand accent
- Success: semantic green
- Warning: semantic amber
- Destructive: semantic red
- Info: semantic blue

Dark mode may be supported later, but the primary demo should be light and premium.

Avoid excessive gradients, neon colors, glassmorphism, and saturated purple AI styling.

## 4. Typography

Recommended:
- Inter or Geist Sans for UI
- Geist Mono for technical identifiers, transaction IDs, timestamps, and code-like data

Hierarchy:
- Display: 40–56px
- Page title: 28–36px
- Section title: 20–24px
- Card title: 15–18px
- Body: 14–16px
- Metadata: 12–13px

Use tight headings and comfortable body line-height.

## 5. Spacing

Use a consistent 4px base grid.

Common values:
- 4, 8, 12, 16, 20, 24, 32, 40, 48, 64

Do not create arbitrary one-off spacing values.

## 6. Radius

Use restrained radii:
- Small controls: 8px
- Inputs/buttons: 10–12px
- Cards: 12–16px
- Large panels: 16–20px

Avoid excessively rounded "AI startup" cards.

## 7. Shadows

Use shadows sparingly.

Preferred hierarchy:
- Flat surfaces for most UI
- Very subtle shadow for floating panels
- Stronger shadow only for dialogs, menus, and payment approval surfaces

## 8. Buttons

Primary:
- High contrast
- Clear verb
- Loading state
- Disabled state
- Keyboard focus state

Examples:
- Add to cart
- View product
- Compare
- Confirm & Pay
- Create campaign
- Approve action

Secondary:
- View details
- Cancel
- No thanks
- Try again

Destructive:
- Refund
- Delete
- Disable campaign

Never use vague labels such as "Continue" when "Confirm & Pay" is possible.

## 9. Product Cards

Every product card can contain:
- Product image
- Brand
- Product name
- Price
- Original price
- Discount badge
- Stock indicator
- Variant summary
- AI recommendation reason
- Primary action

Image aspect ratio should remain consistent.

## 10. Inputs

Inputs must support:
- Placeholder
- Label where needed
- Validation
- Loading
- Disabled
- Error
- Keyboard focus

Customer chat input should be visually dominant but not oversized.

## 11. Badges

Use badges for:
- In stock
- Low stock
- Recommended
- Best match
- Campaign
- Payment pending
- Payment successful
- Requires approval

Never use badges as decoration.

## 12. Cards and Panels

Use cards to establish hierarchy, not to wrap every sentence.

Premium layout:
- Strong whitespace
- One clear title
- Supporting metadata
- One primary action

## 13. Motion

Use Motion for:
- Product card entrance
- Cart updates
- Streaming AI responses
- Tool activity state changes
- Modal transitions
- Toasts
- Successful payment confirmation

Keep animation short and subtle.

Recommended:
- 150–250ms for micro-interactions
- 250–400ms for panels/modals

Respect `prefers-reduced-motion`.

## 14. Loading States

Every asynchronous component needs a deliberate loading state.

Examples:
- Product skeleton
- AI typing/streaming state
- Agent tool activity
- Dashboard metric skeleton
- Payment processing state

Never leave a blank screen while data loads.

## 15. Error States

Errors should explain:
1. What happened
2. What is safe
3. What the user can do next

Never expose raw stack traces or provider errors.

## 16. Empty States

Empty states should explain:
- What is empty
- Why it may be empty
- The next useful action

## 17. Accessibility

Required:
- Semantic HTML
- Keyboard navigation
- Visible focus states
- Accessible labels
- Sufficient contrast
- Screen-reader-friendly status messages
- No color-only status indicators

## 18. Responsive Strategy

Customer:
- Mobile-first
- Tablet supported
- Desktop optimized

Merchant:
- Desktop-first
- Tablet supported
- Mobile should provide functional access to key pages

Important commerce actions must remain usable at 320px width.

## 19. Frontend Component Categories

```text
components/
├── ui/
├── navigation/
├── chat/
├── commerce/
├── product/
├── cart/
├── checkout/
├── payment/
├── agent/
├── dashboard/
├── analytics/
├── audit/
└── knowledge/
```

## 20. Quality Bar

Before a page is considered complete:
- Loading state exists
- Empty state exists
- Error state exists
- Success state exists where applicable
- Keyboard navigation works
- Mobile layout is checked
- No layout shift on image loading
- Buttons have clear actions
- Animations feel intentional
- Visual hierarchy is obvious
