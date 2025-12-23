import React, { useState, useEffect } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";

function App() {
  const [orderBook, setOrderBook] = useState({
    yes_bids: [],
    yes_asks: [],
    no_bids: [],
    no_asks: [],
  });
  const [trades, setTrades] = useState([]);
  const [formData, setFormData] = useState({
    side: "YES",
    type: "BUY",
    price: 50,
    quantity: 10,
    account_id: "user1",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchOrderBook();
    fetchTrades();
    const interval = setInterval(() => {
      fetchOrderBook();
      fetchTrades();
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchOrderBook = async () => {
    try {
      const response = await fetch(`${API_BASE}/orderbook`);
      const data = await response.json();
      setOrderBook(data);
    } catch (err) {
      console.error("Error fetching order book:", err);
    }
  };

  const fetchTrades = async () => {
    try {
      const response = await fetch(`${API_BASE}/trades?limit=10`);
      const data = await response.json();
      setTrades(data);
    } catch (err) {
      console.error("Error fetching trades:", err);
    }
  };

  const submitOrder = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(`${API_BASE}/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          side: formData.side,
          type: formData.type,
          price: parseInt(formData.price),
          quantity: parseInt(formData.quantity),
          account_id: formData.account_id,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to place order");
      }

      const result = await response.json();
      setMessage(result.message);

      // Refresh order book and trades
      await fetchOrderBook();
      await fetchTrades();
    } catch (err) {
      setMessage("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetOrderBook = async () => {
    try {
      await fetch(`${API_BASE}/reset`, { method: "POST" });
      setMessage("Order book reset successfully");
      await fetchOrderBook();
      await fetchTrades();
    } catch (err) {
      setMessage("Error resetting: " + err.message);
    }
  };

  const OrderBookPanel = ({ title, orders, side }) => (
    <div className="order-book-panel">
      <h3>{title}</h3>
      <div className="orders-list">
        {orders.length === 0 ? (
          <p className="empty">No orders</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Price</th>
                <th>Quantity</th>
                <th>Account</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.order_id} className={side}>
                  <td className="price">{order.price}¢</td>
                  <td>{order.quantity}</td>
                  <td className="account">{order.account_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );

  return (
    <div className="App">
      <header>
        <h1>Prediction Market Exchange</h1>
        <p>Order Matching System - YES/NO shares always sum to 100¢</p>
      </header>

      <div className="container">
        <div className="left-panel">
          <div className="order-form">
            <h2>Place Order</h2>
            <form onSubmit={submitOrder}>
              <div className="form-group">
                <label>Side</label>
                <select
                  value={formData.side}
                  onChange={(e) =>
                    setFormData({ ...formData, side: e.target.value })
                  }
                >
                  <option value="YES">YES</option>
                  <option value="NO">NO</option>
                </select>
              </div>

              <div className="form-group">
                <label>Type</label>
                <select
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({ ...formData, type: e.target.value })
                  }
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>

              <div className="form-group">
                <label>
                  Price (0-100)
                  {formData.type === "SELL" &&
                    formData.price === "0" &&
                    " (Market Order)"}
                  {formData.type === "BUY" &&
                    formData.price === "100" &&
                    " (Market Order)"}
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.price}
                  onChange={(e) =>
                    setFormData({ ...formData, price: e.target.value })
                  }
                />
              </div>

              <div className="form-group">
                <label>Quantity (min 1)</label>
                <input
                  type="number"
                  min="1"
                  value={formData.quantity}
                  onChange={(e) =>
                    setFormData({ ...formData, quantity: e.target.value })
                  }
                />
              </div>

              <div className="form-group">
                <label>Account ID</label>
                <input
                  type="text"
                  value={formData.account_id}
                  onChange={(e) =>
                    setFormData({ ...formData, account_id: e.target.value })
                  }
                />
              </div>

              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? "Processing..." : "Submit Order"}
              </button>

              <button
                type="button"
                onClick={resetOrderBook}
                className="btn-secondary"
              >
                Reset Order Book
              </button>
            </form>

            {message && (
              <div
                className={`message ${message.includes("Error") ? "error" : "success"}`}
              >
                {message}
              </div>
            )}
          </div>
        </div>

        <div className="right-panel">
          <div className="order-book-section">
            <h2>Order Book - YES Shares</h2>
            <div className="order-book-grid">
              <OrderBookPanel
                title="Bids (Buy YES)"
                orders={orderBook.yes_bids}
                side="bid"
              />
              <OrderBookPanel
                title="Asks (Sell YES)"
                orders={orderBook.yes_asks}
                side="ask"
              />
            </div>
          </div>

          <div className="order-book-section">
            <h2>Order Book - NO Shares</h2>
            <div className="order-book-grid">
              <OrderBookPanel
                title="Bids (Buy NO)"
                orders={orderBook.no_bids}
                side="bid"
              />
              <OrderBookPanel
                title="Asks (Sell NO)"
                orders={orderBook.no_asks}
                side="ask"
              />
            </div>
          </div>

          <div className="trades-section">
            <h2>Recent Trades</h2>
            <div className="trades-list">
              {trades.length === 0 ? (
                <p className="empty">No trades yet</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Maker</th>
                      <th>Taker</th>
                      <th>Price</th>
                      <th>Quantity</th>
                      <th>Side</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade) => (
                      <tr key={trade.trade_id}>
                        <td>#{trade.maker_order_id}</td>
                        <td>#{trade.taker_order_id}</td>
                        <td>{trade.price}¢</td>
                        <td>{trade.quantity}</td>
                        <td className={`side-${trade.side.toLowerCase()}`}>
                          {trade.side}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
