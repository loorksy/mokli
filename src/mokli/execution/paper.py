"""Paper broker. Fills, slippage, pending orders, and stops are simulated. Nothing is sent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class PaperOrder:
    id: str
    side: str
    order_type: str
    lots: float
    price: float | None
    stop_loss: float | None
    take_profit: float | None
    status: str
    filled_price: float | None = None
    comment: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PaperPosition:
    id: str
    side: str
    lots: float
    remaining: float
    entry: float
    stop_loss: float | None
    targets: list[float]
    realized: float = 0.0
    comment: str = ""
    managed: bool = True
    manual: bool = False
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "open"
    partials: list[dict[str, float]] = field(default_factory=list)


@dataclass(frozen=True)
class Fill:
    id: str
    order_id: str
    side: str
    lots: float
    price: float
    time: datetime


class PaperBroker:
    def __init__(
        self,
        *,
        balance: float = 10_000.0,
        point: float = 0.01,
        slippage_points: float = 2.0,
        contract_ounces: float = 100.0,
    ) -> None:
        self.balance = balance
        self.point = point
        self.slippage_points = slippage_points
        self.contract_ounces = contract_ounces
        self.bid = 0.0
        self.ask = 0.0
        self.quote_time: datetime | None = None
        self.orders: dict[str, PaperOrder] = {}
        self.positions: dict[str, PaperPosition] = {}
        self.fills: list[Fill] = []
        self.killed = False
        self.source = "simulator"

    def quote(self, bid: float, ask: float, when: datetime) -> None:
        if ask < bid:
            raise ValueError("ask below bid")
        self.bid = bid
        self.ask = ask
        self.quote_time = when
        self._trigger_pending()
        self._manage_positions()

    def market(
        self,
        side: str,
        lots: float,
        *,
        stop_loss: float | None,
        take_profit: float | None,
        comment: str,
        when: datetime | None = None,
        manual: bool = False,
    ) -> PaperPosition:
        if self.killed:
            raise RuntimeError("kill switch is on")
        if self.bid <= 0 or self.ask <= 0:
            raise RuntimeError("no quote")
        slip = self.slippage_points * self.point
        price = self.ask + slip if side == "buy" else self.bid - slip
        return self._open(
            side,
            lots,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
            when=when,
            manual=manual,
        )

    def _open(
        self,
        side: str,
        lots: float,
        *,
        price: float,
        stop_loss: float | None,
        take_profit: float | None,
        comment: str,
        when: datetime | None = None,
        manual: bool = False,
        order_id: str | None = None,
    ) -> PaperPosition:
        if order_id is None:
            order = PaperOrder(
                id=_id(),
                side=side,
                order_type="market",
                lots=lots,
                price=None,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status="filled",
                filled_price=price,
                comment=comment,
            )
            self.orders[order.id] = order
            order_id = order.id
        stamp = when or self.quote_time or datetime.now(timezone.utc)
        self.fills.append(Fill(_id(), order_id, side, lots, price, stamp))
        targets = _three_targets(side, price, stop_loss, take_profit)
        position = PaperPosition(
            id=_id(),
            side=side,
            lots=lots,
            remaining=lots,
            entry=price,
            stop_loss=stop_loss,
            targets=targets,
            comment=comment,
            manual=manual,
            managed=not manual,
            opened_at=stamp,
        )
        self.positions[position.id] = position
        return position

    def pending(
        self,
        side: str,
        order_type: str,
        lots: float,
        price: float,
        *,
        stop_loss: float | None,
        take_profit: float | None,
        comment: str,
    ) -> PaperOrder:
        if order_type not in {"limit", "stop"}:
            raise ValueError("pending type must be limit or stop")
        order = PaperOrder(
            id=_id(),
            side=side,
            order_type=order_type,
            lots=lots,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="pending",
            comment=comment,
        )
        self.orders[order.id] = order
        return order

    def cancel_pending(self) -> int:
        count = 0
        for order in self.orders.values():
            if order.status == "pending":
                order.status = "cancelled"
                count += 1
        return count

    def close_position(self, position_id: str, lots: float | None = None) -> float:
        position = self.positions[position_id]
        qty = position.remaining if lots is None else min(lots, position.remaining)
        exit_price = self.bid if position.side == "buy" else self.ask
        pnl = self._pnl(position.side, position.entry, exit_price, qty)
        position.realized += pnl
        self.balance += pnl
        position.remaining = round(position.remaining - qty, 4)
        position.partials.append({"lots": qty, "price": exit_price, "pnl": pnl})
        if position.remaining <= 0:
            position.status = "closed"
        return pnl

    def close_all(self) -> None:
        for position in list(self.positions.values()):
            if position.status == "open" and position.remaining > 0:
                self.close_position(position.id)
        self.cancel_pending()

    def kill(self) -> None:
        self.killed = True
        self.close_all()

    def modify_stop(self, position_id: str, new_stop: float) -> None:
        position = self.positions[position_id]
        if position.side == "buy" and position.stop_loss is not None and new_stop < position.stop_loss:
            raise ValueError("stop widened")
        if position.side == "sell" and position.stop_loss is not None and new_stop > position.stop_loss:
            raise ValueError("stop widened")
        position.stop_loss = new_stop

    def adopt(self, position_id: str) -> None:
        self.positions[position_id].managed = True

    def equity(self) -> float:
        floating = 0.0
        for position in self.positions.values():
            if position.status != "open":
                continue
            mark = self.bid if position.side == "buy" else self.ask
            floating += self._pnl(position.side, position.entry, mark, position.remaining)
        return self.balance + floating

    def snapshot(self) -> dict[str, object]:
        return {
            "source": self.source,
            "balance": round(self.balance, 2),
            "equity": round(self.equity(), 2),
            "bid": self.bid,
            "ask": self.ask,
            "killed": self.killed,
            "positions": [
                {
                    "id": item.id,
                    "side": item.side,
                    "lots": item.lots,
                    "remaining": item.remaining,
                    "entry": item.entry,
                    "stop_loss": item.stop_loss,
                    "targets": item.targets,
                    "status": item.status,
                    "realized": round(item.realized, 2),
                    "manual": item.manual,
                    "managed": item.managed,
                    "comment": item.comment,
                }
                for item in self.positions.values()
            ],
            "orders": [
                {
                    "id": item.id,
                    "side": item.side,
                    "type": item.order_type,
                    "status": item.status,
                    "price": item.price,
                    "lots": item.lots,
                }
                for item in self.orders.values()
            ],
        }

    def _pnl(self, side: str, entry: float, exit_price: float, lots: float) -> float:
        sign = 1 if side == "buy" else -1
        return sign * (exit_price - entry) * self.contract_ounces * lots

    def _trigger_pending(self) -> None:
        for order in list(self.orders.values()):
            if order.status != "pending" or order.price is None:
                continue
            touched = False
            if order.order_type == "limit" and order.side == "buy":
                touched = self.ask <= order.price
            elif order.order_type == "limit" and order.side == "sell":
                touched = self.bid >= order.price
            elif order.order_type == "stop" and order.side == "buy":
                touched = self.ask >= order.price
            elif order.order_type == "stop" and order.side == "sell":
                touched = self.bid <= order.price
            if not touched or self.killed:
                continue
            self._open(
                order.side,
                order.lots,
                price=order.price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                comment=order.comment,
                order_id=order.id,
            )
            order.status = "filled"
            order.filled_price = order.price

    def _manage_positions(self) -> None:
        for position in list(self.positions.values()):
            if position.status != "open" or not position.managed:
                continue
            if position.side == "buy":
                if position.stop_loss is not None and self.bid <= position.stop_loss:
                    self.close_position(position.id)
                    continue
                self._scale(position, self.bid)
            else:
                if position.stop_loss is not None and self.ask >= position.stop_loss:
                    self.close_position(position.id)
                    continue
                self._scale(position, self.ask)

    def _scale(self, position: PaperPosition, price: float) -> None:
        fractions = (0.40, 0.30, 0.30)
        for index, target in enumerate(position.targets):
            if index < len(position.partials):
                continue
            hit = price >= target if position.side == "buy" else price <= target
            if not hit:
                return
            qty = round(position.lots * fractions[index], 4)
            if qty <= 0 or position.remaining <= 0:
                return
            self.close_position(position.id, min(qty, position.remaining))


def _three_targets(side: str, entry: float, stop: float | None, final: float | None) -> list[float]:
    if stop is None or final is None:
        return []
    span = abs(final - entry)
    if side == "buy":
        return [round(entry + span * 0.4, 2), round(entry + span * 0.7, 2), round(final, 2)]
    return [round(entry - span * 0.4, 2), round(entry - span * 0.7, 2), round(final, 2)]
