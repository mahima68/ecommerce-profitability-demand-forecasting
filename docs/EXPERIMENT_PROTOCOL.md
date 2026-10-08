# Price experiment protocol

This is a proposed real-world test and a separately labeled synthetic demonstration. UCI transactions contain no exposure logs or randomized assignments.

## Hypothesis and unit

Hypothesis: raising the eligible product price by 5% increases contribution profit per assigned customer by at least £0.02 after the return window, without materially harming customer outcomes.

Randomize eligible customers 50/50 with a stable assignment. Analyze all assigned eligible customers, including nonbuyers. Avoid session-level assignments that show one customer both prices. Record assignment time, exposure, orders, cancellations, refunds, costs, and attribution window.

## Metrics

Primary: realized contribution profit per assigned customer. Use actual costs/fees when running a real test.

Secondary/exploratory: conversion and revenue per assigned customer. Guardrails: return rate, complaint rate, and exposure/assignment integrity. Specify acceptable harm thresholds before launch. Exploratory p-values are not corrected for multiplicity and cannot independently justify rollout.

## Sample size and stopping

The app's conversion calculator is an approximate two-sided proportions test. It does not power the primary profit metric. With pilot variance σ² and business MDE δ, an approximate equal-arm profit calculation is `n ≈ 2 × (z_(1−α/2) + z_power)² × σ² / δ²`. Account for heavy tails and clustering, and validate with simulation using a representative pilot.

Fix sample size, duration, eligibility, and analysis before launch. Cover weekly cycles and allow the prespecified return window to mature. Do not repeatedly inspect unadjusted p-values and stop when they become significant. Check sample ratio mismatch and instrumentation before interpreting outcomes.

## Analysis and decision

The demo uses a Welch two-sample interval/test for customer profit and revenue. Conversion uses a two-proportion z-test and a large-sample interval. For a real heavy-tailed profit metric, prespecify a bootstrap or robust sensitivity analysis rather than picking the method after seeing results.

The demo's profit threshold is £0.02/customer. A lower 95% interval above this threshold clears the simulated primary-metric rule. Guardrails and assignment quality still require evaluation before any real rollout. An interval spanning zero or the business threshold is inconclusive, even if a secondary metric looks attractive.

## Synthetic generation

Seed 42; 10,000 customers per arm. Control: conversion 5%, price £20. Treatment: conversion 5.5%, price £21. Basket quantity: uniform integer 1–3; returns: 6%; unit cost: £11; fee: 15% of charged revenue; advertising: £0.20/assigned customer. Inventory cost is recovered on returns, while fees remain charged. These are invented simulation settings, not observations or a claim about causal price response.
