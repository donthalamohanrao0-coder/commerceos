# CommerceOS — Agent Evaluation Strategy

## 1. Goal

Treat the agent as a software system that must be evaluated continuously.

## 2. Evaluation Categories

### Intent
Did the agent identify the correct task?

### Retrieval
Did it retrieve useful products/documents?

### Tool selection
Did it choose the correct tool?

### Tool arguments
Were arguments correct and within policy?

### Policy
Did it obey financial boundaries?

### Grounding
Did it avoid unsupported claims?

### Commerce
Did it select the correct product/order?

### Safety
Did it refuse unauthorized actions?

## 3. Dataset

Maintain representative queries:
- shopping
- comparison
- upsell
- support
- campaign
- payment
- refund
- adversarial requests

## 4. Regression

Every discovered failure becomes a test case.

## 5. Scores

Useful metrics:
- task success
- tool accuracy
- policy compliance
- groundedness
- retrieval relevance
- refusal correctness
- latency
- cost

## 6. Release Gate

A new prompt/model version should not be promoted if critical safety or commerce metrics regress.

## 7. Langfuse

Use Langfuse datasets, traces, scores, evaluations, and experiments as the AI evaluation workflow.
