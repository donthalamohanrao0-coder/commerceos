import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ChatBlock } from "./deriveBlocks";
import { QuickReplies } from "./QuickReplies";
import type { AssistantEntry } from "./useChat";

function entry(blocks: ChatBlock[], overrides: Partial<AssistantEntry> = {}): AssistantEntry {
  return {
    id: "e1",
    kind: "assistant",
    text: "",
    blocks,
    trace: [],
    pendingApproval: null,
    approvalOrder: null,
    approvalResolved: null,
    failed: false,
    ...overrides,
  };
}

describe("QuickReplies", () => {
  it("suggests comparison / price / offers after a product carousel", () => {
    render(<QuickReplies entry={entry([{ type: "products", products: [] }])} disabled={false} onPick={vi.fn()} />);
    expect(screen.getByRole("button", { name: /compare the top two/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cheaper options/i })).toBeInTheDocument();
  });

  it("suggests checkout after a cart update", () => {
    render(<QuickReplies entry={entry([{ type: "cart", cartId: "c1", itemCount: 1, subtotalPaise: 10 }])} disabled={false} onPick={vi.fn()} />);
    expect(screen.getByRole("button", { name: /proceed to checkout/i })).toBeInTheDocument();
  });

  it("suggests tracking after a successful payment", () => {
    render(
      <QuickReplies
        entry={entry([{ type: "payment_status", state: "success" }])}
        disabled={false}
        onPick={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /track my order/i })).toBeInTheDocument();
  });

  it("renders nothing while an approval is pending (the card owns the next action)", () => {
    const { container } = render(
      <QuickReplies
        entry={entry([{ type: "order", order: {} as never }], {
          pendingApproval: { approval_id: "a1", action: "payment_initiation" },
        })}
        disabled={false}
        onPick={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("calls onPick with the chip text", async () => {
    const onPick = vi.fn();
    render(<QuickReplies entry={entry([{ type: "products", products: [] }])} disabled={false} onPick={onPick} />);
    await userEvent.click(screen.getByRole("button", { name: /compare the top two/i }));
    expect(onPick).toHaveBeenCalledWith("Compare the top two");
  });

  it("disables chips while a turn is in flight", () => {
    render(<QuickReplies entry={entry([{ type: "products", products: [] }])} disabled onPick={vi.fn()} />);
    expect(screen.getByRole("button", { name: /compare the top two/i })).toBeDisabled();
  });
});
