import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button, EmptyState, ErrorState, Field } from "./index";

describe("Button", () => {
  it("blocks clicks and marks itself busy while loading", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Confirm &amp; Pay
      </Button>,
    );
    const btn = screen.getByRole("button", { name: /confirm & pay/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
    await userEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Field", () => {
  it("links its label and surfaces validation errors accessibly", () => {
    render(<Field label="Email" name="email" error="Required" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Required")).toBeInTheDocument();
  });
});

describe("EmptyState / ErrorState", () => {
  it("EmptyState explains what and offers an action slot", () => {
    render(<EmptyState title="Nothing here" description="Try something" action={<button>Go</button>} />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });

  it("ErrorState is announced and can retry", async () => {
    const onRetry = vi.fn();
    render(<ErrorState description="It broke" onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("It broke");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
