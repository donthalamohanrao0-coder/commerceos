import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthGuard } from "./AuthGuard";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/console",
}));

const auth = {
  session: null as unknown,
  identity: null as unknown,
  loading: true,
  error: null as string | null,
  reloadIdentity: vi.fn(),
  signOut: vi.fn(),
};
vi.mock("@/lib/auth", () => ({ useAuth: () => auth }));

beforeEach(() => {
  auth.session = null;
  auth.identity = null;
  auth.loading = true;
  auth.error = null;
  vi.clearAllMocks();
});

describe("AuthGuard", () => {
  it("spins while auth is still resolving", () => {
    auth.loading = true;
    render(
      <AuthGuard>
        <div>secret</div>
      </AuthGuard>,
    );
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("redirects to login when there is no session", () => {
    auth.loading = false;
    auth.session = null;
    render(
      <AuthGuard>
        <div>secret</div>
      </AuthGuard>,
    );
    expect(replace).toHaveBeenCalledWith("/login?next=%2Fconsole");
  });

  it("shows a recoverable error (not an infinite spinner) when identity fails to load", async () => {
    auth.loading = false;
    auth.session = { access_token: "t" };
    auth.identity = null;
    auth.error = "Something went wrong on our side. Please try again.";

    render(
      <AuthGuard>
        <div>secret</div>
      </AuthGuard>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/couldn't load your workspace/i);
    expect(screen.getByText(/something went wrong on our side/i)).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(auth.reloadIdentity).toHaveBeenCalledOnce();

    await userEvent.click(screen.getByRole("button", { name: /sign out/i }));
    expect(auth.signOut).toHaveBeenCalledOnce();
  });

  it("renders children once the session and identity are both present", () => {
    auth.loading = false;
    auth.session = { access_token: "t" };
    auth.identity = { user: {}, merchant: {} };
    render(
      <AuthGuard>
        <div>secret</div>
      </AuthGuard>,
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
  });
});
