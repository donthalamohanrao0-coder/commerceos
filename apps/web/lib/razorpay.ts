"use client";

/** Loads Razorpay Checkout once and opens it for a given order. Resolves with the
 *  browser-side proof of payment (to be verified server-side); rejects if the
 *  customer closes the window without paying. */

const SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

interface RazorpayResult {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

interface CheckoutParams {
  keyId: string;
  orderId: string;
  amountPaise: number;
  name: string;
  description: string;
  prefill?: { name?: string; email?: string };
}

let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("no window"));
  if ((window as { Razorpay?: unknown }).Razorpay) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<void>((resolve, reject) => {
    const el = document.createElement("script");
    el.src = SCRIPT_SRC;
    el.onload = () => resolve();
    el.onerror = () => {
      scriptPromise = null;
      reject(new Error("Could not load the payment window."));
    };
    document.body.appendChild(el);
  });
  return scriptPromise;
}

export class CheckoutDismissed extends Error {
  constructor() {
    super("Payment window closed before completing payment.");
    this.name = "CheckoutDismissed";
  }
}

export async function openCheckout(params: CheckoutParams): Promise<RazorpayResult> {
  await loadScript();
  const RazorpayCtor = (window as unknown as { Razorpay: new (opts: unknown) => { open: () => void } })
    .Razorpay;

  return new Promise<RazorpayResult>((resolve, reject) => {
    let settled = false;
    const rzp = new RazorpayCtor({
      key: params.keyId,
      order_id: params.orderId,
      amount: params.amountPaise,
      currency: "INR",
      name: params.name,
      description: params.description,
      prefill: params.prefill,
      theme: { color: "#1c1c1a" },
      handler: (res: RazorpayResult) => {
        settled = true;
        resolve(res);
      },
      modal: {
        ondismiss: () => {
          if (!settled) reject(new CheckoutDismissed());
        },
      },
    });
    rzp.open();
  });
}
