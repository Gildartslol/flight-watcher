from __future__ import annotations

from flight_watcher.domain.models import FlightOption, Watcher
from flight_watcher.domain.scoring import pick_best_value, pick_cheapest


def build_watcher_summary(
    watcher: Watcher,
    options: list[FlightOption],
    *,
    previous_best_price: float | None = None,
    threshold_hit: bool = False,
    max_chars: int = 1400,
) -> str:
    if not options:
        return f"[{watcher.name}] No options found this run."

    cheapest = pick_cheapest(options)
    best_value = pick_best_value(options)

    lines = [f"✈️ {watcher.name} ({watcher.origin}→{watcher.destination})"]
    lines.append(f"Top options: {len(options)}")

    for idx, option in enumerate(sorted(options, key=lambda x: x.total_price)[:3], start=1):
        tag_str = f" [{' '.join(option.tags)}]" if option.tags else ""
        lines.append(
            f"{idx}) {option.total_price:.0f} {option.currency} | {option.departure_date}"
            f" | {option.total_duration_min}m | {option.stops} stop(s){tag_str}"
        )

    if cheapest:
        lines.append(f"Cheapest: {cheapest.total_price:.0f} {cheapest.currency} ({cheapest.departure_date})")
    if best_value and cheapest and best_value.fingerprint != cheapest.fingerprint:
        lines.append(f"Best value: {best_value.total_price:.0f} {best_value.currency} ({best_value.departure_date})")

    if previous_best_price is not None and cheapest:
        delta = cheapest.total_price - previous_best_price
        pct = ((previous_best_price - cheapest.total_price) / previous_best_price * 100) if previous_best_price else 0
        if delta < 0:
            lines.append(f"Change: ↓ {abs(delta):.0f} ({pct:.1f}%) vs last best")
        elif delta > 0:
            lines.append(f"Change: ↑ {delta:.0f} vs last best")
        else:
            lines.append("Change: unchanged vs last best")

    if threshold_hit:
        lines.append("Trigger: target threshold hit.")

    if cheapest and watcher.max_price is not None and cheapest.total_price <= watcher.max_price:
        lines.append("Recommendation: viable now, worth shortlisting.")
    elif cheapest:
        lines.append("Recommendation: monitor for drops before acting.")

    message = "\n".join(lines)
    if len(message) > max_chars:
        return message[: max_chars - 1] + "…"
    return message
