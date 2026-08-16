"""Replayable receipts and export payloads for compact signal handoffs."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from .handoff import SignalHandoff
from .handoff_engine import CompanyForecast


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def build_handoff_receipt(handoff: SignalHandoff, result: CompanyForecast) -> dict[str, Any]:
    return {
        "schemaVersion": "forecast_receipt.v1",
        "companyId": result.company_id,
        "targetPeriod": result.target_period,
        "informationCutoff": result.information_cutoff,
        "sources": [
            {
                "id": source.source_id,
                "url": source.url,
                "publishedAt": source.published_at.isoformat(),
                "publisher": source.publisher,
                "title": source.title,
                "documentType": source.document_type,
                "frozenPath": str(source.frozen_path),
                "sha256": source.sha256,
            }
            for source in handoff.sources.values()
        ],
        "forecasts": [
            {
                "metricId": forecast.metric_id,
                "metric": forecast.label,
                "unit": forecast.unit,
                "low": _decimal(forecast.low),
                "high": _decimal(forecast.high),
                "value": _decimal(forecast.value),
                "method": forecast.method,
                "formula": forecast.formula,
                "sourceIds": list(forecast.source_ids),
                "qualitativeSignals": [
                    signal for signal in result.qualitative_signals
                    if forecast.metric_id in signal.get("targetMetricIds", [forecast.metric_id])
                ],
            }
            for forecast in result.forecasts
        ],
        "unresolved": list(result.unresolved),
    }


def build_company_forecast_payload(result: CompanyForecast) -> dict[str, Any]:
    """Workbook-facing payload; Decimal values stay exact in the receipt above."""
    return {
        "schema_version": "company_forecast.v1",
        "company_id": result.company_id,
        "target_period": result.target_period,
        "information_cutoff": result.information_cutoff,
        "forecasts": [
            {
                "metric": forecast.label,
                "metric_id": forecast.metric_id,
                "units": forecast.unit,
                "value": float(forecast.value),
                "value_decimal": _decimal(forecast.value),
                "low_decimal": _decimal(forecast.low),
                "high_decimal": _decimal(forecast.high),
                "method": forecast.method,
            }
            for forecast in result.forecasts
        ],
    }


def write_handoff_receipt(handoff: SignalHandoff, result: CompanyForecast, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(build_handoff_receipt(handoff, result), indent=2, sort_keys=True) + "\n")
    return destination
