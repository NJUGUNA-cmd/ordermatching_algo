# ordermatching_algo
order matching algorithim in fast api and REACT
# Prediction Market Exchange - Order Matching System

## Overview
A full-stack implementation of an order matching engine for a prediction market platform where YES and NO shares always sum to 100 cents.

## Architecture

### Backend (FastAPI)
- **Order Normalization**: All SELL orders are converted to BUY orders on the opposite side
  - `SELL YES at P` → `BUY NO at (100-P)`
  - `SELL NO at P` → `BUY YES at (100-P)`
- **Data Structures**: Priority queues (heapq) for efficient O(log n) order insertion and O(1) best-price retrieval
- **Matching Algorithm**: Price-time priority (best price first, then FIFO for same price)
- **Concurrency**: Thread-safe operations using Lock()

### Frontend (React)
- Real-time order book visualization
- Order submission form with validation
- Trade history display
- Auto-refresh every 2 seconds

## Key Features Implemented

✅ **Order Types**
- Limit orders (BUY/SELL at specific prices)
- Market orders (BUY at 100¢ or SELL at 0¢)

✅ **Order Matching**
- Price-time priority
- Partial fills
- Self-matching prevention
- YES + NO = 100¢ invariant maintained

✅ **Edge Cases Handled**
- Minimum order size (1 share)
- Account ID validation
- Self-trade prevention
- Concurrent order processing

## Installation & Running

### Backend
```bash
cd backend
pip install fastapi uvicorn pydantic
python main.py
```
Server runs on `http://localhost:8000`

### Frontend
```bash
cd frontend
npm install
npm start
```
App runs on `http://localhost:3000`

## API Endpoints

- `POST /orders` - Place a new order
- `GET /orderbook` - Get current order book state
- `GET /trades` - Get recent trades
- `POST /reset` - Reset order book (for testing)

## Testing Examples

1. **Basic Match**:
   - User1: BUY YES at 60¢, quantity 10
   - User2: SELL YES at 60¢, quantity 10
   - Result: Orders match, trade executes at 60¢

2. **Partial Fill**:
   - User1: BUY YES at 50¢, quantity 20
   - User2: SELL YES at 50¢, quantity 5
   - Result: 5 shares trade, 15 remain in order book

3. **Market Order**:
   - User1: BUY YES at 100¢ (market order)
   - Matches against any resting SELL YES order

4. **Self-Match Prevention**:
   - User1: BUY YES at 60¢
   - User1: SELL YES at 60¢
   - Result: Orders don't match (same account)

## Design Decisions

1. **Normalization Approach**: Simplifies matching logic by converting all orders to canonical BUY form
2. **Heapq for Priority Queue**: Efficient O(log n) operations for order book management
3. **In-Memory Storage**: Fast access, suitable for single-market demo
4. **Thread Lock**: Ensures atomic order processing and prevents race conditions
5. **Original Price Tracking**: Maintains user-facing prices while using normalized prices internally

## Time Complexity

- Order Placement: O(log n) for insertion
- Order Matching: O(k log n) where k = number of matches
- Order Book Retrieval: O(n log n) for top 10 orders

## Future Enhancements

- Multiple markets support
- Order cancellation
- Persistent storage (database)
- WebSocket for real-time updates
- Advanced order types (stop-loss, iceberg)
- Market maker functionality
