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
-- This file contains code defining database triggers for the
-- CMB web application.
--



----------------------------------------------------------------------
-- The following code takes care "trader_status" records are kept in
-- sync.
----------------------------------------------------------------------
DROP TRIGGER IF EXISTS init_trader_status_profile_trig ON profile;
DROP TRIGGER IF EXISTS set_trader_status_profile_trig ON profile;
DROP TRIGGER IF EXISTS unset_trader_status_profile_trig ON profile;
DROP TRIGGER IF EXISTS increase_unconfirmed_receipt_count_trig ON unconfirmed_receipt;
DROP TRIGGER IF EXISTS decrease_unconfirmed_receipt_count_trig ON unconfirmed_receipt;
DROP TRIGGER IF EXISTS increase_unconfirmed_transaction_count_trig ON unconfirmed_transaction;
DROP TRIGGER IF EXISTS decrease_unconfirmed_transaction_count_trig ON unconfirmed_transaction;
DROP TRIGGER IF EXISTS increase_unconfirmed_deal_count_trig ON unconfirmed_deal;
DROP TRIGGER IF EXISTS decrease_unconfirmed_deal_count_trig ON unconfirmed_deal;

--
-- Take care the profile information gets updated:
--

CREATE OR REPLACE FUNCTION init_trader_status_profile()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status
  SET
    p_has_profile = TRUE,
    p_time_zone = NEW.time_zone
  WHERE trader_id=NEW.trader_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_trader_status_profile()
RETURNS trigger AS $$
BEGIN
  IF NEW.time_zone <> OLD.time_zone THEN
    UPDATE trader_status
    SET
      p_has_profile = TRUE,
      p_time_zone = NEW.time_zone
    WHERE trader_id=NEW.trader_id;

  END IF;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION unset_trader_status_profile()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status
  SET
    p_has_profile = FALSE,
    p_time_zone = ''
  WHERE trader_id=OLD.trader_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER init_trader_status_profile_trig AFTER INSERT ON profile
  FOR EACH ROW EXECUTE PROCEDURE init_trader_status_profile();

CREATE TRIGGER set_trader_status_profile_trig AFTER UPDATE ON profile
  FOR EACH ROW EXECUTE PROCEDURE set_trader_status_profile();

CREATE TRIGGER unset_trader_status_profile_trig AFTER DELETE ON profile
  FOR EACH ROW EXECUTE PROCEDURE unset_trader_status_profile();

--
-- Take care "p_unconfirmed_receipt_count" gets updated:
--

CREATE OR REPLACE FUNCTION increase_unconfirmed_receipt_count()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status_ext
  SET p_unconfirmed_receipt_count = p_unconfirmed_receipt_count + 1
  WHERE trader_id=NEW.issuer_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrease_unconfirmed_receipt_count()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status_ext
  SET p_unconfirmed_receipt_count = p_unconfirmed_receipt_count - 1
  WHERE trader_id=OLD.issuer_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER increase_unconfirmed_receipt_count_trig AFTER INSERT ON unconfirmed_receipt
  FOR EACH ROW EXECUTE PROCEDURE increase_unconfirmed_receipt_count();

CREATE TRIGGER decrease_unconfirmed_receipt_count_trig AFTER DELETE ON unconfirmed_receipt
  FOR EACH ROW EXECUTE PROCEDURE decrease_unconfirmed_receipt_count();

--
-- Take care "p_unconfirmed_transaction_count" gets updated:
--

CREATE OR REPLACE FUNCTION increase_unconfirmed_transaction_count()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status_ext
  SET
    p_unconfirmed_transaction_count = p_unconfirmed_transaction_count + 1,
    last_event_ts = CURRENT_TIMESTAMP
  WHERE trader_id=NEW.recipient_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrease_unconfirmed_transaction_count()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status_ext
  SET p_unconfirmed_transaction_count = p_unconfirmed_transaction_count - 1
  WHERE trader_id=OLD.recipient_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER increase_unconfirmed_transaction_count_trig AFTER INSERT ON unconfirmed_transaction
  FOR EACH ROW EXECUTE PROCEDURE increase_unconfirmed_transaction_count();

CREATE TRIGGER decrease_unconfirmed_transaction_count_trig AFTER DELETE ON unconfirmed_transaction
  FOR EACH ROW EXECUTE PROCEDURE decrease_unconfirmed_transaction_count();

--
-- Take care "p_unconfirmed_deal_count" gets updated:
--

CREATE OR REPLACE FUNCTION increase_unconfirmed_deal_count()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status_ext
  SET
    p_unconfirmed_deal_count = p_unconfirmed_deal_count + 1,
    last_event_ts = CURRENT_TIMESTAMP
  WHERE trader_id=NEW.recipient_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrease_unconfirmed_deal_count()
RETURNS trigger AS $$
BEGIN
  UPDATE trader_status_ext
  SET p_unconfirmed_deal_count = p_unconfirmed_deal_count - 1
  WHERE trader_id=OLD.recipient_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER increase_unconfirmed_deal_count_trig AFTER INSERT ON unconfirmed_deal
  FOR EACH ROW EXECUTE PROCEDURE increase_unconfirmed_deal_count();

CREATE TRIGGER decrease_unconfirmed_deal_count_trig AFTER DELETE ON unconfirmed_deal
  FOR EACH ROW EXECUTE PROCEDURE decrease_unconfirmed_deal_count();





----------------------------------------------------------------------
-- The following code takes care "offer" records are kept in sync.
----------------------------------------------------------------------
DROP TRIGGER IF EXISTS fill_offer_fields_trig ON offer;
DROP TRIGGER IF EXISTS increase_asset_amount_trig ON asset;
DROP TRIGGER IF EXISTS decrease_asset_amount_trig ON asset;

--
-- Take care "offer" records are properly inserted:
--

CREATE OR REPLACE FUNCTION fill_offer_fields()
RETURNS trigger AS $$
BEGIN
  SELECT 0.0, epsilon
  INTO NEW.p_amount, NEW.p_epsilon
  FROM product
  WHERE
    issuer_id=NEW.issuer_id AND
    promise_id=NEW.promise_id;

  IF FOUND THEN
    RETURN NEW;

  ELSE
    RAISE EXCEPTION 'Product not found';

  END IF;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER fill_offer_fields_trig BEFORE INSERT ON offer
  FOR EACH ROW EXECUTE PROCEDURE fill_offer_fields();

--
-- Take care "p_amount" gets updated:
--

CREATE OR REPLACE FUNCTION increase_asset_amount()
RETURNS trigger AS $$
BEGIN
  UPDATE offer
  SET p_amount = p_amount + NEW.amount
  WHERE issuer_id=NEW.issuer_id AND promise_id=NEW.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrease_asset_amount()
RETURNS trigger AS $$
BEGIN
  UPDATE offer
  SET p_amount = p_amount - OLD.amount
  WHERE issuer_id=OLD.issuer_id AND promise_id=OLD.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER increase_asset_amount_trig AFTER INSERT OR UPDATE ON asset
  FOR EACH ROW EXECUTE PROCEDURE increase_asset_amount();

CREATE TRIGGER decrease_asset_amount_trig AFTER UPDATE OR DELETE ON asset
  FOR EACH ROW EXECUTE PROCEDURE decrease_asset_amount();





----------------------------------------------------------------------
-- The following code takes care "bid" records are properly
-- initialized and kept in sync.
----------------------------------------------------------------------
DROP TRIGGER IF EXISTS fill_bid_fields_trig ON bid;
DROP TRIGGER IF EXISTS increase_unconfirmed_transaction_amount_trig ON unconfirmed_transaction;
DROP TRIGGER IF EXISTS decrease_unconfirmed_transaction_amount_trig ON unconfirmed_transaction;
DROP TRIGGER IF EXISTS increase_unconfirmed_deal_amount_trig ON unconfirmed_deal;
DROP TRIGGER IF EXISTS decrease_unconfirmed_deal_amount_trig ON unconfirmed_deal;

--
-- Take care "bid" records are properly inserted:
--

CREATE OR REPLACE FUNCTION fill_bid_fields()
RETURNS trigger AS $$
BEGIN
  SELECT 0.0, COALESCE(SUM(amount), 0.0)
  INTO NEW.p_unconfirmed_transaction_amount, NEW.p_unconfirmed_deal_amount
  FROM unconfirmed_deal
  WHERE
    recipient_id=NEW.recipient_id AND
    issuer_id=NEW.issuer_id AND
    promise_id=NEW.promise_id;

  RETURN NEW;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER fill_bid_fields_trig BEFORE INSERT ON bid
  FOR EACH ROW EXECUTE PROCEDURE fill_bid_fields();

--
-- Take care "p_unconfirmed_transaction_amount" gets updated:
--

CREATE OR REPLACE FUNCTION increase_unconfirmed_transaction_amount()
RETURNS trigger AS $$
BEGIN
  UPDATE bid
  SET p_unconfirmed_transaction_amount = p_unconfirmed_transaction_amount + NEW.amount
  WHERE
    recipient_id=NEW.recipient_id AND
    issuer_id=NEW.issuer_id AND
    promise_id=NEW.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrease_unconfirmed_transaction_amount()
RETURNS trigger AS $$
BEGIN
  UPDATE bid
  SET p_unconfirmed_transaction_amount = p_unconfirmed_transaction_amount - OLD.amount
  WHERE
    recipient_id=OLD.recipient_id AND
    issuer_id=OLD.issuer_id AND
    promise_id=OLD.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER increase_unconfirmed_transaction_amount_trig AFTER INSERT ON unconfirmed_transaction
  FOR EACH ROW EXECUTE PROCEDURE increase_unconfirmed_transaction_amount();

CREATE TRIGGER decrease_unconfirmed_transaction_amount_trig AFTER DELETE ON unconfirmed_transaction
  FOR EACH ROW EXECUTE PROCEDURE decrease_unconfirmed_transaction_amount();

--
-- Take care "p_unconfirmed_deal_amount" gets updated:
--

CREATE OR REPLACE FUNCTION increase_unconfirmed_deal_amount()
RETURNS trigger AS $$
BEGIN
  UPDATE bid
  SET p_unconfirmed_deal_amount = p_unconfirmed_deal_amount + NEW.amount
  WHERE
    recipient_id=NEW.recipient_id AND
    issuer_id=NEW.issuer_id AND
    promise_id=NEW.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrease_unconfirmed_deal_amount()
RETURNS trigger AS $$
BEGIN
  UPDATE bid
  SET p_unconfirmed_deal_amount = p_unconfirmed_deal_amount - OLD.amount
  WHERE
    recipient_id=OLD.recipient_id AND
    issuer_id=OLD.issuer_id AND
    promise_id=OLD.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER increase_unconfirmed_deal_amount_trig AFTER INSERT ON unconfirmed_deal
  FOR EACH ROW EXECUTE PROCEDURE increase_unconfirmed_deal_amount();

CREATE TRIGGER decrease_unconfirmed_deal_amount_trig AFTER DELETE ON unconfirmed_deal
  FOR EACH ROW EXECUTE PROCEDURE decrease_unconfirmed_deal_amount();





----------------------------------------------------------------------
-- The following code creates trigger functions to keep the
-- "mv_recent_deal" table in sync with "recent_deal".
----------------------------------------------------------------------
DROP TRIGGER IF EXISTS insert_mv_recent_deal_trig ON recent_deal;

CREATE OR REPLACE FUNCTION insert_mv_recent_deal()
RETURNS trigger AS $$
BEGIN
  INSERT INTO mv_recent_deal (
    turn_id, recipient_id, issuer_id, promise_id,
    amount, price, ts,
    title, unit, summary, epsilon)
  SELECT
    NEW.turn_id, NEW.recipient_id, NEW.issuer_id, NEW.promise_id,
    NEW.amount, NEW.price, NEW.ts,
    title, unit, summary, epsilon
  FROM product
  WHERE issuer_id=NEW.issuer_id AND promise_id=NEW.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER insert_mv_recent_deal_trig AFTER INSERT ON recent_deal
  FOR EACH ROW EXECUTE PROCEDURE insert_mv_recent_deal();





----------------------------------------------------------------------
-- The following code creates trigger functions to keep "mv_asset"
-- table in sync with "asset".
----------------------------------------------------------------------
DROP TRIGGER IF EXISTS insert_mv_asset_trig ON asset;
DROP TRIGGER IF EXISTS update_mv_asset_trig ON asset;

CREATE OR REPLACE FUNCTION insert_mv_asset()
RETURNS trigger AS $$
BEGIN
  INSERT INTO mv_asset (recipient_id, issuer_id, promise_id, amount)
  VALUES (NEW.recipient_id, NEW.issuer_id, NEW.promise_id, NEW.amount);

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_mv_asset()
RETURNS trigger AS $$
BEGIN
  UPDATE mv_asset
  SET
    recipient_id = NEW.recipient_id,
    issuer_id = NEW.issuer_id,
    promise_id = NEW.promise_id,
    amount = NEW.amount
  WHERE
    recipient_id=OLD.recipient_id AND
    issuer_id=OLD.issuer_id AND
    promise_id=OLD.promise_id;

  RETURN NULL;

END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER insert_mv_asset_trig AFTER INSERT ON asset
  FOR EACH ROW EXECUTE PROCEDURE insert_mv_asset();

CREATE TRIGGER update_mv_asset_trig AFTER UPDATE ON asset
  FOR EACH ROW EXECUTE PROCEDURE update_mv_asset();





----------------------------------------------------------------------
-- The following code creates a trigger function to keep "p_tsvector"
-- field in the "trust" table updated.
----------------------------------------------------------------------
DROP TRIGGER IF EXISTS calc_trust_tsvector_trig ON trust;

CREATE TRIGGER calc_trust_tsvector_trig BEFORE INSERT OR UPDATE ON trust
  FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger_column('p_tsvector', 'tsearch_config', 'name', 'comment');
