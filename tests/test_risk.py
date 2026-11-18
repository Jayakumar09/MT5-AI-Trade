"""Unit tests for the AEGIS risk rules and lot sizing (backend/core/risk.py)."""

from __future__ import annotations

import pytest

from backend.core.models import AccountInfo, Signal
from backend.core.risk import (
    aegis_guard,
    confidence_ok,
    daily_drawdown_ok,
    rr_ok,
    spread_ok,
    risk_per_trade_ok,
    max_open_trades_ok,
)
from backend.core.mt5_client import normalize_volume, validate_sl_tp, retcode_to_message

RULES = {
    "spread_limit_xau": 35,
    "spread_limit_btc": 500,
    "risk_per_trade_default": 0.01,
    "risk_per_trade_max": 0.02,
    "daily_drawdown_kill": 0.04,
    "max_open_trades": 5,
    "min_rr": 2.0,
    "min_confidence": 7.0,
    "session_filter": {},
}


def _signal(direction="LONG", conf=8.0, rr=2.5, entry=2380.0, sl=2370.0, tp1=2400.0):
    return Signal(
        instrument="XAUUSD",
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=tp1 + 10,
        risk_reward_ratio=rr,
        confidence=conf,
    )


def _account(balance=10000.0, daily_dd=0.0):
    return AccountInfo(balance=balance, equity=balance, margin_free=balance * 0.9, daily_drawdown=daily_dd)


def test_spread_ok():
    assert spread_ok("XAUUSD", 30, RULES) is True
    assert spread_ok("XAUUSD", 40, RULES) is False
    assert spread_ok("BTCUSD", 400, RULES) is True


def test_rr_ok():
    assert rr_ok({"risk_reward_ratio": 2.0}) is True
    assert rr_ok({"risk_reward_ratio": 1.9}) is False
    assert rr_ok({"risk_reward_ratio": 3.1}) is True


def test_confidence_ok():
    assert confidence_ok(7.0, RULES) is True
    assert confidence_ok(6.4, RULES) is False


def test_daily_drawdown_kill():
    assert daily_drawdown_ok(_account(daily_dd=100), RULES) is True    # 1% dd
    assert daily_drawdown_ok(_account(daily_dd=500), RULES) is False   # 5% dd, over kill level


def test_max_open_trades():
    assert max_open_trades_ok(4, RULES) is True
    assert max_open_trades_ok(6, RULES) is False


def test_risk_per_trade():
    assert risk_per_trade_ok("LONG", 8.0, RULES, _account()) is True


def test_aegis_guard_approves_valid_signal():
    sig = _signal(conf=8.0, rr=2.5)
    acct = _account()
    res = aegis_guard("XAUUSD", sig, acct,
                      {"risk_reward_ratio": 2.5, "entry_price": 2380.0, "stop_loss": 2370.0},
                      RULES, [])
    assert res.vetoed is False
    assert res.approved is True
    assert res.lot_size and res.lot_size > 0


def test_aegis_guard_vetoes_low_confidence():
    sig = _signal(conf=5.0, rr=2.5)
    res = aegis_guard("XAUUSD", sig, _account(),
                      {"risk_reward_ratio": 2.5, "entry_price": 2380.0, "stop_loss": 2370.0},
                      RULES, [])
    assert res.vetoed is True
    assert any("confidence" in r.lower() for r in res.veto_reasons)


def test_aegis_guard_vetoes_low_rr():
    sig = _signal(conf=8.0, rr=1.2)
    res = aegis_guard("XAUUSD", sig, _account(),
                      {"risk_reward_ratio": 1.2, "entry_price": 2380.0, "stop_loss": 2370.0},
                      RULES, [])
    assert res.vetoed is True
    assert any("risk-reward" in r.lower() for r in res.veto_reasons)


def test_aegis_guard_vetoes_daily_drawdown():
    sig = _signal()
    res = aegis_guard("XAUUSD", sig, _account(daily_dd=500),
                      {"risk_reward_ratio": 2.5, "entry_price": 2380.0, "stop_loss": 2370.0},
                      RULES, [])
    assert res.vetoed is True
    assert any("drawdown" in r.lower() for r in res.veto_reasons)


def test_aegis_guard_vetoes_duplicate_signal():
    sig = _signal()
    res = aegis_guard("XAUUSD", sig, _account(),
                      {"risk_reward_ratio": 2.5, "entry_price": 2380.0, "stop_loss": 2370.0},
                      RULES, [sig.id])
    assert res.vetoed is True
    assert any("duplicate" in r.lower() for r in res.veto_reasons)


def test_normalize_volume():
    assert normalize_volume(0.037, 0.01, 0.01, 100.0) == pytest.approx(0.04)
    assert normalize_volume(0.001, 0.01, 0.01, 100.0) == pytest.approx(0.01)
    assert normalize_volume(250.0, 0.01, 0.01, 100.0) == pytest.approx(100.0)
    assert normalize_volume(0.05, 0.01, 0.0, 100.0) == pytest.approx(0.05)  # zero step tolerated


def test_validate_sl_tp():
    ok, reason = validate_sl_tp("XAUUSD", "BUY", 2380.0, 2370.0, 2400.0, 10, 0.01)
    assert ok is True
    ok, reason = validate_sl_tp("XAUUSD", "BUY", 2380.0, 2380.5, 2400.0, 10, 0.01)
    assert ok is False  # SL above entry for BUY
    ok, reason = validate_sl_tp("XAUUSD", "SELL", 2380.0, 2390.0, 2350.0, 10, 0.01)
    assert ok is True


def test_retcode_mapping():
    assert "Requote" in retcode_to_message(10004)
    assert "margin" in retcode_to_message(10019).lower()
    assert "Unknown" in retcode_to_message(99999)