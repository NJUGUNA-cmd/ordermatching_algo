from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from enum import Enum
import heapq
from threading import Lock
from dataclasses import dataclass, field
import time

app = FastAPI(title="Prediction Market Exchange")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Side(str, Enum):
    YES = "YES"
    NO = "NO"

class OrderType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderRequest(BaseModel):
    side: Side
    type: OrderType
    price: int = Field(ge=0, le=100)
    quantity: int = Field(ge=1)
    account_id: str

    @validator('price')
    def validate_price(cls, v, values):
        if 'type' in values:
            if values['type'] == OrderType.SELL and v > 100:
                raise ValueError('SELL price cannot exceed 100')
            if values['type'] == OrderType.BUY and v < 0:
                raise ValueError('BUY price cannot be negative')
        return v

@dataclass(order=True)
class Order:
    priority: tuple = field(compare=True)
    order_id: int = field(compare=False)
    account_id: str = field(compare=False)
    side: str = field(compare=False)
    order_type: str = field(compare=False)
    price: int = field(compare=False)
    original_price: int = field(compare=False)
    quantity: int = field(compare=False)
    timestamp: float = field(compare=False)

class Trade(BaseModel):
    trade_id: int
    maker_order_id: int
    taker_order_id: int
    price: int
    quantity: int
    side: str
    timestamp: float

class OrderBookResponse(BaseModel):
    yes_bids: List[dict]
    yes_asks: List[dict]
    no_bids: List[dict]
    no_asks: List[dict]

class OrderResponse(BaseModel):
    order_id: int
    status: str
    filled_quantity: int
    remaining_quantity: int
    trades: List[Trade]
    message: str

class OrderBook:
    def __init__(self):
        self.yes_bids = []
        self.yes_asks = []
        self.no_bids = []
        self.no_asks = []

        self.next_order_id = 1
        self.next_trade_id = 1
        self.lock = Lock()
        self.all_trades = []
        self.orders_by_id = {}

    def _normalize_order(self, order_req: OrderRequest):
        """
        Normalize orders to canonical form for matching.
        SELL YES at P becomes BUY NO at (100-P)
        SELL NO at P becomes BUY YES at (100-P)
        Returns: (canonical_side, is_buy, canonical_price)
        """
        if order_req.type == OrderType.SELL:
            if order_req.side == Side.YES:
                return ("NO", True, 100 - order_req.price)
            else:
                return ("YES", True, 100 - order_req.price)
        else:
            return (order_req.side.value, True, order_req.price)

    def _add_to_book(self, book: list, order: Order, is_bid: bool):
        """Add order to the appropriate book with correct priority"""
        if is_bid:
            priority = (-order.price, order.timestamp, order.order_id)
        else:
            priority = (order.price, order.timestamp, order.order_id)
        
        order.priority = priority
        heapq.heappush(book, order)

    def _get_matching_book(self, canonical_side: str):
        # Incoming BUY matches against resting BUYs
        if canonical_side == "YES":
            return self.yes_bids
        else:
            return self.no_bids

    def _get_resting_book(self, canonical_side: str):
        # Rest unmatched BUY orders into bids
        if canonical_side == "YES":
            return self.yes_bids
        else:
            return self.no_bids

    def _can_match(self, taker_price: int, maker_price: int, taker_account: str, maker_account: str) -> bool:
        """Check if taker can match with maker"""
        if taker_account == maker_account:
            return False
        return taker_price >= maker_price

    def _execute_trade(self, taker: Order, maker: Order, quantity: int) -> Trade:
        """Execute a trade between two orders"""
        trade_price = maker.original_price

        trade = Trade(
            trade_id=self.next_trade_id,
            maker_order_id=maker.order_id,
            taker_order_id=taker.order_id,
            price=trade_price,
            quantity=quantity,
            side=taker.side,
            timestamp=time.time()
        )

        self.next_trade_id += 1
        self.all_trades.append(trade)
        return trade

    def place_order(self, order_req: OrderRequest) -> OrderResponse:
        """Place and match an order"""
        with self.lock:
            order_id = self.next_order_id
            self.next_order_id += 1

            is_market = (order_req.type == OrderType.BUY and order_req.price == 100) or \
                       (order_req.type == OrderType.SELL and order_req.price == 0)

            canonical_side, is_buy, canonical_price = self._normalize_order(order_req)

            order = Order(
                priority=(0, 0, 0),
                order_id=order_id,
                account_id=order_req.account_id,
                side=order_req.side.value,
                order_type=order_req.type.value,
                price=canonical_price,
                original_price=order_req.price,
                quantity=order_req.quantity,
                timestamp=time.time()
            )

            trades = []
            remaining_qty = order.quantity
            matching_book = self._get_matching_book(canonical_side)
            skipped_orders = []

            while remaining_qty > 0 and matching_book:
                if not matching_book:
                    break

                best_maker = matching_book[0]

                if order.account_id == best_maker.account_id:
                    heapq.heappop(matching_book)
                    skipped_orders.append(best_maker)
                    continue

                can_match = is_market or self._can_match(
                    canonical_price,
                    best_maker.price,
                    order.account_id,
                    best_maker.account_id
                )

                if can_match:
                    heapq.heappop(matching_book)

                    trade_qty = min(remaining_qty, best_maker.quantity)
                    trade = self._execute_trade(order, best_maker, trade_qty)
                    trades.append(trade)

                    remaining_qty -= trade_qty
                    best_maker.quantity -= trade_qty

                    if best_maker.quantity > 0:
                        heapq.heappush(matching_book, best_maker)
                else:
                    break

            for skipped in skipped_orders:
                heapq.heappush(matching_book, skipped)

            if remaining_qty > 0:
                order.quantity = remaining_qty
                resting_book = self._get_resting_book(canonical_side)
                self._add_to_book(resting_book, order, True)

                self.orders_by_id[order_id] = order
                status = "PARTIALLY_FILLED" if trades else "OPEN"
            else:
                status = "FILLED"

            filled_qty = order_req.quantity - remaining_qty

            return OrderResponse(
                order_id=order_id,
                status=status,
                filled_quantity=filled_qty,
                remaining_quantity=remaining_qty,
                trades=trades,
                message=f"Order {order_id}: {status}. Filled {filled_qty}/{order_req.quantity} shares in {len(trades)} trade(s)."
            )

    def get_order_book(self) -> OrderBookResponse:
        """Get current order book state with proper bid/ask separation"""
        with self.lock:
            yes_bids_display = []
            yes_asks_display = []
            no_bids_display = []
            no_asks_display = []

            # Process YES orders
            for order in heapq.nsmallest(10, self.yes_bids):
                order_dict = {
                    "order_id": order.order_id,
                    "price": order.original_price,
                    "quantity": order.quantity,
                    "account_id": order.account_id
                }
                
                # Determine if this is a bid or ask based on original order type
                if order.order_type == "BUY" and order.side == "YES":
                    yes_bids_display.append(order_dict)
                elif order.order_type == "SELL" and order.side == "NO":
                    # SELL NO at X becomes BUY YES at (100-X), show as YES bid
                    yes_bids_display.append(order_dict)

            # Process NO orders  
            for order in heapq.nsmallest(10, self.no_bids):
                order_dict = {
                    "order_id": order.order_id,
                    "price": order.original_price,
                    "quantity": order.quantity,
                    "account_id": order.account_id
                }
                
                # Determine if this is a bid or ask based on original order type
                if order.order_type == "BUY" and order.side == "NO":
                    no_bids_display.append(order_dict)
                elif order.order_type == "SELL" and order.side == "YES":
                    # SELL YES at X becomes BUY NO at (100-X), show as NO bid
                    no_bids_display.append(order_dict)

            # For asks, we need to derive them from the opposite side
            # YES asks = offers to sell YES = same as buying NO
            # So we look at NO bids with original SELL YES orders
            for order in heapq.nsmallest(10, self.no_bids):
                if order.order_type == "SELL" and order.side == "YES":
                    yes_asks_display.append({
                        "order_id": order.order_id,
                        "price": order.original_price,
                        "quantity": order.quantity,
                        "account_id": order.account_id
                    })

            # NO asks = offers to sell NO = same as buying YES  
            # So we look at YES bids with original SELL NO orders
            for order in heapq.nsmallest(10, self.yes_bids):
                if order.order_type == "SELL" and order.side == "NO":
                    no_asks_display.append({
                        "order_id": order.order_id,
                        "price": order.original_price,
                        "quantity": order.quantity,
                        "account_id": order.account_id
                    })

            return OrderBookResponse(
                yes_bids=yes_bids_display,
                yes_asks=yes_asks_display,
                no_bids=no_bids_display,
                no_asks=no_asks_display
            )

    def get_recent_trades(self, limit: int = 20) -> List[Trade]:
        """Get recent trades"""
        with self.lock:
            return self.all_trades[-limit:][::-1]

order_book = OrderBook()

@app.get("/")
def read_root():
    return {"message": "Prediction Market Exchange API", "status": "running"}

@app.post("/orders", response_model=OrderResponse)
def place_order(order: OrderRequest):
    """Place a new order"""
    try:
        return order_book.place_order(order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orderbook", response_model=OrderBookResponse)
def get_order_book():
    """Get current order book"""
    return order_book.get_order_book()

@app.get("/trades", response_model=List[Trade])
def get_trades(limit: int = 20):
    """Get recent trades"""
    return order_book.get_recent_trades(limit)

@app.post("/reset")
def reset_order_book():
    """Reset the order book (for testing)"""
    global order_book
    order_book = OrderBook()
    return {"message": "Order book reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)