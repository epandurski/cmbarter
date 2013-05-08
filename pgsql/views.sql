-- The author disclaims copyright to this source code.  In place of
-- a legal notice, here is a poem:
--
--   “Epiphany”
-- 
--   Deep, unconscious,
--   self-fulfilling wish:
--   the true knowledge
--   is certainly this.
-- 
--   Big, certain, and
--   nutritious dish:
--   a plain slavery, 
--   ironically that is.
-- 
----------------------------------------------------------------------
-- This file contains code which adds some important views to the
-- database schema for the CMB web application.
--


-- Very fast if selected by (recipient_id, issuer_id)
CREATE OR REPLACE VIEW deposit AS 
  SELECT
    a.recipient_id, a.issuer_id, a.promise_id,
    a.amount,
    p.title, p.unit, p.summary, p.epsilon
  FROM mv_asset a, product p
  WHERE
    p.issuer_id=a.issuer_id AND
    p.promise_id=a.promise_id AND
    p.epsilon < a.amount;


--Very fast if selected by (issuer_id, promise_id)
CREATE OR REPLACE VIEW product_deposit AS 
  SELECT
    a.recipient_id, a.issuer_id, a.promise_id,
    a.amount,
    p.title, p.unit, p.summary, p.epsilon
  FROM asset a, product p
  WHERE
    p.issuer_id=a.issuer_id AND
    p.promise_id=a.promise_id AND
    p.epsilon < a.amount;


CREATE OR REPLACE VIEW extended_bid AS 
  SELECT
    b.recipient_id, b.issuer_id, b.promise_id, 
    GREATEST(b.amount - b.p_unconfirmed_deal_amount, (- COALESCE(a.amount, 0.0))) AS buy_amount,
    COALESCE(a.amount, 0.0) - b.p_unconfirmed_transaction_amount - b.p_unconfirmed_deal_amount AS have_amount,
    COALESCE(a.amount, 0.0) - b.p_unconfirmed_transaction_amount - b.p_unconfirmed_deal_amount + b.amount  AS need_amount,
    p.title, p.unit, p.summary, p.epsilon,
    o.price AS issuer_price,
    b.price AS recipient_price
  FROM
    bid b
      LEFT OUTER JOIN bid_product p ON
        p.recipient_id=b.recipient_id AND
        p.issuer_id=b.issuer_id AND
        p.promise_id=b.promise_id
      LEFT OUTER JOIN mv_asset a ON
        a.recipient_id=b.recipient_id AND
        a.issuer_id=b.issuer_id AND
        a.promise_id=b.promise_id
      LEFT OUTER JOIN offer o ON
        o.issuer_id=b.issuer_id AND
        o.promise_id=b.promise_id;


CREATE OR REPLACE VIEW shopping_item AS 
  SELECT b.*, t.name, t.comment
  FROM extended_bid b, trust t
  WHERE
    t.recipient_id=b.recipient_id AND
    t.issuer_id=b.issuer_id;


CREATE OR REPLACE VIEW candidate_commitment AS 
  SELECT
    b.recipient_id, b.issuer_id, b.promise_id,
    CAST(b.issuer_price * b.buy_amount AS value) AS value
  FROM extended_bid b
  WHERE ABS(b.buy_amount) > b.epsilon AND (
    (b.buy_amount > 0.0 AND b.recipient_price >= b.issuer_price) OR 
    (b.buy_amount < 0.0 AND b.recipient_price <= b.issuer_price))

  UNION ALL

  SELECT
    o.issuer_id, o.issuer_id, o.promise_id,
    CAST(- o.price * a.amount AS value) AS value
  FROM offer o, asset a
  WHERE
    a.recipient_id=o.issuer_id AND
    a.issuer_id=o.issuer_id AND
    a.promise_id=o.promise_id AND
    a.amount > o.p_epsilon AND
    o.price IS NOT NULL;


CREATE OR REPLACE VIEW delivery_order AS 
  SELECT
    dd.recipient_id, dd.order_id,
    dd.issuer_id, dd.promise_id, dd.amount, dd.carrier, dd.instructions, dd.insertion_ts,
    dd.title, dd.unit, dd.summary, dd.epsilon,
    ds.is_active, ds.last_issuer_review_ts, ds.issuer_message, ds.execution_ts
  FROM delivery_description dd, delivery_status ds
  WHERE
    ds.recipient_id=dd.recipient_id AND ds.order_id=dd.order_id AND
    (ds.is_active=TRUE OR ds.last_issuer_review_ts > CURRENT_TIMESTAMP - INTERVAL '1 day');
