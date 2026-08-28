import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DataTable, QueryBoundary, type Column } from "./Shared";

interface Q<T> {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  data: T | undefined;
  refetch: () => void;
}

function q<T>(over: Partial<Q<T>>): Q<T> {
  return {
    isLoading: false,
    isError: false,
    error: null,
    data: undefined,
    refetch: vi.fn(),
    ...over,
  };
}

describe("QueryBoundary", () => {
  it("renders skeletons while loading", () => {
    const { container } = render(
      <QueryBoundary query={q({ isLoading: true })} skeletonRows={3}>
        {() => <div>data</div>}
      </QueryBoundary>,
    );
    expect(container.querySelectorAll(".co-shimmer")).toHaveLength(3);
  });

  it("shows a retry-able error state on failure", async () => {
    const refetch = vi.fn();
    render(
      <QueryBoundary query={q({ isError: true, error: new Error("boom"), refetch })}>
        {() => <div>data</div>}
      </QueryBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(refetch).toHaveBeenCalledOnce();
  });

  it("shows the empty state when the data is empty", () => {
    render(
      <QueryBoundary
        query={q<number[]>({ data: [] })}
        isEmpty={(d) => d.length === 0}
        emptyState={<p>nothing here</p>}
      >
        {() => <div>data</div>}
      </QueryBoundary>,
    );
    expect(screen.getByText("nothing here")).toBeInTheDocument();
  });

  it("renders children with the resolved data", () => {
    render(
      <QueryBoundary query={q<{ n: number }>({ data: { n: 7 } })}>
        {(d) => <div>value {d.n}</div>}
      </QueryBoundary>,
    );
    expect(screen.getByText("value 7")).toBeInTheDocument();
  });
});

describe("DataTable", () => {
  interface Row {
    id: string;
    name: string;
    total: number;
  }
  const columns: Column<Row>[] = [
    { key: "name", header: "Name", cell: (r) => r.name },
    { key: "total", header: "Total", align: "right", cell: (r) => `₹${r.total}` },
  ];
  const rows: Row[] = [
    { id: "a", name: "Alpha", total: 10 },
    { id: "b", name: "Beta", total: 20 },
  ];

  it("renders headers and a row per record", () => {
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.id} />);
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3); // header + 2
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("₹20")).toBeInTheDocument();
  });

  it("renders an empty body when there are no rows", () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(r) => r.id} />);
    expect(screen.getAllByRole("row")).toHaveLength(1); // just the header
  });
});
