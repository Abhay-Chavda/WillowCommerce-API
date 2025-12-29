# WillowCommerce Support Policies (Test Knowledge)

## Order Status Definitions
- PLACED: Order received, payment verified.
- PROCESSING: Preparing/packing in warehouse.
- SHIPPED: Handed to courier, tracking available.
- OUT_FOR_DELIVERY: Courier is delivering today.
- DELIVERED: Delivered successfully.
- CANCELLED: Cancelled before delivery.
- RETURN_REQUESTED: Return/refund initiated and pending pickup.
- REFUNDED: Refund completed.

## Cancellation Policy
- Cancellation is allowed only if order status is PLACED or PROCESSING.
- If order status is SHIPPED / OUT_FOR_DELIVERY / DELIVERED, cancellation is not allowed.
- If user wants cancellation after shipping, suggest return/refund options if eligible.

## 7-Day Refund Policy (Delivered Orders)
Refund is allowed if:
1) Product is within 7 days from delivery AND condition is OK (no damage required), OR
2) Product condition is DAMAGED or WRONG_ITEM (eligible even if delivery is older than 7 days).

Refund is NOT allowed if:
- Product condition is OK and more than 7 days have passed since delivery.

Refund methods:
- Refund will be processed to original payment method.
- Typical refund time: 3–7 business days after approval (test policy).

## Replacement Policy
Replacement is allowed if:
- Product condition is DAMAGED or WRONG_ITEM
- Replacement can be initiated for delivered orders.

If product is OK and user simply doesn't like it:
- Suggest refund only if within 7 days of delivery.

## What Support Agent Must Ask (Slot-Filling)
If user asks for order status/refund/cancel/replacement but does not share order ID:
- Ask: "Please share your Order ID or product name."

If user shares product name and multiple matching orders exist:
- Ask them to choose an order ID from the top matches.

For refund/replacement:
- Ask product condition only if not available in system:
  - OK / DAMAGED / WRONG_ITEM
