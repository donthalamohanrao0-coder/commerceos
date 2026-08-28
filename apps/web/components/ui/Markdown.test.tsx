import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("renders bold, lists and headings from the assistant's markdown", () => {
    render(
      <Markdown>{"**NovaBook Pro 14**\n\n- 16GB RAM\n- 512GB SSD\n\n# In stock"}</Markdown>,
    );
    expect(screen.getByText("NovaBook Pro 14").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("In stock")).toBeInTheDocument();
  });

  it("neutralises links (renders the text, not an anchor)", () => {
    render(<Markdown>{"See [our site](https://evil.example) for more"}</Markdown>);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("our site")).toBeInTheDocument();
  });

  it("renders plain paragraphs unchanged", () => {
    render(<Markdown>{"Just a sentence."}</Markdown>);
    expect(screen.getByText("Just a sentence.")).toBeInTheDocument();
  });
});
