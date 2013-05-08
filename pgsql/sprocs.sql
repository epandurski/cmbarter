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
-- This file contains code defining the database stored procedures 
-- for the CMB web application.
--

CREATE OR REPLACE FUNCTION _ensure_no_turn_is_running() RETURNS void AS $$
BEGIN
  BEGIN
    PERFORM 1 
    FROM solver
    WHERE status=0
    FOR SHARE NOWAIT;

    IF FOUND THEN
      RETURN;

    END IF;

  EXCEPTION WHEN lock_not_available THEN
    NULL;

  END;

  RAISE EXCEPTION 'a turn is running';

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _opt_payment(
  _payee_id int,
  _issuer_id int,
  _promise_id int,
  _payer_id int)
RETURNS void AS $$
DECLARE
  _order_id int;
  _amount float;
  _reason text;
  _payer_name text;
  _avl_amt float;
BEGIN
  DELETE FROM delivery_automation
  WHERE
    payee_id=_payee_id AND
    payer_id=_payer_id AND
    p_issuer_id=_issuer_id AND
    p_promise_id=_promise_id;

  <<infloop>>
  LOOP
    SELECT MIN(order_id) INTO _order_id
    FROM delivery_order
    WHERE
      recipient_id=_payer_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id AND
      carrier=LPAD(_payee_id::text, 9, '0') AND
      is_active=TRUE AND
      issuer_message IS NULL;
  
    EXIT infloop WHEN _order_id IS NULL;

    SELECT amount, instructions
    INTO _amount, _reason
    FROM delivery_order
    WHERE
      recipient_id=_payer_id AND
      order_id=_order_id AND
      is_active=TRUE AND
      issuer_message IS NULL
    FOR SHARE;

    IF FOUND THEN
      --
      -- We need to obtain the available amount.
      --
      SELECT amount INTO _avl_amt
      FROM asset WHERE
        recipient_id=_payer_id AND
	issuer_id=_issuer_id AND
	promise_id=_promise_id;

      IF NOT FOUND THEN
        _avl_amt := 0.0;

      END IF;

      IF _amount <= _avl_amt THEN
        --
        -- Puts the delivery order in the payee's list of incoming
        -- payments if the requested amount is available.
	--
        SELECT full_name INTO _payer_name
        FROM profile
        WHERE trader_id=_payer_id;
  
        BEGIN
          INSERT INTO delivery_automation (
            payer_id, order_id,
            payee_id, reason,
            p_issuer_id, p_promise_id, p_amount,
            p_payer_name)
          VALUES (
            _payer_id, _order_id,
            _payee_id, _reason,
            _issuer_id, _promise_id, _amount,
            _payer_name);
    
        EXCEPTION WHEN unique_violation THEN
          NULL;
    
        END;
  
        EXIT infloop;

      ELSE
        --
        -- Rejects the delivery order if the requested amount is not
        -- available.
	--
        UPDATE delivery_status
        SET
          issuer_message='',
          execution_ts=NULL
        WHERE
          recipient_id=_payer_id AND
          order_id=_order_id;
    
      END IF;
   
    END IF;

  END LOOP;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _cancel_delivery_automation(
  _payer_id int,
  _order_id int)
RETURNS void AS $$
DECLARE
  _payee_id int;
  _issuer_id int;
  _promise_id int;
BEGIN
  SELECT payee_id, p_issuer_id, p_promise_id
  INTO _payee_id, _issuer_id, _promise_id
  FROM delivery_automation
  WHERE payer_id=_payer_id AND order_id=_order_id;

  IF FOUND THEN
    PERFORM _opt_payment(_payee_id, _issuer_id, _promise_id, _payer_id);

  END IF;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _increase_asset(
  _recipient_id int,
  _issuer_id int,
  _promise_id int,
  _amount float,
  _epsilon float)
RETURNS void AS $$
BEGIN
  <<infloop>>
  LOOP
    UPDATE asset
    SET
      amount = amount + _amount,
      last_change_ts = CURRENT_TIMESTAMP,
      epsilon = _epsilon
    WHERE
      recipient_id=_recipient_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id;

    EXIT infloop WHEN FOUND;

    BEGIN
      INSERT INTO asset (
        recipient_id, issuer_id, promise_id,
        amount, last_change_ts, epsilon)
      VALUES (
        _recipient_id, _issuer_id, _promise_id,
        _amount, CURRENT_TIMESTAMP, _epsilon);

      EXIT infloop;

    EXCEPTION WHEN unique_violation THEN
      NULL;

    END;

  END LOOP;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _insert_unconfirmed_deal(
  _turn_id int,
  _recipient_id int,
  _issuer_id int,
  _promise_id int,
  _amount float,
  _price value,
  _ts timestamp with time zone)
RETURNS void AS $$
DECLARE
  _title text;
  _unit text;
  _summary text;
  _epsilon float;
BEGIN
  -- We DO NOT need to obtain a lock on the corresponding "product"
  -- record, because a lock on "solver" must be held at that time.
  SELECT title, unit, summary, epsilon
  INTO _title, _unit, _summary, _epsilon
  FROM product
  WHERE
    issuer_id=_issuer_id AND
    promise_id=_promise_id;

  IF FOUND THEN
    INSERT INTO unconfirmed_deal (
      turn_id, recipient_id, issuer_id, promise_id,
      amount, price, ts,
      title, unit, summary, epsilon)
    VALUES (
      _turn_id, _recipient_id, _issuer_id, _promise_id,
      _amount, _price, _ts,
      _title, _unit, _summary, _epsilon);

  ELSE
    RAISE EXCEPTION 'Product not found';

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _confirm_deal(
  _turn_id int,
  _recipient_id int,
  _issuer_id int,
  _promise_id int)
RETURNS void AS $$
DECLARE
  _amount float;
BEGIN
  -- We try to obtain a lock on the corresponding "product" record, in
  -- order to prevent race-condition when new shopping-items are
  -- inserted.  It is OK if the product record does not exist because
  -- in this case new shopping-items can not be inserted.
  PERFORM 1
  FROM product
  WHERE
    issuer_id=_issuer_id AND
    promise_id=_promise_id
  FOR UPDATE;

  DELETE FROM unconfirmed_deal
  WHERE
    turn_id=_turn_id AND
    recipient_id=_recipient_id AND
    issuer_id=_issuer_id AND
    promise_id=_promise_id
  RETURNING amount INTO _amount;

  IF FOUND THEN
    -- We need to update the prescribed amount in the recipient's bid
    -- because a relevant sale has occurred.
    UPDATE bid
    SET amount = amount - _amount
    WHERE
      recipient_id=_recipient_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id;

    -- We update the last_recorded_indirect_activity_ts field for the
    -- issuer, because we do not want to kill a user that do not log
    -- in, but still continues to get new deals.
    UPDATE trader_status_ext
    SET last_recorded_indirect_activity_ts = CURRENT_TIMESTAMP
    WHERE trader_id=_issuer_id AND last_recorded_indirect_activity_ts <= CURRENT_TIMESTAMP - INTERVAL '1 day';

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _confirm_transaction(
  _unconfirmed_transaction_id bigint)
RETURNS void AS $$
DECLARE
  _recipient_id int;
  _issuer_id int;
  _promise_id int;
  _amount float;
BEGIN
  DELETE FROM unconfirmed_transaction
  WHERE id=_unconfirmed_transaction_id
  RETURNING recipient_id, issuer_id, promise_id, amount
  INTO _recipient_id, _issuer_id, _promise_id, _amount;

  IF FOUND THEN
    -- We need to update the prescribed amount in the recipient's bid
    -- because a relevant transaction has occurred.
    UPDATE bid
    SET amount = amount - _amount
    WHERE
      recipient_id=_recipient_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _delete_product_offer(
  _issuer_id int,
  _promise_id int)
RETURNS void AS $$
BEGIN
  DELETE FROM offer
  WHERE issuer_id=_issuer_id AND promise_id=_promise_id;

  IF FOUND THEN
    INSERT INTO offer_removal (issuer_id, promise_id)
    VALUES (_issuer_id, _promise_id);

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _purge_trader_objects(
  _trader_id int)
RETURNS void AS $$
DECLARE
  _promise_id int;
  _unconfirmed_transaction_id bigint;
BEGIN
  UPDATE profile
  SET
    (full_name, summary, country, postal_code, address, email, phone, fax, www, time_zone, photograph_id)
    = ('?', '', '', '', '', '', '', '', '', '?', NULL)
  WHERE trader_id=_trader_id;

  DELETE FROM image WHERE trader_id=_trader_id;

  DELETE FROM bid WHERE recipient_id=_trader_id;

  DELETE FROM trust WHERE recipient_id=_trader_id;

  FOR _promise_id IN
    SELECT promise_id FROM offer WHERE issuer_id=_trader_id

  LOOP
    PERFORM _delete_product_offer(_trader_id, _promise_id);

  END LOOP;

  DELETE FROM asset WHERE issuer_id=_trader_id;

  FOR _unconfirmed_transaction_id IN
    SELECT id FROM unconfirmed_transaction WHERE recipient_id=_trader_id

  LOOP
    PERFORM _confirm_transaction(_unconfirmed_transaction_id);

  END LOOP;

  DELETE FROM delivery_status WHERE recipient_id=_trader_id;

  UPDATE trader_status_ext
  SET banned_until_ts = CURRENT_TIMESTAMP + interval '1000 years'
  WHERE trader_id=_trader_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION ban_trader_permanently(
  _trader_id int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  PERFORM _purge_trader_objects(_trader_id);

END
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION report_transaction_cost(_trader_id int, _cost float) RETURNS void AS $$
BEGIN
  UPDATE trader_status
  SET accumulated_transaction_cost = accumulated_transaction_cost + _cost
  WHERE trader_id=_trader_id;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION acquire_email_verification_rights(_trader_id int) RETURNS boolean AS $$
BEGIN
  UPDATE trader_status
  SET max_email_verification_count = max_email_verification_count - 1
  WHERE trader_id=_trader_id AND max_email_verification_count > 0;

  RETURN FOUND;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION acquire_sent_email_rights(_trader_id int) RETURNS boolean AS $$
BEGIN
  UPDATE trader_status
  SET max_sent_email_count = max_sent_email_count - 1
  WHERE trader_id=_trader_id AND max_sent_email_count > 0;

  RETURN FOUND;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION acquire_received_email_rights(_trader_id int) RETURNS boolean AS $$
BEGIN
  UPDATE trader_status
  SET max_received_email_count = max_received_email_count - 1
  WHERE trader_id=_trader_id AND max_received_email_count > 0;

  RETURN FOUND;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _generate_promise_id(_trader_id int) RETURNS int AS $$
DECLARE
  _promise_id int;
BEGIN
  UPDATE trader_status
  SET last_generated_promise_id = COALESCE(last_generated_promise_id, 0) + 1
  WHERE trader_id=_trader_id AND (
    last_generated_promise_id IS NULL OR
    last_generated_promise_id < max_generated_promise_id)
  RETURNING last_generated_promise_id INTO _promise_id;

  IF FOUND THEN
    RETURN _promise_id;

  ELSE
    RETURN NULL;

  END IF;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _generate_handoff_id(_trader_id int) RETURNS int AS $$
DECLARE
  _handoff_id int;
BEGIN
  UPDATE trader_status
  SET last_generated_handoff_id = COALESCE(last_generated_handoff_id, 0) + 1
  WHERE trader_id=_trader_id AND (
    last_generated_handoff_id IS NULL OR
    last_generated_handoff_id < max_generated_handoff_id)
  RETURNING last_generated_handoff_id INTO _handoff_id;

  IF FOUND THEN
    RETURN _handoff_id;

  ELSE
    RETURN NULL;

  END IF;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _generate_order_id(_trader_id int) RETURNS int AS $$
DECLARE
  _order_id int;
BEGIN
  UPDATE trader_status
  SET last_generated_order_id = COALESCE(last_generated_order_id, 0) + 1
  WHERE trader_id=_trader_id AND (
    last_generated_order_id IS NULL OR
    last_generated_order_id < max_generated_order_id)
  RETURNING last_generated_order_id INTO _order_id;

  IF FOUND THEN
    RETURN _order_id;

  ELSE
    RETURN NULL;

  END IF;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _lock_solver()
RETURNS boolean AS $$
BEGIN
  PERFORM pg_advisory_lock(1);

  UPDATE solver
  SET status=1
  WHERE status=0 AND CURRENT_TIMESTAMP >= next_turn_start_ts;

  RETURN FOUND;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _prepare_commitments()
RETURNS boolean AS $$
BEGIN
  PERFORM 1 FROM solver WHERE status=1 FOR SHARE;

  IF FOUND THEN
    DROP INDEX IF EXISTS commitment_ordering_idx; TRUNCATE commitment;

    INSERT INTO commitment (
      recipient_id, issuer_id, promise_id, 
      value, ordering_number)
    SELECT
      cc.recipient_id, cc.issuer_id,cc.promise_id,
      cc.value, RANDOM()
    FROM candidate_commitment cc, trader_status ts
    WHERE
      ts.trader_id=cc.issuer_id AND
      ts.offers_are_enabled=TRUE;

    CREATE INDEX commitment_ordering_idx ON commitment (ordering_number);
    ANALYZE commitment;

    DROP INDEX IF EXISTS matched_commitment_grouping_idx; TRUNCATE matched_commitment;

    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _write_deals()
RETURNS boolean AS $$
DECLARE 
  _turn_id int;
  _recipient_id int;
  _issuer_id int;
  _promise_id int;
  _amount float;
  _price value;
  _epsilon float;
BEGIN
  PERFORM 1 FROM solver WHERE status=1 FOR SHARE;

  IF FOUND THEN
    INSERT INTO turn (id) VALUES (DEFAULT) RETURNING id INTO _turn_id;

    ALTER TABLE asset DISABLE TRIGGER increase_asset_amount_trig;
    ALTER TABLE asset DISABLE TRIGGER decrease_asset_amount_trig;

    DROP INDEX IF EXISTS matched_commitment_grouping_idx;
    CREATE INDEX matched_commitment_grouping_idx ON matched_commitment (issuer_id, promise_id, recipient_id);
    ANALYZE matched_commitment;

    FOR _recipient_id, _issuer_id, _promise_id, _amount, _price, _epsilon IN
      SELECT
        mc.recipient_id, mc.issuer_id, mc.promise_id,
        CAST(SUM(mc.value)/MIN(o.price) AS float), MIN(o.price), MIN(o.p_epsilon)
      FROM matched_commitment mc, offer o
      WHERE o.issuer_id=mc.issuer_id AND o.promise_id=mc.promise_id
      GROUP BY mc.issuer_id, mc.promise_id, mc.recipient_id
      ORDER BY mc.issuer_id, mc.promise_id, mc.recipient_id
    
    LOOP
      INSERT INTO recent_deal (
        turn_id, recipient_id, issuer_id, promise_id,
        amount, price, ts)
      VALUES (
        _turn_id, _recipient_id, _issuer_id, _promise_id,
        _amount, _price, CURRENT_TIMESTAMP);

      PERFORM _increase_asset(
        _recipient_id, _issuer_id, _promise_id,
        _amount, _epsilon);

      PERFORM _insert_unconfirmed_deal(
        _turn_id, _recipient_id, _issuer_id, _promise_id,
        _amount, _price, CURRENT_TIMESTAMP);

    END LOOP;

    ALTER TABLE asset ENABLE TRIGGER increase_asset_amount_trig;
    ALTER TABLE asset ENABLE TRIGGER decrease_asset_amount_trig;

    DROP INDEX IF EXISTS commitment_ordering_idx; TRUNCATE commitment;
    DROP INDEX IF EXISTS matched_commitment_grouping_idx; TRUNCATE matched_commitment;

    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _perform_housekeeping()
RETURNS boolean AS $$
DECLARE
  _turn_id int;
  _recipient_id int;
  _issuer_id int;
  _promise_id int;
  _unconfirmed_transaction_id bigint;
  _trader_id int;
BEGIN
  PERFORM 1 FROM solver WHERE status=1 FOR SHARE;

  IF FOUND THEN
    --
    -- All traders that had been inactive for at least 3 years should
    -- get some of their stuff deleted in order to save disk space.
    --
    FOR _trader_id IN
      SELECT ts.trader_id
      FROM trader_status ts, trader_status_ext tse
      WHERE 
        tse.trader_id=ts.trader_id AND
        tse.banned_until_ts <= CURRENT_TIMESTAMP AND
        tse.last_recorded_indirect_activity_ts <= CURRENT_TIMESTAMP - INTERVAL '3 years' AND
        ts.last_recorded_activity_ts <= CURRENT_TIMESTAMP - INTERVAL '3 years'

    LOOP
      PERFORM _purge_trader_objects(_trader_id);

    END LOOP;

    --
    -- All products that have been removed from users' respective
    -- price lists for more than 1 month should be deleted.
    --
    FOR _issuer_id, _promise_id IN
      SELECT issuer_id, promise_id
      FROM offer_removal
      WHERE ts <= CURRENT_TIMESTAMP - INTERVAL '1 month'

    LOOP
      DELETE FROM product
      WHERE issuer_id=_issuer_id AND promise_id=_promise_id;

    END LOOP;

    --
    -- All negligible assets that have not been changed for 1 month
    -- should be discarded, if they are not included in the
    -- recipient's shopping list.  Also, all assets that have not been
    -- changed for 3 years, if they are not included in the
    -- recipient's shopping list, should be discarded too -- even if
    -- they are non-negligible.
    --
    DELETE FROM asset
    WHERE
      NOT EXISTS(
        SELECT 1 
        FROM bid
        WHERE
          bid.recipient_id=asset.recipient_id AND
          bid.issuer_id=asset.issuer_id AND
          bid.promise_id=asset.promise_id)
      AND (
        amount <= epsilon AND last_change_ts <= CURRENT_TIMESTAMP - INTERVAL '1 month'
        OR 
        last_change_ts <= CURRENT_TIMESTAMP - INTERVAL '3 years');

    --
    -- All "recent transactions" and "recent deals" that are older
    -- than 1 month should be deleted.
    --
    DELETE FROM recent_transaction
    WHERE ts <= CURRENT_TIMESTAMP - INTERVAL '1 month';

    DELETE FROM recent_deal
    WHERE ts <= CURRENT_TIMESTAMP - INTERVAL '1 month';

    --
    -- All "unconfirmed deals" that are older than 1 month should get
    -- automatically confirmed.
    --
    FOR _turn_id, _recipient_id, _issuer_id, _promise_id IN
      SELECT turn_id, recipient_id, issuer_id, promise_id 
      FROM unconfirmed_deal
      WHERE ts <= CURRENT_TIMESTAMP - INTERVAL '1 month'

    LOOP
      PERFORM _confirm_deal(_turn_id, _recipient_id, _issuer_id, _promise_id);

    END LOOP;

    --
    -- All delivery orders that are not active and have not been
    -- reviewed within the last day should be deleted.
    --
    DELETE FROM delivery_status
    WHERE
      is_active=FALSE AND
      (last_issuer_review_ts IS NULL OR last_issuer_review_ts <= CURRENT_TIMESTAMP - INTERVAL '1 day');

    --
    -- All "delivery_automation" records that does not have the
    -- necessary amount to make the payment should be re-considered.
    --
    FOR _trader_id, _issuer_id, _promise_id, _recipient_id IN
      SELECT p.payee_id, p.p_issuer_id, p.p_promise_id, p.payer_id
      FROM delivery_automation p LEFT OUTER JOIN asset a ON
        a.issuer_id=p.p_issuer_id AND
        a.promise_id=p.p_promise_id AND
        a.recipient_id=p.payer_id
      WHERE p.p_amount > COALESCE(a.amount, 0.0)

    LOOP
      PERFORM _opt_payment(_trader_id, _issuer_id, _promise_id, _recipient_id);

    END LOOP;

    --
    -- Users having too many unconfirmed transactions should receive
    -- additional attention -- all their unconfirmed transactions
    -- older than 1 month get automatically confirmed.
    --
    FOR _recipient_id IN
      SELECT recipient_id
      FROM unconfirmed_transaction
      GROUP BY recipient_id
      HAVING COUNT(*) > 1000

    LOOP
      FOR _unconfirmed_transaction_id IN
        SELECT id
        FROM unconfirmed_transaction
        WHERE recipient_id=_recipient_id AND ts <= CURRENT_TIMESTAMP - INTERVAL '1 month'

      LOOP
        PERFORM _confirm_transaction(_unconfirmed_transaction_id);

      END LOOP;

    END LOOP;

    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _schedule_notifications()
RETURNS boolean AS $$
DECLARE
  _ni interval;  -- the notification interval
  _trader_id int;
  _email text;
  _email_cancellation_code text;
BEGIN
  PERFORM 1 FROM solver WHERE status=1 FOR SHARE;

  IF FOUND THEN
    _ni := interval '1 week';  -- must be greater than 1 day

    FOR _trader_id, _email, _email_cancellation_code IN
      SELECT ts.trader_id, ve.email, ve.email_cancellation_code
      FROM
        trader_status ts, 
        trader_status_ext tse,
        verified_email ve
      WHERE
        tse.trader_id=ts.trader_id AND
        tse.banned_until_ts <= CURRENT_TIMESTAMP AND  -- the user is not banned
        tse.p_unconfirmed_transaction_count + tse.p_unconfirmed_deal_count > 0 AND  -- there are unconfirmed deals/transactions
        tse.last_event_notification_ts < tse.last_event_ts AND  -- the events seems to be fresh
        tse.last_event_notification_ts < CURRENT_TIMESTAMP - _ni AND  -- some time has passed since the last notification
        tse.last_event_notification_ts < ts.last_recorded_activity_ts + _ni AND  -- looks like the user pays attention to notifications
        ve.trader_id=ts.trader_id AND  -- the user has a verified email
        ts.last_recorded_activity_ts <= CURRENT_TIMESTAMP - _ni  -- the user have not logged in for some time

    LOOP
      BEGIN
        INSERT INTO outgoing_notification (trader_id, to_mailbox, email_cancellation_code) 
        VALUES (_trader_id, _email, _email_cancellation_code);

      EXCEPTION
        WHEN foreign_key_violation THEN
          NULL;  -- this should never happen, but anyway, it does no harm to be prepared

      END;

      UPDATE trader_status_ext
      SET last_event_notification_ts = CURRENT_TIMESTAMP
      WHERE trader_id=_trader_id;

    END LOOP;

    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _update_user_limits()
RETURNS boolean AS $$
BEGIN
  PERFORM 1 FROM solver WHERE status=1 FOR SHARE;

  IF FOUND THEN
    LOCK TABLE trader_status IN EXCLUSIVE MODE;

    UPDATE trader_status
    SET
      max_email_verification_count = 5,
      max_sent_email_count = 10,
      max_received_email_count = 1000,
      max_login_count = 1000,
      accumulated_transaction_cost = 0.0,
      max_generated_photograph_id =
        + 100
        + COALESCE(last_generated_photograph_id, 0),
      max_generated_promise_id =
        + 200
        + COALESCE(last_generated_promise_id, 0)
        - (SELECT COUNT(*) FROM offer WHERE issuer_id=trader_id) 
        - (SELECT COUNT(*) FROM offer_removal WHERE issuer_id=trader_id),
      max_generated_handoff_id =
        + 3000
        + COALESCE(last_generated_handoff_id, 0)
        - (SELECT COUNT(*) FROM unconfirmed_receipt WHERE issuer_id=trader_id),
      max_generated_order_id =
        + 1000
        + COALESCE(last_generated_order_id, 0)
        - (SELECT COUNT(*) FROM delivery_status WHERE recipient_id=trader_id),
      last_limits_update_ts = CURRENT_TIMESTAMP
    WHERE last_limits_update_ts <= CURRENT_TIMESTAMP - interval '1 month';

    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _unlock_solver()
RETURNS void AS $$
DECLARE
  ltts timestamp with time zone;
  ti interval;
  n int;
BEGIN
  SELECT next_turn_start_ts, turn_interval INTO ltts, ti
  FROM solver
  WHERE status=1
  FOR UPDATE;

  IF FOUND THEN
    n := CEIL(EXTRACT(epoch from CURRENT_TIMESTAMP - ltts) / EXTRACT(epoch from ti));

    UPDATE solver
    SET status=0, next_turn_start_ts=(ltts + n * ti);

    DROP INDEX IF EXISTS commitment_ordering_idx; TRUNCATE commitment;
    DROP INDEX IF EXISTS matched_commitment_grouping_idx; TRUNCATE matched_commitment;

  END IF;

  PERFORM pg_advisory_unlock(1);

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_trader(
  _id int,
  _username text,
  _language_code text,
  _password_hash crypt_hash,
  _password_salt text,
  _registration_key text)
RETURNS int AS $$
DECLARE
  _username_lowercase text;
BEGIN
  IF _registration_key IS NOT NULL THEN
    IF _registration_key='' THEN
      RETURN 3;  -- The registration key is invalid.

    END IF;

    IF EXISTS(SELECT 1 FROM trader WHERE registration_key=_registration_key) THEN
      RETURN 3;  -- The registration key is invalid.

    END IF;
  
  END IF;
  
  _username_lowercase := LOWER(_username);

  IF EXISTS(SELECT 1 FROM trader WHERE username_lowercase=_username_lowercase) THEN
    RETURN 2;  -- The username is taken.

  ELSE
    BEGIN
      INSERT INTO trader (id, username_lowercase, password_hash, password_salt, registration_key)
      VALUES (_id, _username_lowercase, _password_hash, _password_salt, _registration_key);

    EXCEPTION WHEN unique_violation THEN
      RETURN 1;  -- Most probably the ID taken. 

    END;
    
  END IF;

  INSERT INTO trader_status (trader_id, username, last_request_language_code)
  VALUES (_id, _username, _language_code);

  INSERT INTO trader_status_ext (trader_id)
  VALUES (_id);

  RETURN 0;  -- Success

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _replace_email_verification (
  _trader_id int,
  _email text)
RETURNS void AS $$
BEGIN
  <<infloop>>
  LOOP
    UPDATE email_verification
    SET
      email=_email,
      email_verification_code=NULL,
      email_verification_code_ts=NULL
    WHERE trader_id=_trader_id;
    
    EXIT infloop WHEN FOUND;
    
    BEGIN
      INSERT INTO email_verification (trader_id, email) VALUES (_trader_id, _email);
    
      EXIT infloop;

    EXCEPTION WHEN unique_violation THEN
      NULL;
    
    END;
    
  END LOOP;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_profile(
  _trader_id int,
  _full_name text,
  _summary text,
  _country text,
  _postal_code text,
  _address text,
  _email text,
  _phone text,
  _fax text,
  _www text,
  _time_zone text)
RETURNS void AS $$
BEGIN
  IF EXISTS(SELECT 1 FROM profile WHERE trader_id=_trader_id) THEN
    RETURN;

  END IF;

  INSERT INTO profile (
    trader_id, full_name, summary, country, 
    postal_code, address, email, phone, fax, www, time_zone, photograph_id)
  VALUES (
    _trader_id, _full_name, _summary, _country, 
    _postal_code, _address, _email, _phone, _fax, _www, _time_zone, NULL);

  IF _email <> '' THEN
    PERFORM _replace_email_verification(_trader_id, _email);

  END IF;

EXCEPTION
  WHEN unique_violation THEN
    NULL;

  WHEN foreign_key_violation THEN
    NULL;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_profile(
  _trader_id int,
  _full_name text,
  _summary text,
  _country text,
  _postal_code text,
  _address text,
  _new_email text,
  _phone text,
  _fax text,
  _www text,
  _time_zone text,
  _advertise_trusted_partners boolean)
RETURNS void AS $$
DECLARE
  _old_email text;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT email INTO _old_email FROM profile WHERE trader_id=_trader_id FOR UPDATE;

  IF FOUND THEN
    UPDATE profile
    SET (
      full_name, summary, country, 
      postal_code, address, email, phone, fax, www, time_zone, advertise_trusted_partners)
    = (
      _full_name, _summary, _country, 
      _postal_code, _address, _new_email, _phone, _fax, _www, _time_zone, _advertise_trusted_partners)
    WHERE trader_id=_trader_id;
  
    IF _new_email <> '' AND _new_email <> _old_email THEN
      PERFORM _replace_email_verification(_trader_id, _new_email);

    END IF;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION generate_photograph_id(_trader_id int) RETURNS int AS $$
DECLARE
  _photograph_id int;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  UPDATE trader_status
  SET last_generated_photograph_id = COALESCE(last_generated_photograph_id, 0) + 1
  WHERE trader_id=_trader_id AND (
    last_generated_photograph_id IS NULL OR
    last_generated_photograph_id < max_generated_photograph_id)
  RETURNING last_generated_photograph_id INTO _photograph_id;

  IF FOUND THEN
    RETURN _photograph_id;

  ELSE
    RETURN NULL;

  END IF;

END;    
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION replace_profile_photograph(
  _trader_id int,
  _photograph_id int,
  _raw_content bytea)
RETURNS void AS $$
DECLARE
  _old_photograph_id int;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT photograph_id INTO _old_photograph_id
  FROM profile
  WHERE trader_id=_trader_id
  FOR UPDATE;

  IF FOUND THEN
    INSERT INTO image (trader_id, photograph_id, raw_content)
    VALUES (_trader_id, _photograph_id, _raw_content);

    UPDATE profile
    SET photograph_id=_photograph_id
    WHERE trader_id=_trader_id;

    IF _old_photograph_id IS NOT NULL THEN
      DELETE FROM image
      WHERE trader_id=_trader_id AND photograph_id=_old_photograph_id;

    END IF;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_password(
  _trader_id int,
  _old_password_hash text,
  _new_password_hash text)
RETURNS boolean AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  UPDATE trader
  SET password_hash=_new_password_hash
  WHERE id=_trader_id AND password_hash=_old_password_hash;

  RETURN FOUND;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_username(
  _trader_id int,
  _password_hash text,
  _new_username text)
RETURNS int AS $$
DECLARE
  _new_username_lowercase text;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  _new_username_lowercase := LOWER(_new_username);

  BEGIN
    UPDATE trader
    SET username_lowercase=_new_username_lowercase
    WHERE id=_trader_id AND password_hash=_password_hash;

    IF NOT FOUND THEN
      RETURN 2; -- Wrong password.

    END IF;

  EXCEPTION
    WHEN unique_violation THEN
      RETURN 1;  -- The username is already taken.

  END;

  UPDATE trader_status
  SET username=_new_username
  WHERE trader_id=_trader_id;

  RETURN 0;  -- Success

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_product_offer(
  _issuer_id int,
  _title text,
  _summary text,
  _description text,
  _unit text,
  _epsilon float)
RETURNS boolean AS $$
DECLARE
  _promise_id int;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  --
  -- First: Pick a promise ID.
  --
  _promise_id := _generate_promise_id(_issuer_id);

  IF _promise_id IS NULL THEN
    RETURN FALSE;  -- invalid promise ID

  END IF;

  --
  -- Second: Insert the product.
  --
  INSERT INTO product (
    issuer_id, promise_id,
    title, summary, description, unit, epsilon)
  VALUES (
    _issuer_id, _promise_id,
    _title, _summary, _description, _unit, _epsilon);
  
  --
  -- Third: Insert an offer for the new product.
  --
  INSERT INTO offer (issuer_id, promise_id, price) 
  VALUES (_issuer_id, _promise_id, NULL);
  
  RETURN TRUE;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_product_offer(
  _issuer_id int,
  _promise_id int,
  _price value)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  UPDATE offer
  SET price=_price
  WHERE issuer_id=_issuer_id AND promise_id=_promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_product_offer(
  _issuer_id int,
  _promise_id int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  --
  -- First: Obtain a lock on the "product" record, making sure no
  -- transactions can interfere with what we do.
  --
  PERFORM 1
  FROM product
  WHERE issuer_id=_issuer_id AND promise_id=_promise_id
  FOR UPDATE;

  IF FOUND THEN
    --
    -- Second: Make sure there are no deposits outstanding.
    --
    PERFORM 1
    FROM product_deposit
    WHERE issuer_id=_issuer_id AND promise_id=_promise_id;
  
    IF NOT FOUND THEN
      PERFORM _delete_product_offer(_issuer_id, _promise_id);

    END IF;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION replace_trust(
  _recipient_id int,
  _issuer_id int,
  _name text,
  _comment text)
RETURNS boolean AS $$
DECLARE
  _trust_count int;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  BEGIN
    UPDATE trust
    SET name=_name, comment=_comment
    WHERE recipient_id=_recipient_id AND issuer_id=_issuer_id;

  EXCEPTION
    WHEN unique_violation THEN
      RETURN FALSE;

  END;

  IF NOT FOUND THEN
    -- If we are dealing with a new partner, we insert a new record.
    -- Although we may end up having done nothing if case some very
    -- odd transaction serialization had happened, it is user's
    -- responsibility to avoid or resolve such problems.
    SELECT COUNT(*) INTO _trust_count
    FROM trust
    WHERE recipient_id=_recipient_id;

    IF _trust_count < 400 THEN
      BEGIN
        INSERT INTO trust (recipient_id, issuer_id, name, comment)
        VALUES (_recipient_id, _issuer_id, _name, _comment);

      EXCEPTION
        WHEN unique_violation THEN
          RETURN FALSE;		

        WHEN foreign_key_violation THEN
          RETURN FALSE;		

        WHEN check_violation THEN
          RETURN FALSE;		
	
      END;

    END IF;
  
  END IF;

  RETURN TRUE;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_trust(
  _recipient_id int,
  _issuer_id int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  DELETE FROM trust
  WHERE recipient_id=_recipient_id AND issuer_id=_issuer_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_shopping_item(
  _recipient_id int,
  _issuer_id int,
  _promise_id int)
RETURNS void AS $$
DECLARE
  _title text;
  _unit text;
  _summary text;
  _epsilon float;
  _bid_count int;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  -- We need to obtain a lock on the corresponding "product" record,
  -- making sure "p_unconfirmed_deal_amount" will be properly
  -- initialized.
  SELECT title, unit, summary, epsilon
  INTO _title, _unit, _summary, _epsilon
  FROM product
  WHERE
    issuer_id=_issuer_id AND
    promise_id=_promise_id
  FOR SHARE;

  IF FOUND THEN
    SELECT COUNT(*) INTO _bid_count
    FROM bid
    WHERE recipient_id=_recipient_id;

    IF _bid_count < 400 THEN
      BEGIN
        INSERT INTO bid (recipient_id, issuer_id, promise_id)
        VALUES (_recipient_id, _issuer_id, _promise_id);

      EXCEPTION
        WHEN unique_violation THEN
          RETURN;

        WHEN foreign_key_violation THEN
          RETURN;

      END;

      INSERT INTO bid_product (
        recipient_id, issuer_id, promise_id,
        title, unit, summary, epsilon)
      VALUES (
        _recipient_id, _issuer_id, _promise_id,
        _title, _unit, _summary, _epsilon);

    END IF;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_shopping_item(
  _recipient_id int,
  _issuer_id int,
  _promise_id int,
  _need_amount float,
  _recipient_price value)
RETURNS void AS $$
DECLARE
  _have_amount float;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT have_amount INTO _have_amount
  FROM extended_bid
  WHERE
    recipient_id=_recipient_id AND
    issuer_id=_issuer_id AND
    promise_id=_promise_id;

  IF FOUND THEN
    -- Although user's intentions may get messed up by some odd
    -- transaction serialization, it is user's responsibility to
    -- avoid or resolve such problems.
    UPDATE bid
    SET 
      amount = _need_amount - _have_amount,
      price = _recipient_price
    WHERE
      recipient_id=_recipient_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_shopping_item(
  _recipient_id int,
  _issuer_id int,
  _promise_id int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  DELETE FROM bid
  WHERE
    recipient_id=_recipient_id AND
    issuer_id=_issuer_id AND
    promise_id=_promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_transaction(
  _issuer_id int,
  _recipient_id int,
  _promise_id int,
  _amount float,
  _reason text,
  _is_a_payment boolean,
  _payment_payer_name text,
  _payment_reason text,
  _payment_payer_id int,
  _payment_order_id int,
  _payment_payee_id int)
RETURNS boolean AS $$
DECLARE
  _title text;
  _unit text;
  _summary text;
  _epsilon float;
  _avl_amt float;
  _handoff_id int;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  --
  -- First: Obtain a lock on the "product" record, making sure no
  -- other transactions can interfere with what we do.
  --
  SELECT p.title, p.unit, p.summary, p.epsilon
  INTO _title, _unit, _summary, _epsilon
  FROM product p, offer o
  WHERE
    o.issuer_id=p.issuer_id AND o.promise_id=p.promise_id AND
    p.issuer_id=_issuer_id AND p.promise_id=_promise_id
  FOR UPDATE;  -- we lock the "offer" row too, because we do not it being deleted under our feet.

  IF NOT FOUND THEN
    RETURN FALSE;  -- missing product

  END IF;

  --
  -- Second: Check the available amount.
  --
  SELECT amount INTO _avl_amt
  FROM asset
  WHERE
    recipient_id=_recipient_id AND
    issuer_id=_issuer_id AND
    promise_id=_promise_id;

  IF NOT FOUND THEN
    _avl_amt := 0.0;

  END IF;
    
  IF _avl_amt + _amount < LEAST(_avl_amt, 0.0) THEN
    RETURN FALSE;  -- insufficient amount

  END IF;

  --
  -- Third: Pick a handoff ID.
  --
  -- If this is a payment transaction, we increment the
  -- "max_generated_handoff_id" in advance , so as to make sure the
  -- number of issued payments is not limited by it.
  IF _is_a_payment=TRUE THEN
    UPDATE trader_status
    SET max_generated_handoff_id = max_generated_handoff_id + 1
    WHERE trader_id=_issuer_id;

  END IF;

  _handoff_id := _generate_handoff_id(_issuer_id);

  IF _handoff_id IS NULL THEN
    RETURN FALSE;  -- invalid handoff ID

  END IF;
  
  --
  -- Fourth: Try to add the transaction to the list of committed
  -- transactions.
  --
  BEGIN
    INSERT INTO recent_transaction (
      issuer_id, handoff_id, 
      recipient_id, promise_id, amount, reason, ts,
      is_a_payment, payment_payer_name, payment_reason,
      payment_payer_id, payment_order_id, payment_payee_id)
    VALUES (
      _issuer_id, _handoff_id,
      _recipient_id, _promise_id, _amount, _reason, CURRENT_TIMESTAMP,
      _is_a_payment, _payment_payer_name, _payment_reason,
      _payment_payer_id, _payment_order_id, _payment_payee_id);
  
  EXCEPTION
    WHEN foreign_key_violation THEN
      RETURN FALSE;  -- bad trader ID
  
  END;
  
  --
  -- Fifth: Update the corresponding "asset" record.
  --
  PERFORM _increase_asset(_recipient_id, _issuer_id, _promise_id, _amount, _epsilon);

  --
  -- Sixth: Inform the recipient about the transaction.
  --
  BEGIN
    INSERT INTO unconfirmed_transaction (
      issuer_id, handoff_id, 
      recipient_id, promise_id, amount, reason,
      title, unit, summary, epsilon, ts,
      is_a_payment, payment_payer_name, payment_reason,
      payment_payer_id, payment_order_id, payment_payee_id)
    VALUES (
      _issuer_id, _handoff_id,
      _recipient_id, _promise_id, _amount, _reason,
      _title, _unit, _summary, _epsilon, CURRENT_TIMESTAMP,
      _is_a_payment, _payment_payer_name, _payment_reason,
      _payment_payer_id, _payment_order_id, _payment_payee_id);

  EXCEPTION
    WHEN foreign_key_violation THEN
      NULL;

  END;

  IF NOT _is_a_payment THEN
    -- Seventh: Make a record in the "unconfirmed_receipt" table in
    -- order to reliably inform the issuer that the transaction has
    -- been committed successfully.
    INSERT INTO unconfirmed_receipt (
      issuer_id, handoff_id,
      recipient_id, promise_id, amount, reason, ts)
    VALUES (
      _issuer_id, _handoff_id,
      _recipient_id, _promise_id, _amount, _reason, CURRENT_TIMESTAMP);

  END IF;
  
  RETURN TRUE;
  
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION confirm_receipt(
  _issuer_id int,
  _handoff_id int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  DELETE FROM unconfirmed_receipt 
  WHERE issuer_id=_issuer_id AND handoff_id=_handoff_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION confirm_deal(
  _turn_id int,
  _recipient_id int,
  _issuer_id int,
  _promise_id int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  PERFORM _confirm_deal(_turn_id, _recipient_id, _issuer_id, _promise_id);

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION confirm_transaction(
  _recipient_id int,
  _unconfirmed_transaction_id bigint)
RETURNS void AS $$
DECLARE
  _is_a_payment boolean;
  _payment_payer_id int;
  _payment_order_id int;
  _amount float;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT is_a_payment, payment_payer_id, payment_order_id, amount
  INTO _is_a_payment, _payment_payer_id, _payment_order_id, _amount
  FROM unconfirmed_transaction
  WHERE id=_unconfirmed_transaction_id AND recipient_id=_recipient_id;

  IF FOUND THEN
    PERFORM _confirm_transaction(_unconfirmed_transaction_id);

    -- We want to deactivate the corresponding delivery order of a
    -- completed payment.
    IF _is_a_payment=TRUE AND _amount < 0.0 THEN
      PERFORM deactivate_delivery_order(_payment_payer_id, _payment_order_id);

    END IF;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_delivery_order(
  _recipient_id int,
  _issuer_id int,
  _promise_id int,
  _amount float,
  _carrier text,
  _instructions text)
RETURNS int AS $$
DECLARE
  _order_id int;
  _title text;
  _unit text;
  _summary text;
  _epsilon float;
  _payee_id int;
  _pending_payments_amount float;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  --
  -- First: Pick an order ID.
  --
  _order_id := _generate_order_id(_recipient_id);

  IF _order_id IS NULL THEN
    RETURN 0;  -- invalid order ID

  END IF;

  --
  -- Second: If this is a payment, make sure the amount is actually
  -- available. A payment is a special kind of delivery order that has
  -- a valid trader ID in its "carrier" field.
  _payee_id := SUBSTRING(_carrier from '^[0-9]{9}$')::int;

  IF _payee_id IS NOT NULL THEN
    SELECT COALESCE(SUM(amount), 0.0) INTO _pending_payments_amount
    FROM delivery_order
    WHERE
      recipient_id=_recipient_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id AND
      carrier~'^[0-9]{9}$' AND
      is_active=TRUE AND
      issuer_message IS NULL;

    PERFORM 1
    FROM asset
    WHERE
      recipient_id=_recipient_id AND
      issuer_id=_issuer_id AND
      promise_id=_promise_id AND
      _amount <= amount - _pending_payments_amount;

    IF NOT FOUND THEN
      RETURN 0;  -- wrong amount

    END IF;

  END IF;

  --
  -- Third: Obtain the product information.
  --
  SELECT title, unit, summary, epsilon
  INTO _title, _unit, _summary, _epsilon
  FROM product
  WHERE issuer_id=_issuer_id AND promise_id=_promise_id;

  IF NOT FOUND THEN
    RETURN 0;  -- invalid product

  END IF;

  --
  -- Fourth: Insert the delivery order.
  --
  INSERT INTO delivery_status (recipient_id, order_id)
  VALUES (_recipient_id, _order_id);

  INSERT INTO delivery_description (
    recipient_id, order_id,
    issuer_id, promise_id, amount, carrier, instructions,
    title, unit, summary, epsilon)
  VALUES (
    _recipient_id, _order_id,
    _issuer_id, _promise_id, _amount, _carrier, _instructions,
    _title, _unit, _summary, _epsilon);

  IF _payee_id IS NOT NULL THEN
    PERFORM _opt_payment(_payee_id, _issuer_id, _promise_id, _recipient_id);

  END IF;

  RETURN _order_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION deactivate_delivery_order(
  _recipient_id int,
  _order_id int)
RETURNS timestamp with time zone AS $$
DECLARE
  _execution_ts timestamp with time zone;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  UPDATE delivery_status
  SET is_active=FALSE
  WHERE recipient_id=_recipient_id AND order_id=_order_id AND is_active=TRUE
  RETURNING execution_ts INTO _execution_ts;

  IF FOUND THEN
    PERFORM _cancel_delivery_automation(_recipient_id, _order_id);

  ELSE
    _execution_ts := NULL;

  END IF;
  
  RETURN _execution_ts;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION execute_delivery_order(
  _issuer_id int,
  _recipient_id int,
  _order_id int,
  _message text)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  PERFORM 1
  FROM delivery_description
  WHERE
    recipient_id=_recipient_id AND order_id=_order_id AND
    issuer_id=_issuer_id AND  -- Ensures that the issuer has been properly authenticated.
    carrier!~'^[0-9]{9}$';  -- Payments must not be executed "manually".

  IF FOUND THEN
    UPDATE delivery_status
    SET
      issuer_message=_message,
      execution_ts=CURRENT_TIMESTAMP,  -- A NULL here would mean "rejected"
      is_active=TRUE
    WHERE
      recipient_id=_recipient_id AND order_id=_order_id AND
      issuer_message IS NULL;

    IF FOUND THEN
      PERFORM _cancel_delivery_automation(_recipient_id, _order_id);

    END IF;

  END IF;

END;
$$
LANGUAGE plpgsql;


--
-- User login
--
CREATE OR REPLACE FUNCTION get_password_salt(
  _username text)
RETURNS text AS $$
DECLARE
  _password_salt text;
BEGIN
  SELECT trader.password_salt
  INTO _password_salt
  FROM trader
  WHERE trader.username_lowercase=LOWER(_username);

  IF FOUND THEN
    RETURN _password_salt;

  ELSE
    RETURN '';

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION login_trader(
  _username text,
  _password_hash crypt_hash,
  OUT needs_captcha boolean,
  OUT is_valid boolean,
  OUT trader_id int)
RETURNS SETOF record AS $$
DECLARE
  _trader_password_hash crypt_hash;
  _a_day_before_ts timestamp with time zone;
BEGIN
  SELECT trader.id, trader.password_hash
  INTO trader_id, _trader_password_hash
  FROM trader
  WHERE trader.username_lowercase=LOWER(_username);

  IF FOUND THEN
    IF _password_hash=_trader_password_hash THEN
      is_valid := TRUE;

    ELSE
      is_valid := FALSE;

    END IF;

    _a_day_before_ts := CURRENT_TIMESTAMP - interval '1 day';

    PERFORM 1
    FROM trader_status s
    WHERE
      s.trader_id=login_trader.trader_id AND
      s.max_login_count > 0 AND
      (s.last_bad_auth_ts < _a_day_before_ts OR s.bad_auth_count < 5)
    FOR UPDATE;  -- the lock prevents race-conditions

    IF FOUND THEN
      needs_captcha := FALSE;

      IF is_valid=TRUE THEN
        UPDATE trader_status
        SET
          bad_auth_count=0,
          max_login_count = max_login_count - 1
        WHERE trader_status.trader_id=login_trader.trader_id;

      ELSE
        UPDATE trader_status
        SET
          bad_auth_count = CASE WHEN last_bad_auth_ts < _a_day_before_ts THEN 0 ELSE bad_auth_count END + 1,
          last_bad_auth_ts = CURRENT_TIMESTAMP
        WHERE trader_status.trader_id=login_trader.trader_id;

      END IF;

    ELSE
      needs_captcha := TRUE;

    END IF;

  ELSE
    needs_captcha := FALSE;
    is_valid := FALSE;
    trader_id := 0;

  END IF;

  RETURN NEXT;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION report_login_captcha_success(
  _trader_id int)
RETURNS void AS $$
BEGIN
  UPDATE trader_status
  SET
    bad_auth_count=0,
    max_login_count = LEAST(1000, max_login_count + 30)
  WHERE trader_id=_trader_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION verify_email(
  _trader_id int,
  _email_verification_code text)
RETURNS boolean AS $$
DECLARE
  _email text;
BEGIN
  -- If someone ever changes the 1-month interval to something else,
  -- he should not forget to make appropriate change in the
  -- "find_failed_email_verification" function too.
  SELECT email INTO _email
  FROM email_verification
  WHERE
    trader_id=_trader_id AND 
    email_verification_code=_email_verification_code AND
    email_verification_code_ts + interval '1 month' > CURRENT_TIMESTAMP;

  IF FOUND THEN
    IF NOT EXISTS(SELECT 1 FROM verified_email WHERE trader_id=_trader_id AND email=_email) THEN
      <<infloop>>
      LOOP
        UPDATE verified_email
        SET
          email=_email,
          email_cancellation_code=_email_verification_code
        WHERE trader_id=_trader_id;
    
        EXIT infloop WHEN FOUND;
    
        BEGIN
          INSERT INTO verified_email (
            trader_id, email, email_cancellation_code)
          VALUES (
            _trader_id, _email, _email_verification_code);
    
          EXIT infloop;
    
        EXCEPTION WHEN unique_violation THEN
          NULL;
    
        END;
    
      END LOOP;

    END IF;
    
    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION cancel_email(
  _trader_id int,
  _email_cancellation_code text)
RETURNS boolean AS $$
DECLARE
  _email text;
BEGIN
  SELECT email INTO _email
  FROM verified_email
  WHERE
    trader_id=_trader_id AND
    email_cancellation_code=_email_cancellation_code
  FOR UPDATE;

  IF FOUND THEN
    DELETE FROM verified_email WHERE trader_id=_trader_id;

    -- In order to prevent users from switching their verification
    -- status on and off (a potential DoS attack), we should erase the
    -- verification code from the email-verification record.
    PERFORM update_email_verification_code(_trader_id, _email, '');

    RETURN TRUE;

  ELSE
    RETURN FALSE;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION find_failed_email_verification(
  _trader_id int)
RETURNS text AS $$
DECLARE
  _email text;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT p.email INTO _email
  FROM
    profile p
      LEFT OUTER JOIN verified_email v ON
        v.trader_id=p.trader_id
      LEFT OUTER JOIN email_verification u ON
        u.trader_id=p.trader_id AND
        (u.email_verification_code IS NULL OR u.email_verification_code <> '') AND
        COALESCE(u.email_verification_code_ts, CURRENT_TIMESTAMP) + interval '1 month' > CURRENT_TIMESTAMP
  WHERE
    p.trader_id=_trader_id AND
    p.email <> '' AND (v.email IS NULL OR v.email <> p.email) AND (u.email IS NULL OR u.email <> p.email)
  FOR UPDATE OF p;

  IF FOUND THEN
    UPDATE profile
    SET email=''
    WHERE trader_id=_trader_id;

    RETURN _email;

  ELSE
    RETURN NULL;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_email_verification(
  _trader_id int,
  OUT trader_id int,
  OUT email text,
  OUT email_verification_code text,
  OUT email_verification_code_ts timestamp with time zone)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    ev.trader_id,
    ev.email,
    ev.email_verification_code,
    ev.email_verification_code_ts
  FROM email_verification ev
  WHERE ev.trader_id=_trader_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_verified_email(
  _trader_id int,
  OUT trader_id int,
  OUT email text,
  OUT email_cancellation_code text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    ve.trader_id,
    ve.email,
    ve.email_cancellation_code
  FROM verified_email ve
  WHERE ve.trader_id=_trader_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_outgoing_email(
  _subject text,
  _content text,
  _orig_date timestamp with time zone,
  _from_mailbox text, 
  _from_display_name text,
  _to_mailbox text, 
  _to_display_name text,
  _reply_to_mailbox text,
  _reply_to_display_name text,
  _sender_mailbox text,
  _sender_display_name text)
RETURNS void AS $$
BEGIN
  INSERT INTO outgoing_email (
    subject, content, orig_date, from_mailbox, from_display_name, to_mailbox, to_display_name,
    reply_to_mailbox, reply_to_display_name, sender_mailbox, sender_display_name)
  VALUES (
    _subject, _content, _orig_date, _from_mailbox, _from_display_name, _to_mailbox, _to_display_name,
    _reply_to_mailbox, _reply_to_display_name, _sender_mailbox, _sender_display_name);

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_email_verification_code(
  _trader_id int,
  _email text,
  _email_verificaton_code text)
RETURNS boolean AS $$
BEGIN
  UPDATE email_verification
  SET
    email_verification_code=_email_verificaton_code,
    email_verification_code_ts=CURRENT_TIMESTAMP
  WHERE trader_id=_trader_id AND email=_email;

  RETURN FOUND;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION insert_outgoing_customer_broadcast(
  _trader_id int,
  _from_mailbox text, 
  _subject text,
  _content text)
RETURNS boolean AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  IF acquire_sent_email_rights(_trader_id) THEN
    INSERT INTO outgoing_customer_broadcast (
      trader_id, from_mailbox, subject, content)
    VALUES (
      _trader_id, _from_mailbox, _subject, _content);

    RETURN TRUE;

  END IF;

  RETURN FALSE;

END;
$$
LANGUAGE plpgsql;


--
-- Partners & profiles
--
CREATE OR REPLACE FUNCTION get_userinfo(
  _trader_id int,
  _language_code text,
  OUT trader_id int,
  OUT username text,
  OUT banned_until_ts timestamp with time zone,
  OUT has_profile boolean,
  OUT time_zone text,
  OUT accumulated_transaction_cost float,
  OUT unconfirmed_deal_count int,
  OUT unconfirmed_transaction_count int,
  OUT unconfirmed_receipt_count int,
  OUT next_turn_start_ts timestamp with time zone,
  OUT use_simplified_ui boolean,
  OUT offers_are_enabled boolean)
RETURNS SETOF record AS $$
DECLARE
  _last_recorded_activity_ts timestamp with time zone;
  _last_request_language_code text;
  _max_login_count int;
BEGIN
  SELECT solver.next_turn_start_ts INTO next_turn_start_ts
  FROM solver
  WHERE status=0;

  -- We do not want to put the database on load while a turn is
  -- running.  Also, users are better off with all requests being
  -- disabled rather than only part of them (otherwise, they would be
  -- angry an confused).  Therefore, if we detect that we are in the
  -- middle of a trading turn, we raise an exception, which will be
  -- reported to the user.
  IF NOT FOUND THEN
    RAISE EXCEPTION 'a turn is running';

  END IF;

  SELECT
    ts.trader_id, ts.username, tse.banned_until_ts, 
    ts.p_has_profile, ts.p_time_zone, ts.accumulated_transaction_cost,
    tse.p_unconfirmed_deal_count, tse.p_unconfirmed_transaction_count, tse.p_unconfirmed_receipt_count,
    ts.last_recorded_activity_ts, ts.last_request_language_code,
    ts.max_login_count,
    ts.use_simplified_ui,
    ts.offers_are_enabled
  INTO
    trader_id, username, banned_until_ts,
    has_profile, time_zone, accumulated_transaction_cost,
    unconfirmed_deal_count, unconfirmed_transaction_count, unconfirmed_receipt_count,
    _last_recorded_activity_ts, _last_request_language_code,
    _max_login_count,
    use_simplified_ui,
    offers_are_enabled
  FROM trader_status ts, trader_status_ext tse
  WHERE ts.trader_id=_trader_id AND tse.trader_id=_trader_id;
  -- Since this stored procedure is executed by virtually every
  -- request, we refrain from locking the record "FOR UPDATE", because
  -- this might negatively impact the performance, at least in theory.

  IF FOUND THEN
    -- We must know the last time when the user logged in.  We do not
    -- need to know it exactly, so we save us precious database
    -- transaction "flush"-es by updating the record only when we are
    -- off by more than a day.
    IF _last_recorded_activity_ts < CURRENT_TIMESTAMP - interval '1 day' AND banned_until_ts <= CURRENT_TIMESTAMP THEN
      UPDATE trader_status
      SET last_recorded_activity_ts = CURRENT_TIMESTAMP
      WHERE trader_status.trader_id=_trader_id;

    END IF;

    -- Since this stored procedure may and will be executed on
    -- GET-requests, which are hard to put a quota on, we use the
    -- login-seqnum quota so as to put a limit to the number of
    -- changes a user can make to his language preferences.  In
    -- theory, the limit can be exceeded by issuing a huge number of
    -- requests in parallel, but this should not be a problem in
    -- practice.
    IF _last_request_language_code <> _language_code AND _max_login_count > 0 THEN
      UPDATE trader_status
      SET
        last_request_language_code = _language_code,
        max_login_count = max_login_count - 1
      WHERE trader_status.trader_id=_trader_id;

    END IF;

    RETURN NEXT;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_image(
  _trader_id int,
  _photograph_id int,
  OUT trader_id int,
  OUT photograph_id int,
  OUT raw_content bytea,
  OUT insertion_ts timestamp with time zone)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    i.trader_id, 
    CAST(i.photograph_id AS int), i.raw_content, i.insertion_ts
  FROM image i
  WHERE
    i.trader_id=_trader_id AND
    i.photograph_id=_photograph_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_profile(
  _trader_id int,
  OUT trader_id int,
  OUT full_name text,
  OUT summary text,
  OUT country text,
  OUT postal_code text,
  OUT address text,
  OUT email text,
  OUT phone text,
  OUT fax text,
  OUT www text,
  OUT time_zone text,
  OUT photograph_id int,
  OUT advertise_trusted_partners boolean)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.trader_id,
    p.full_name, p.summary, p.country, p.postal_code, p.address,
    p.email, p.phone, p.fax, p.www, p.time_zone, p.photograph_id, p.advertise_trusted_partners
  FROM profile p
  WHERE p.trader_id=_trader_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_trust(
  _recipient_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT t.recipient_id, t.issuer_id, t.name, t.comment
  FROM trust t
  WHERE t.recipient_id=_recipient_id
  ORDER BY t.name ASC;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_trust(
  _recipient_id int,
  _issuer_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT t.recipient_id, t.issuer_id, t.name, t.comment
  FROM trust t
  WHERE
    t.recipient_id=_recipient_id AND
    t.issuer_id=_issuer_id;

END;
$$
LANGUAGE plpgsql;


--
-- Products
--
CREATE OR REPLACE FUNCTION get_product(
  _issuer_id int,
  _promise_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT description text,
  OUT insertion_ts timestamp with time zone)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.issuer_id, CAST(p.promise_id AS int),
    p.title, p.unit, p.summary, p.epsilon,
    p.description, p.insertion_ts
  FROM product p
  WHERE
    p.issuer_id=_issuer_id AND
    p.promise_id=_promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_product_offer(
  _issuer_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT price value,
  OUT amount float,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    o.issuer_id, o.promise_id,
    o.price, o.p_amount,
    p.title, p.unit, p.summary, p.epsilon
  FROM offer o, product p
  WHERE
    p.issuer_id=o.issuer_id AND
    p.promise_id=o.promise_id AND
    o.issuer_id=_issuer_id
  ORDER BY p.title, p.unit, o.promise_id;  -- This would be faster: ORDER BY o.promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_product_offer(
  _issuer_id int,
  _promise_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT price value,
  OUT amount float,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    o.issuer_id, o.promise_id,
    o.price, o.p_amount,
    p.title, p.unit, p.summary, p.epsilon
  FROM offer o, product p
  WHERE
    p.issuer_id=o.issuer_id AND
    p.promise_id=o.promise_id AND
    o.issuer_id=_issuer_id AND
    o.promise_id=_promise_id;

END;
$$
LANGUAGE plpgsql;


--
-- Deposits & shopping list
--
CREATE OR REPLACE FUNCTION get_deposit(
  _recipient_id int,
  _issuer_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.recipient_id, d.issuer_id, d.promise_id,
    d.amount,
    d.title, d.unit, d.summary, d.epsilon
  FROM deposit d
  WHERE
    d.recipient_id=_recipient_id AND
    d.issuer_id=_issuer_id
  ORDER BY d.title, d.unit, d.promise_id;  -- This would be faster: ORDER BY d.promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_deposit(
  _recipient_id int,
  _issuer_id int,
  _promise_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.recipient_id, d.issuer_id, d.promise_id,
    d.amount,
    d.title, d.unit, d.summary, d.epsilon
  FROM deposit d
  WHERE
    d.recipient_id=_recipient_id AND
    d.issuer_id=_issuer_id AND
    d.promise_id=_promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_deposit_avl_amount(
  _recipient_id int,
  _issuer_id int,
  _promise_id int)
RETURNS float AS $$
DECLARE
  _pending_payments_amount float;
  _deposited_amount float;
BEGIN
  SELECT COALESCE(SUM(amount), 0.0) INTO _pending_payments_amount
  FROM delivery_order
  WHERE
    recipient_id=_recipient_id AND
    issuer_id=_issuer_id AND
    promise_id=_promise_id AND
    carrier~'^[0-9]{9}$' AND
    is_active=TRUE AND
    issuer_message IS NULL;

  SELECT amount INTO _deposited_amount
  FROM asset
  WHERE
    recipient_id=_recipient_id AND
    issuer_id=_issuer_id AND
    promise_id=_promise_id;

  IF NOT FOUND THEN
    _deposited_amount := 0.0;

  END IF;

  RETURN _deposited_amount - _pending_payments_amount;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_product_deposit(
  _issuer_id int,
  _promise_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
DECLARE
  _deposit_count int;
BEGIN
  SELECT COUNT(*)
  FROM product_deposit d
  WHERE d.issuer_id=_issuer_id AND d.promise_id=_promise_id
  INTO _deposit_count;

  IF _deposit_count > 3000 THEN
    --
    -- We must return 2 rows. Here are the common fields:
    --
    issuer_id := _issuer_id;
    promise_id := _promise_id;
    name := NULL;
    comment := NULL;

    --
    -- The first row: the issuer itself.
    --
    recipient_id := _issuer_id;

    SELECT d.amount INTO amount
    FROM product_deposit d
    WHERE
      d.issuer_id=_issuer_id AND
      d.promise_id=_promise_id AND
      d.recipient_id=_issuer_id;
    amount := COALESCE(amount, 0.0);

    RETURN NEXT;

    --
    -- The second row: the aggregated others.
    --
    recipient_id := NULL;

    SELECT SUM(d.amount) INTO amount
    FROM product_deposit d
    WHERE
      d.issuer_id=_issuer_id AND
      d.promise_id=_promise_id AND
      d.recipient_id<>_issuer_id;
    amount := COALESCE(amount, 0.0);

    RETURN NEXT;

  ELSE
    RETURN QUERY
    SELECT
      d.recipient_id, d.issuer_id, d.promise_id,
      d.amount,
      t.name, t.comment
    FROM product_deposit d LEFT OUTER JOIN trust t ON
      t.recipient_id=d.issuer_id AND
      t.issuer_id=d.recipient_id
    WHERE
      d.issuer_id=_issuer_id AND
      d.promise_id=_promise_id
    ORDER BY d.recipient_id;

  END IF;
  
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_shopping_item(
  _recipient_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT have_amount float,
  OUT need_amount float,
  OUT issuer_price value,
  OUT recipient_price value,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    si.recipient_id, si.issuer_id, si.promise_id,
    si.have_amount, si.need_amount, si.issuer_price, si.recipient_price,
    si.title, si.unit, si.summary, si.epsilon,
    si.name, si.comment
  FROM shopping_item si
  WHERE si.recipient_id=_recipient_id
  ORDER BY si.name, si.title, si.unit, si.promise_id;  -- This would be faster: ORDER BY si.issuer_id, si.promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_shopping_item(
  _recipient_id int,
  _issuer_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT have_amount float,
  OUT need_amount float,
  OUT issuer_price value,
  OUT recipient_price value,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    si.recipient_id, si.issuer_id, si.promise_id,
    si.have_amount, si.need_amount, si.issuer_price, si.recipient_price,
    si.title, si.unit, si.summary, si.epsilon,
    si.name, si.comment
  FROM shopping_item si
  WHERE
    si.recipient_id=_recipient_id AND
    si.issuer_id=_issuer_id
  ORDER BY si.promise_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_shopping_item(
  _recipient_id int,
  _issuer_id int,
  _promise_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT have_amount float,
  OUT need_amount float,
  OUT issuer_price value,
  OUT recipient_price value,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    si.recipient_id, si.issuer_id, si.promise_id,
    si.have_amount, si.need_amount, si.issuer_price, si.recipient_price,
    si.title, si.unit, si.summary, si.epsilon,
    si.name, si.comment
  FROM shopping_item si
  WHERE
    si.recipient_id=_recipient_id AND
    si.issuer_id=_issuer_id AND
    si.promise_id=_promise_id;

END;
$$
LANGUAGE plpgsql;


--
-- Deals & transactions
--
CREATE OR REPLACE FUNCTION get_recent_deal(
  _recipient_id int,
  _from_ts timestamp with time zone,
  _to_ts timestamp with time zone,
  OUT turn_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT price value,
  OUT ts timestamp with time zone,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.turn_id, d.recipient_id, d.issuer_id, d.promise_id,
    d.amount, d.price, d.ts,
    d.title, d.unit, d.summary, d.epsilon,
    t.name, t.comment
  FROM mv_recent_deal d LEFT OUTER JOIN trust t ON
    t.recipient_id=d.recipient_id AND
    t.issuer_id=d.issuer_id
  WHERE
    d.recipient_id=_recipient_id AND
    _from_ts <= d.ts AND d.ts < _to_ts
  ORDER BY d.ts DESC;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_customer_recent_deal(
  _issuer_id int,
  _from_ts timestamp with time zone,
  _to_ts timestamp with time zone,
  OUT turn_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT price value,
  OUT ts timestamp with time zone,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.turn_id, d.recipient_id, d.issuer_id, d.promise_id,
    d.amount, d.price, d.ts,
    p.title, p.unit, p.summary, p.epsilon,
    t.name, t.comment
  FROM
    recent_deal d LEFT OUTER JOIN trust t ON
      t.recipient_id=d.issuer_id AND
      t.issuer_id=d.recipient_id,
    product p
  WHERE
    p.issuer_id=d.issuer_id AND
    p.promise_id=d.promise_id AND
    d.issuer_id=_issuer_id AND
    _from_ts <= d.ts AND d.ts < _to_ts
  ORDER BY d.ts DESC;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_recent_transaction(
  _recipient_id int,
  _issuer_id int,
  OUT issuer_id int,
  OUT handoff_id int,
  OUT recipient_id int,
  OUT promise_id int,
  OUT amount float,
  OUT reason text,
  OUT ts timestamp with time zone,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT is_a_payment boolean,
  OUT payment_payer_name text,
  OUT payment_reason text,
  OUT payment_payer_id int,
  OUT payment_order_id int,
  OUT payment_payee_id int)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    rt.issuer_id, CAST(rt.handoff_id AS int),
    rt.recipient_id, rt.promise_id,
    rt.amount, rt.reason, rt.ts,
    p.title, p.unit, p.summary, p.epsilon,
    rt.is_a_payment,
    rt.payment_payer_name, rt.payment_reason, 
    rt.payment_payer_id, rt.payment_order_id, rt.payment_payee_id
  FROM
    recent_transaction rt,
    product p
  WHERE
    p.issuer_id=rt.issuer_id AND
    p.promise_id=rt.promise_id AND
    rt.recipient_id=_recipient_id AND
    rt.issuer_id=_issuer_id
  ORDER BY rt.ts DESC;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_recent_nonpayment_transaction(
  _recipient_id int,
  _issuer_id int,
  OUT issuer_id int,
  OUT handoff_id int,
  OUT recipient_id int,
  OUT promise_id int,
  OUT amount float,
  OUT reason text,
  OUT ts timestamp with time zone,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    rt.issuer_id, CAST(rt.handoff_id AS int),
    rt.recipient_id, rt.promise_id,
    rt.amount, rt.reason, rt.ts,
    p.title, p.unit, p.summary, p.epsilon
  FROM
    recent_transaction rt,
    product p
  WHERE
    p.issuer_id=rt.issuer_id AND
    p.promise_id=rt.promise_id AND
    rt.recipient_id=_recipient_id AND
    rt.issuer_id=_issuer_id AND
    rt.is_a_payment=FALSE
  ORDER BY rt.ts DESC;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_unconfirmed_receipt(
  _issuer_id int,
  OUT issuer_id int,
  OUT handoff_id int,
  OUT recipient_id int,
  OUT promise_id int,
  OUT amount float,
  OUT reason text,
  OUT ts timestamp with time zone,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT 
    r.issuer_id, CAST(r.handoff_id AS int), 
    r.recipient_id,  r.promise_id,
    r.amount, r.reason, r.ts,
    p.title,
    p.unit,
    p.summary,
    p.epsilon,
    t.name, t.comment
  FROM
    unconfirmed_receipt r
      LEFT OUTER JOIN trust t ON
        t.recipient_id=r.issuer_id AND
        t.issuer_id=r.recipient_id,
    product p
  WHERE
    p.issuer_id=r.issuer_id AND
    p.promise_id=r.promise_id AND
    r.issuer_id=_issuer_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_unconfirmed_transaction(
  _recipient_id int,
  OUT id bigint,
  OUT issuer_id int,
  OUT handoff_id int,
  OUT recipient_id int,
  OUT promise_id int,
  OUT amount float,
  OUT reason text,
  OUT ts timestamp with time zone,
  OUT is_a_payment boolean,
  OUT payment_payer_name text,
  OUT payment_reason text,
  OUT payment_payer_id int,
  OUT payment_order_id int,
  OUT payment_payee_id int,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    ut.id, 
    ut.issuer_id, CAST(ut.handoff_id AS int),
    ut.recipient_id,  ut.promise_id, 
    ut.amount, ut.reason, ut.ts,
    ut.is_a_payment, ut.payment_payer_name, ut.payment_reason,
    ut.payment_payer_id, ut.payment_order_id, ut.payment_payee_id,
    ut.title,
    ut.unit,
    ut.summary,
    ut.epsilon,
    t.name, t.comment
  FROM
    unconfirmed_transaction ut,
    trust t
  WHERE
    t.recipient_id=ut.recipient_id AND
    t.issuer_id=ut.issuer_id AND
    ut.recipient_id=_recipient_id
  ORDER BY ut.ts DESC
  LIMIT 1000;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_unconfirmed_deal(
  _recipient_id int,
  OUT turn_id int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT price value,
  OUT ts timestamp with time zone,
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.turn_id, d.recipient_id, d.issuer_id, d.promise_id,
    d.amount, d.price, d.ts,
    d.title,
    d.unit,
    d.summary,
    d.epsilon,
    t.name, t.comment
  FROM
    unconfirmed_deal d LEFT OUTER JOIN trust t ON
      t.recipient_id=d.recipient_id AND
      t.issuer_id=d.issuer_id
  WHERE d.recipient_id=_recipient_id
  ORDER BY d.ts DESC
  LIMIT 1000;

END;
$$
LANGUAGE plpgsql;


--
-- Delivery orders
--
CREATE OR REPLACE FUNCTION get_active_delivery_order(
  _recipient_id int,
  OUT recipient_id int,
  OUT order_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT carrier text,
  OUT instructions text, 
  OUT insertion_ts timestamp with time zone, 
  OUT is_active boolean,
  OUT issuer_message text,
  OUT execution_ts timestamp with time zone, 
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text,
  OUT is_a_payment boolean,
  OUT payee_name text,
  OUT payee_comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    o.recipient_id, o.order_id,
    o.issuer_id, o.promise_id, o.amount, o.carrier, o.instructions, o.insertion_ts,
    o.is_active, o.issuer_message, o.execution_ts, 
    o.title, o.unit, o.summary, o.epsilon,
    t.name, t.comment,
    o.carrier~'^[0-9]{9}$', p.name, p.comment
  FROM
    delivery_order o
      LEFT OUTER JOIN trust t ON
        t.recipient_id=o.recipient_id AND
        t.issuer_id=o.issuer_id
      LEFT OUTER JOIN trust p ON
        p.recipient_id=o.recipient_id AND
        p.issuer_id=SUBSTRING(o.carrier, '^[0-9]{9}$')::int
  WHERE
    o.recipient_id=_recipient_id AND
    o.is_active=TRUE
  ORDER BY o.order_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_active_delivery_order(
  _recipient_id int,
  _order_id int,
  OUT recipient_id int,
  OUT order_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT carrier text,
  OUT instructions text, 
  OUT insertion_ts timestamp with time zone, 
  OUT is_active boolean,
  OUT issuer_message text,
  OUT execution_ts timestamp with time zone, 
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT name text,
  OUT comment text,
  OUT is_a_payment boolean,
  OUT payee_name text,
  OUT payee_comment text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    o.recipient_id, o.order_id,
    o.issuer_id, o.promise_id, o.amount, o.carrier, o.instructions, o.insertion_ts,
    o.is_active, o.issuer_message, o.execution_ts, 
    o.title, o.unit, o.summary, o.epsilon,
    t.name, t.comment,
    o.carrier~'^[0-9]{9}$', p.name, p.comment
  FROM
    delivery_order o
      LEFT OUTER JOIN trust t ON
        t.recipient_id=o.recipient_id AND
        t.issuer_id=o.issuer_id
      LEFT OUTER JOIN trust p ON
        p.recipient_id=o.recipient_id AND
        p.issuer_id=SUBSTRING(o.carrier, '^[0-9]{9}$')::int
  WHERE
    o.recipient_id=_recipient_id AND o.order_id=_order_id AND
    o.is_active=TRUE;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_customer_delivery_order(
  _issuer_id int,
  _recipient_id int,
  OUT recipient_id int,
  OUT order_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT carrier text,
  OUT instructions text, 
  OUT insertion_ts timestamp with time zone, 
  OUT is_active boolean,
  OUT issuer_message text,
  OUT execution_ts timestamp with time zone, 
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT is_a_payment boolean)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    o.recipient_id, o.order_id,
    o.issuer_id, o.promise_id, o.amount, o.carrier, o.instructions, o.insertion_ts,
    o.is_active, o.issuer_message, o.execution_ts, 
    o.title, o.unit, o.summary, o.epsilon,
    o.carrier~'^[0-9]{9}$'
  FROM delivery_order o
  WHERE
    o.recipient_id=_recipient_id AND
    o.issuer_id=_issuer_id
  ORDER BY o.order_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION review_customer_delivery_order(
  _issuer_id int,
  _recipient_id int,
  _order_id int,
  OUT recipient_id int,
  OUT order_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT carrier text,
  OUT instructions text, 
  OUT insertion_ts timestamp with time zone, 
  OUT is_active boolean,
  OUT issuer_message text,
  OUT execution_ts timestamp with time zone, 
  OUT title text,
  OUT unit text,
  OUT summary text,
  OUT epsilon float,
  OUT is_a_payment boolean)
RETURNS SETOF record AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT
    o.recipient_id, o.order_id,
    o.issuer_id, o.promise_id, o.amount, o.carrier, o.instructions, o.insertion_ts, 
    o.is_active, o.issuer_message, o.execution_ts, 
    o.title, o.unit, o.summary, o.epsilon,
    o.carrier~'^[0-9]{9}$'
  INTO
    recipient_id, order_id,
    issuer_id, promise_id, amount, carrier, instructions, insertion_ts, 
    is_active, issuer_message, execution_ts, 
    title, unit, summary, epsilon,
    is_a_payment
  FROM delivery_order o
  WHERE
    o.recipient_id=_recipient_id AND o.order_id=_order_id AND
    o.issuer_id=_issuer_id;

  IF FOUND THEN
    RETURN NEXT;

    UPDATE delivery_status
    SET last_issuer_review_ts = CURRENT_TIMESTAMP
    WHERE
      delivery_status.recipient_id=_recipient_id AND
      delivery_status.order_id=_order_id AND (
        delivery_status.last_issuer_review_ts IS NULL
        OR delivery_status.last_issuer_review_ts < CURRENT_TIMESTAMP - interval '3 hours'
      );

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_pending_payment(
  _payee_id int,
  _issuer_id int,
  _promise_id int,
  OUT payer_id int,
  OUT order_id int,
  OUT payee_id int,
  OUT issuer_id int,
  OUT promise_id int,
  OUT amount float,
  OUT reason text, 
  OUT payer_name text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    o.payer_id, o.order_id,
    o.payee_id, o.p_issuer_id, o.p_promise_id, o.p_amount, 
    o.reason, o.p_payer_name
  FROM delivery_automation o
  WHERE
    o.payee_id=_payee_id AND
    o.p_issuer_id=_issuer_id AND
    o.p_promise_id=_promise_id
  ORDER BY o.p_amount DESC
  LIMIT 10;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION accept_payment(
  _payment_payee_id int,
  _payment_payer_id int,
  _payment_order_id int)
RETURNS int AS $$
DECLARE
  _issuer_id int;
  _promise_id int;
  _amount float;
  _payment_payer_name text;
  _payment_reason text;
  _withdrawal_is_ok boolean;
BEGIN
  PERFORM _ensure_no_turn_is_running();

  SELECT a.p_issuer_id, a.p_promise_id, a.p_amount, a.p_payer_name, a.reason
  INTO _issuer_id, _promise_id, _amount, _payment_payer_name, _payment_reason
  FROM
    delivery_automation a,
    profile p,
    delivery_status s
  WHERE
    a.payer_id=_payment_payer_id AND
    a.order_id=_payment_order_id AND
    a.payee_id=_payment_payee_id AND
    p.trader_id=a.payee_id AND
    s.recipient_id=a.payer_id AND
    s.order_id=a.order_id AND
    s.is_active=TRUE AND
    s.issuer_message IS NULL
  FOR UPDATE OF s, a;  -- we join the "profile", so as to ensure that the payee_id is valid.

  IF FOUND THEN
    PERFORM 1
    FROM offer
    WHERE
      issuer_id=_issuer_id AND
      promise_id=_promise_id AND
      price IS NOT NULL AND
      payments_are_enabled=TRUE
    FOR SHARE;

    IF NOT FOUND THEN
      RETURN 3;  -- Payments have been disabled.

    END IF;

    _withdrawal_is_ok := insert_transaction(
      _issuer_id, _payment_payer_id, _promise_id, (- _amount), '', TRUE,
      _payment_payer_name, _payment_reason, _payment_payer_id,
      _payment_order_id, _payment_payee_id);

    IF _withdrawal_is_ok THEN
      PERFORM insert_transaction(
        _issuer_id, _payment_payee_id, _promise_id, _amount, '', TRUE,
        _payment_payer_name, _payment_reason, _payment_payer_id, 
        _payment_order_id, _payment_payee_id);

    END IF;

    UPDATE delivery_status
    SET
      issuer_message='',
      execution_ts=(CASE WHEN _withdrawal_is_ok THEN CURRENT_TIMESTAMP ELSE NULL END)
    WHERE
      recipient_id=_payment_payer_id AND
      order_id=_payment_order_id;

    PERFORM _cancel_delivery_automation(_payment_payer_id, _payment_order_id);

    IF _withdrawal_is_ok THEN
      -- We update the last_recorded_indirect_activity_ts field for
      -- the issuer, because we do not want to kill a user that do not
      -- log in, but still continues to route payments between his/her
      -- customers.
      UPDATE trader_status_ext
      SET last_recorded_indirect_activity_ts = CURRENT_TIMESTAMP
      WHERE trader_id=_issuer_id AND last_recorded_indirect_activity_ts <= CURRENT_TIMESTAMP - INTERVAL '1 day';

      RETURN 0;

    ELSE
      RETURN 1;

    END IF;

  END IF;

  RETURN 2;  -- The payment has been canceled.

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION _html_escape(s text) RETURNS text AS $$
BEGIN
  RETURN replace(replace(replace(replace(replace(s, '&', '&amp;'), '<', '&lt;'), '>', '&gt;'), '"', '&quot;'), '''', '&#39;');

END;
$$
LANGUAGE plpgsql; 


CREATE OR REPLACE FUNCTION get_trust_match(
  _recipient_id int,
  _query_text text,
  _pages_to_skip int,
  OUT recipient_id int,
  OUT issuer_id int,
  OUT name text,
  OUT comment text)
RETURNS SETOF record AS $$
DECLARE
  _query tsquery;
  _items_on_page int;
  _items_to_skip int;
BEGIN
  _query := plainto_tsquery(_query_text);

  _items_on_page := 10;

  _items_to_skip := (_items_on_page * GREATEST(_pages_to_skip, 0));

  IF numnode(_query)=0 THEN
    RETURN QUERY
    SELECT
      tt.recipient_id,
      tt.issuer_id,
      _html_escape(tt.name),
      _html_escape(tt.comment)
    FROM (
      SELECT t.recipient_id, t.issuer_id, t.name, t.comment
      FROM trust t
      WHERE t.recipient_id=_recipient_id
      ORDER BY t.insertion_ts DESC
      LIMIT _items_on_page OFFSET _items_to_skip
    ) AS tt;

  ELSE
    RETURN QUERY
    SELECT
      tt.recipient_id,
      tt.issuer_id,
      ts_headline(_html_escape(tt.name), _query, 'HighlightAll=TRUE'),
      ts_headline(_html_escape(tt.comment), _query, 'HighlightAll=TRUE')
    FROM (
      SELECT t.recipient_id, t.issuer_id, t.name, t.comment
      FROM trust t
      WHERE t.recipient_id=_recipient_id AND t.p_tsvector @@ _query
      ORDER BY ts_rank_cd(t.p_tsvector, _query) DESC, t.insertion_ts DESC
      LIMIT _items_on_page OFFSET _items_to_skip
    ) AS tt;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_trust_match_count(
  _recipient_id int,
  _query_text text,
  OUT number_of_items int,
  OUT number_of_pages int,
  OUT number_of_items_per_page int)
RETURNS SETOF record AS $$
DECLARE
  _query tsquery;
BEGIN
  _query := plainto_tsquery(_query_text);

  number_of_items_per_page := 10;

  IF numnode(_query)=0 THEN
    SELECT COUNT(*) INTO number_of_items
    FROM trust 
    WHERE recipient_id=_recipient_id;

  ELSE
    SELECT COUNT(*) INTO number_of_items
    FROM trust 
    WHERE recipient_id=_recipient_id AND p_tsvector @@ _query;

  END IF;

  number_of_pages := number_of_items / number_of_items_per_page + CASE WHEN number_of_items % number_of_items_per_page > 0 THEN 1 ELSE 0 END;

  RETURN NEXT;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_outgoing_email(
  _id int)
RETURNS boolean AS $$
BEGIN
  DELETE FROM outgoing_email WHERE id=_id;

  RETURN FOUND;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_broadcast_recipient(
  _issuer_id int,
  OUT trader_id int,
  OUT mailbox text,
  OUT issuer_display_name text,
  OUT last_request_language_code text,
  OUT email_cancellation_code text)
RETURNS SETOF record AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.recipient_id,
    e.email,
    t.name,
    ts.last_request_language_code,
    e.email_cancellation_code
  FROM trust t, verified_email e, trader_status ts
  WHERE
    t.issuer_id=_issuer_id AND
    e.trader_id=t.recipient_id AND
    ts.trader_id=t.recipient_id AND
    ts.max_received_email_count > 0;
  
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_outgoing_customer_broadcast(
  _id bigint)
RETURNS boolean AS $$
BEGIN
  DELETE FROM outgoing_customer_broadcast WHERE id=_id;

  RETURN FOUND;
  
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_outgoing_notification(
  _id int)
RETURNS boolean AS $$
BEGIN
  DELETE FROM outgoing_notification WHERE id=_id;

  RETURN FOUND;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_loginkey_trader_id(
  _secret_md5 text)
RETURNS int AS $$
DECLARE _trader_id int;
BEGIN
  SELECT trader_id INTO _trader_id
  FROM loginkey
  WHERE
    secret_md5=_secret_md5 AND
    last_recorded_use_ts > CURRENT_TIMESTAMP - interval '1 month';

  IF FOUND THEN
    UPDATE loginkey
    SET last_recorded_use_ts=CURRENT_TIMESTAMP
    WHERE 
      secret_md5=_secret_md5 AND
      trader_id=_trader_id AND
      last_recorded_use_ts <= CURRENT_TIMESTAMP - interval '1 day';

    RETURN _trader_id;

  ELSE
    RETURN 0;

  END IF;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION replace_loginkey(
  _trader_id int,
  _secret_md5 text)
RETURNS boolean AS $$
BEGIN
  UPDATE loginkey
  SET
    secret_md5=_secret_md5,
    creation_ts=CURRENT_TIMESTAMP,
    last_recorded_use_ts=CURRENT_TIMESTAMP
  WHERE trader_id=_trader_id;

  IF NOT FOUND THEN
    INSERT INTO loginkey (secret_md5, trader_id)
    VALUES (_secret_md5, _trader_id);

  END IF;

  RETURN TRUE;

EXCEPTION WHEN unique_violation THEN
  RETURN FALSE;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_loginkey(
  _trader_id int)
RETURNS void AS $$
BEGIN
  DELETE FROM loginkey
  WHERE trader_id=_trader_id;

END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION update_solver_schedule(
  _next_turn_start_ts timestamp with time zone,
  _period_seconds int)
RETURNS void AS $$
BEGIN
  PERFORM _ensure_no_turn_is_running();

  UPDATE solver
  SET 
    next_turn_start_ts = _next_turn_start_ts,
    turn_interval = CAST(_period_seconds || ' seconds' AS interval);

END;
$$
LANGUAGE plpgsql;
