"""Retrieval-accuracy test set for the NovaTech knowledge corpus.

Each case: a realistic customer question, the ``document_id``(s) a correct
retrieval must surface, and (optionally) a phrase the top chunk should contain
for the answer to be *grounded*. Keep questions phrased the way a shopper would
ask them, not the way the doc is written — that's what makes it a real test.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalCase:
    question: str
    docs: tuple[str, ...]
    phrase: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


CASES: list[EvalCase] = [
    # --- shipping -------------------------------------------------------
    EvalCase("How long does standard delivery take?", ("shipping_policy",), "3–6 business days"),
    EvalCase("Is shipping free?", ("shipping_policy",), "₹2,000"),
    EvalCase("How much is delivery on a small order?", ("shipping_policy",), "₹99"),
    EvalCase("When do I get a tracking number?", ("shipping_policy", "customer_support_faq")),
    # --- returns -------------------------------------------------------
    EvalCase("What's the return window?", ("returns_policy",), "7 calendar days"),
    EvalCase("My laptop arrived cracked, what do I do?", ("returns_policy", "customer_support_faq"), "48 hours"),
    EvalCase("Can I return a final-sale item?", ("returns_policy",), "Final-sale"),
    EvalCase("How do I start a return?", ("customer_support_faq",), "Return Request"),
    # --- warranty / NovaCare ----------------------------------------------
    EvalCase("How long is the standard warranty on a laptop?", ("warranty_policy", "novacare_extended_warranty")),
    EvalCase("Does the warranty cover liquid damage?", ("warranty_policy",), "liquid damage"),
    EvalCase("What does NovaCare Plus add over Essential?", ("novacare_extended_warranty",), "accidental damage"),
    EvalCase("How much does NovaCare Complete cost?", ("novacare_extended_warranty",), "16%"),
    EvalCase("Is theft covered by the extended warranty?", ("novacare_extended_warranty",), "not insurance"),
    EvalCase("Can I get a battery replacement under the protection plan?", ("novacare_extended_warranty",), "80%"),
    EvalCase("How many days do I have to buy NovaCare after my laptop?", ("novacare_extended_warranty",), "45 days"),
    EvalCase("What's the service fee for a cracked screen claim on a laptop?", ("novacare_extended_warranty",), "3,500"),
    # --- payment -------------------------------------------------------
    EvalCase("What payment methods can I use?", ("payment_faq",), "UPI"),
    EvalCase("My payment page failed — was I charged twice?", ("payment_faq",), "second payment"),
    EvalCase("Can the assistant pay for me automatically?", ("payment_faq",), "confirmation"),
    # --- recommendation guide ------------------------------------------
    EvalCase("How much RAM do I need for software development?", ("product_recommendation_guide",), "16GB"),
    EvalCase("What matters most in a laptop for students?", ("product_recommendation_guide",), "value"),
    EvalCase("What accessories go with a desk setup?", ("product_recommendation_guide",), "stand"),
    # --- bulk / business --------------------------------------------------
    EvalCase("What's the discount for buying 30 laptops?", ("bulk_and_business_orders",), "8%"),
    EvalCase("Can my company pay on invoice instead of upfront?", ("bulk_and_business_orders",), "net-30"),
    EvalCase("How many units counts as a bulk order?", ("bulk_and_business_orders",), "10 units"),
    EvalCase("Is express shipping available for bulk orders?", ("bulk_and_business_orders",), "not available"),
    EvalCase("What's the restocking fee if I cancel a bulk order after it ships?", ("bulk_and_business_orders",), "15%"),
    EvalCase("Do you offer custom OS imaging for large orders?", ("bulk_and_business_orders",), "imaging"),
    # --- trade-in -------------------------------------------------------
    EvalCase("Can I trade in my old laptop?", ("trade_in_program",), "partial payment"),
    EvalCase("How old can a trade-in phone be?", ("trade_in_program",), "5 years"),
    EvalCase("What if my device doesn't turn on?", ("trade_in_program",), "recycle-only"),
    EvalCase("How long do I have to send in my trade-in device?", ("trade_in_program",), "14 days"),
    EvalCase("Is trade-in credit paid out as cash?", ("trade_in_program",), "not paid out as cash"),
    # --- education / GST ------------------------------------------------
    EvalCase("Do you have a student discount?", ("education_and_gst_invoicing",), "8%"),
    EvalCase("How do I verify I'm a student?", ("education_and_gst_invoicing",), "institution email"),
    EvalCase("Can I get a GST invoice in my company's name?", ("education_and_gst_invoicing",), "GSTIN"),
    EvalCase("Is GST charged before or after the trade-in credit?", ("education_and_gst_invoicing",), "before"),
    EvalCase("I forgot to add my GSTIN — can you fix the invoice?", ("education_and_gst_invoicing",), "7 days"),
]
