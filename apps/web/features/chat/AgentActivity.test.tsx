import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ToolTraceRow } from "@/lib/types";

import { AgentActivity } from "./AgentActivity";

const trace: ToolTraceRow[] = [
  { tool: "catalog_search", status: "succeeded", output: {} },
  { tool: "cart_add_item", status: "succeeded", output: {} },
  { tool: "payment_request", status: "failed", output: {} },
];

describe("AgentActivity", () => {
  it("shows an honest, live-region thinking indicator while busy with no progress yet", () => {
    render(<AgentActivity busy />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(/thinking through your request/i);
  });

  it("streams the real steps as they arrive during a turn", () => {
    render(
      <AgentActivity
        busy
        liveSteps={[{ tool: "catalog_search", status: "succeeded" }]}
        livePlanning={["order_create"]}
      />,
    );
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Searched the catalogue");
    expect(status).toHaveTextContent(/preparing your order/i); // the in-flight step
  });

  it("renders nothing once idle with no trace", () => {
    const { container } = render(<AgentActivity busy={false} trace={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("summarises the real steps and flags failures, without leaking tool internals", async () => {
    render(<AgentActivity busy={false} trace={trace} />);
    const toggle = screen.getByRole("button", { name: /3 steps/i });
    expect(toggle).toHaveTextContent(/1 needed attention/i);

    await userEvent.click(toggle);
    expect(screen.getByText("Searched the catalogue")).toBeInTheDocument();
    expect(screen.getByText("Verified payment requirements")).toBeInTheDocument();
    // raw tool names never surface
    expect(screen.queryByText(/catalog_search/)).not.toBeInTheDocument();
    expect(screen.queryByText(/payment_request/)).not.toBeInTheDocument();
  });

  it("says all checks passed when nothing failed", () => {
    render(
      <AgentActivity
        busy={false}
        trace={[{ tool: "catalog_search", status: "succeeded", output: {} }]}
      />,
    );
    expect(screen.getByRole("button", { name: /all checks passed/i })).toBeInTheDocument();
  });
});
