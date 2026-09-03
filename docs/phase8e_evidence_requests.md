# Phase 8E: Evidence Request Planner

## 1. Overview & Objective

Phase 8E generates structured, targeted sensory evidence requests when an inspection has incomplete coverage, unobserved diagnostic factors (such as wall thickness or defect depth), or marginal detection confidence.

## 2. Request Types & Triggers

- `COMPONENT_CLOSEUP`: Triggered when dimensional depth, wall loss, or thickness cannot be determined from standard optical perspective.
- `HIGHER_RESOLUTION_IMAGE`: Triggered when primary visual detections have confidence $< 0.70$ or suffer from motion blur.
- `ALTERNATE_VIEW`: Triggered when orientation or angle is obscured.
- `ADDITIONAL_IMAGE`: Triggered for general coverage gaps.
- `HISTORICAL_COMPARISON`: Triggered when temporal baseline imagery is required.

## 3. Human Approval Gate

- **Truthfulness Guarantee:** The planner never claims requested evidence already exists.
- **Strict Human Authorization:** Every evidence request requires human engineering approval before being dispatched to inspection teams (`human_approval_required = True`).
