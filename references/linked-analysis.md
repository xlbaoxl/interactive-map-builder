# Linked views by stable ID

Use linked views only to connect existing, user-defined variables. The shared event bus uses the normalized feature ID; chart elements expose the same value through `data-feature-id`.

The supported v0.1 recipe is a scatter view:

```json
{
  "linked_view": {
    "layer": "places",
    "x_field": "x_value",
    "y_field": "y_value",
    "title": "Linked comparison"
  }
}
```

Validate ID uniqueness and finite x/y values. Keep missing values out of the chart and report their count. Synchronize hover and click selection in both directions.

Do not create quadrants, thresholds, causal labels, statistical significance claims, or domain metrics unless the user supplies and defines them.
