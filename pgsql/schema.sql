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
-- This file contains code defining the database schema for the
-- CMB web application.
--

DROP DOMAIN IF EXISTS crypt_hash CASCADE;
DROP DOMAIN IF EXISTS value CASCADE;
DROP DOMAIN IF EXISTS seqnum CASCADE;
DROP TABLE IF EXISTS solver CASCADE;
DROP TABLE IF EXISTS turn CASCADE;
DROP TABLE IF EXISTS trader CASCADE;
DROP TABLE IF EXISTS trader_status CASCADE;
DROP TABLE IF EXISTS profile CASCADE;
DROP TABLE IF EXISTS image CASCADE;
DROP TABLE IF EXISTS trust CASCADE;
DROP TABLE IF EXISTS product CASCADE;
DROP TABLE IF EXISTS bid CASCADE;
DROP TABLE IF EXISTS bid_product CASCADE;
DROP TABLE IF EXISTS offer CASCADE;
DROP TABLE IF EXISTS offer_removal CASCADE;
DROP TABLE IF EXISTS asset CASCADE;
DROP TABLE IF EXISTS recent_transaction CASCADE;
DROP TABLE IF EXISTS unconfirmed_transaction CASCADE;
DROP TABLE IF EXISTS recent_deal CASCADE;
DROP TABLE IF EXISTS unconfirmed_deal CASCADE;
DROP TABLE IF EXISTS unconfirmed_receipt CASCADE;
DROP TABLE IF EXISTS delivery_status CASCADE;
DROP TABLE IF EXISTS delivery_description CASCADE;
DROP TABLE IF EXISTS delivery_automation CASCADE;
DROP TABLE IF EXISTS loginkey CASCADE;
DROP TABLE IF EXISTS whitelist_entry CASCADE;


-- Base64 over SHA-256 (URL-safe).
CREATE DOMAIN crypt_hash AS char(44);

-- A measure of abstract value.
CREATE DOMAIN value AS decimal(15,2);

-- A sequence number
CREATE DOMAIN seqnum AS int CHECK (VALUE BETWEEN 1 AND 999999999);

-- Global solver parameters.
CREATE TABLE solver (
  is_unique boolean PRIMARY KEY CHECK (is_unique=TRUE),
  status int NOT NULL CHECK (status >= 0),  -- 0: serving users; 1: performing turn
  turn_interval interval NOT NULL CHECK (turn_interval >= interval '1 second'),
  next_turn_start_ts timestamp with time zone NOT NULL
);
INSERT INTO solver (
  is_unique, status, turn_interval, next_turn_start_ts)
VALUES (
  TRUE, 0, interval '1 day', 'tomorrow'::timestamp with time zone + interval '2 hours');

-- Signifies a successfully executed trading turn.
CREATE TABLE turn (
  id serial PRIMARY KEY CHECK (id > 0),
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Signifies a registered user. 
--
-- Once assigned to a given user an "id" must not be reassigned to
-- another user.
CREATE TABLE trader (
  id seqnum PRIMARY KEY,
  username_lowercase text NOT NULL UNIQUE,  -- the lower-cased username 
  password_hash crypt_hash NOT NULL,  -- the hashed, salted password
  password_salt text NOT NULL DEFAULT '',  -- prepended to the password before hashing
  registration_key text UNIQUE,
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- The following two tables signify status information about a given
-- registered user.  A record must be inserted in these tables during
-- users' signup.
--
-- Tables are split in order to avoid the long-running transactions
-- (the solver) from locking the "trader_status" table for update,
-- thus delaying some user requests.
--
--  The fields "p_has_profile", "p_time_zone",
-- "p_unconfirmed_receipt_count", "p_unconfirmed_transaction_count",
-- "p_unconfirmed_deal_count" are added merely for performance reasons
-- and do not contain independent data.
CREATE TABLE trader_status (
  trader_id int NOT NULL REFERENCES trader,
  username text NOT NULL,
  last_bad_auth_ts timestamp with time zone NOT NULL DEFAULT '1900-01-01',
  bad_auth_count int NOT NULL CHECK (bad_auth_count >= 0) DEFAULT 0,
  use_simplified_ui boolean NOT NULL DEFAULT FALSE,
  offers_are_enabled boolean NOT NULL DEFAULT TRUE,
  last_limits_update_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_recorded_activity_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_generated_photograph_id seqnum,  max_generated_photograph_id seqnum NOT NULL DEFAULT 100,
  last_generated_promise_id seqnum,  max_generated_promise_id seqnum NOT NULL DEFAULT 200,
  last_generated_handoff_id seqnum,  max_generated_handoff_id seqnum NOT NULL DEFAULT 3000,
  last_generated_order_id seqnum,  max_generated_order_id seqnum NOT NULL DEFAULT 1000,
  max_email_verification_count int NOT NULL DEFAULT 5,
  max_sent_email_count int NOT NULL DEFAULT 10,
  max_received_email_count int NOT NULL DEFAULT 1000,
  max_login_count int NOT NULL DEFAULT 1000,
  accumulated_transaction_cost float NOT NULL DEFAULT 0.0,
  last_request_language_code text NOT NULL DEFAULT 'en',
  p_has_profile boolean NOT NULL DEFAULT FALSE,
  p_time_zone text NOT NULL DEFAULT '',
  PRIMARY KEY (trader_id) WITH (FILLFACTOR=75)
);

CREATE TABLE trader_status_ext (
  trader_id int NOT NULL REFERENCES trader_status,
  banned_until_ts timestamp with time zone NOT NULL DEFAULT '1900-01-01',
  last_event_ts timestamp with time zone NOT NULL DEFAULT '1900-01-01',
  last_event_notification_ts timestamp with time zone NOT NULL DEFAULT '1900-01-01',
  last_recorded_indirect_activity_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  p_unconfirmed_receipt_count int NOT NULL DEFAULT 0,
  p_unconfirmed_transaction_count int NOT NULL DEFAULT 0,
  p_unconfirmed_deal_count int NOT NULL DEFAULT 0,
  PRIMARY KEY (trader_id) WITH (FILLFACTOR=75)
);

-- Signifies a photograph uploaded by an user.
--
--  Once assigned to a given photograph, the pair ("trader_id",
-- "photograph_id") should not be reassigned to another photograph.
CREATE TABLE image (
  trader_id int NOT NULL REFERENCES trader_status,
  photograph_id seqnum NOT NULL,
  raw_content bytea NOT NULL,  -- JPEG file stream
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (trader_id, photograph_id)
);

-- Signifies personal information about a given trader, which is
-- supplied by the trader itself.  A record should be inserted in this
-- table during users' signup, or otherwise there is almost nothing
-- that the user can do in the system.
CREATE TABLE profile (
  trader_id int NOT NULL REFERENCES trader_status,
  full_name text NOT NULL,
  summary text NOT NULL,
  country text NOT NULL,
  postal_code text NOT NULL,
  address text NOT NULL,
  email text NOT NULL,
  phone text NOT NULL,
  fax text NOT NULL,
  www text NOT NULL,
  time_zone text NOT NULL,  -- pytz time zone name.
  photograph_id int,
  advertise_trusted_partners boolean NOT NULL DEFAULT FALSE,  -- whether other traders can view this trader's partners.
  FOREIGN KEY (trader_id, photograph_id) REFERENCES image,
  PRIMARY KEY (trader_id)
);

-- Signifies the current status of an email-verification procedure.
CREATE TABLE email_verification (
  trader_id int NOT NULL REFERENCES trader_status,
  email text NOT NULL,
  email_verification_code text,  -- a NULL here means that a verification email needs to be sent to "email".
  email_verification_code_ts timestamp with time zone,
  CONSTRAINT must_have_verification_code_ts CHECK (email_verification_code_ts IS NOT NULL OR email_verification_code IS NULL),
  PRIMARY KEY (trader_id)
);
CREATE INDEX email_verification_idx ON email_verification (trader_id) WHERE email_verification_code IS NULL;

-- Signifies a successfully verified email address.
CREATE TABLE verified_email (
  trader_id int NOT NULL REFERENCES trader_status,
  email text NOT NULL,
  email_cancellation_code text NOT NULL,
  PRIMARY KEY (trader_id)
);

-- Signifies that a recipient trusts a given issuer (We are talking
-- about recipients and issuers of promises to deliver goods or
-- services).  Each recipient maintains a list of trusted issuers.
CREATE TABLE trust (
  recipient_id int NOT NULL REFERENCES profile,
  issuer_id int NOT NULL REFERENCES profile,
  name text NOT NULL,  -- An alias of the issuer (for recipient's convenience)
  comment text NOT NULL,  -- A short description of the issuer (for recipient's convenience)
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tsearch_config regconfig NOT NULL DEFAULT get_current_ts_config(),  -- Tsearch-configuration to be used.
  p_tsvector tsvector NOT NULL,  -- The pre-calculated tsvector for the columns "name" and "comment".
  CONSTRAINT forbid_self_trust CHECK (recipient_id != issuer_id),
  CONSTRAINT unique_trust_name UNIQUE (recipient_id, name),
  PRIMARY KEY (recipient_id, issuer_id) WITH (FILLFACTOR=90)
)
WITH (FILLFACTOR=90);
CREATE INDEX trust_issuer_id_idx ON trust (issuer_id);
CREATE INDEX trust_insertion_ts_idx ON trust (recipient_id, insertion_ts);
CLUSTER trust USING unique_trust_name;

-- Signifies a product defined by a trader.  The trader's ID is given
-- by the "issuer_id" field.  "epsilon" determines the greatest amount
-- of the product that may normally be neglected.  The "summary" holds
-- for a short description, while "description" is for a more detailed
-- one.  "unit" determines the unit of measurement.  
--
-- Once assigned to a given product, the pair ("issuer_id",
-- "promise_id") should not be reassigned to a different product.
CREATE TABLE product (
  issuer_id int NOT NULL REFERENCES profile,
  promise_id seqnum NOT NULL,
  title text NOT NULL,
  summary text NOT NULL,
  description text NOT NULL,
  unit text NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (issuer_id, promise_id)
);
CLUSTER product USING product_pkey;

-- Signifies that a recipient wants to receive a delivery promise for
-- some amount of goods or services from a given issuer, and he/she is
-- willing to pay the specified maximal price.  If the declared amount
-- is negative, the record signifies that the recipient wants to sell
-- a received delivery promise back (in which case "price" determines
-- the *minimal* price that the recipient is willing to accept). 
--
-- The fields "p_unconfirmed_transaction_amount" and
-- "p_unconfirmed_deal_amount" are added merely for performance
-- reasons and do not contain independent data.
CREATE TABLE bid (
  recipient_id int NOT NULL REFERENCES profile,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  amount float NOT NULL DEFAULT 0.0,
  price value CHECK (price IS NULL OR price >= 0),  -- If "price" is NULL, the bid is void.
  p_unconfirmed_transaction_amount float NOT NULL,
  p_unconfirmed_deal_amount float NOT NULL,
  FOREIGN KEY (recipient_id, issuer_id) REFERENCES trust ON DELETE CASCADE,
  PRIMARY KEY (recipient_id, issuer_id, promise_id) WITH (FILLFACTOR=75)
)
WITH (FILLFACTOR=75);
CLUSTER bid USING bid_pkey;

-- Signifies product summary for a product belonging to users'
-- shopping list.
--
-- Tables "bid" and "bid_product" constitute one object, but are kept
-- separated for performance reasons.
CREATE TABLE bid_product (
  recipient_id int NOT NULL,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  title text NOT NULL,
  unit text NOT NULL,
  summary text NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),
  FOREIGN KEY (recipient_id, issuer_id, promise_id) REFERENCES bid ON DELETE CASCADE,
  PRIMARY KEY (recipient_id, issuer_id, promise_id)
);
CLUSTER bid_product USING bid_product_pkey;

-- Signifies that an issuer is willing to accept the stated price for
-- his/her promise to deliver specific goods or services.  It also
-- implies that the issuer is willing to accept sellbacks for his/her
-- promises, at the stated price. 
--
-- The fields "p_amount" and "p_epsilon" are added merely for
-- performance reasons and does not contain independent data.
CREATE TABLE offer (
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  price value CHECK (price IS NULL OR price > 0),  -- If "price" is NULL, the offer is void.
  payments_are_enabled boolean NOT NULL DEFAULT TRUE,  -- allows automated deliveries among customers
  p_amount float NOT NULL,  -- holds the aggregate deposited amount
  p_epsilon float NOT NULL,
  FOREIGN KEY (issuer_id, promise_id) REFERENCES product ON DELETE CASCADE,
  PRIMARY KEY (issuer_id, promise_id) WITH (FILLFACTOR=75)
)
WITH (FILLFACTOR=75);
CLUSTER offer USING offer_pkey;

-- Signifies that an offer has been removed (see the previous
-- comment).
CREATE TABLE offer_removal (
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (issuer_id, promise_id) REFERENCES product ON DELETE CASCADE,
  PRIMARY KEY (issuer_id, promise_id)
);

-- Signifies an aggregated indebtedness of a given issuer to a given
-- recipient.
CREATE TABLE asset (
  recipient_id int NOT NULL REFERENCES profile,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  amount float NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),  -- an amount that can be considered negligible
  last_change_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (issuer_id, promise_id) REFERENCES product ON DELETE CASCADE,
  PRIMARY KEY (issuer_id, promise_id, recipient_id) WITH (FILLFACTOR=75)
)
WITH (FILLFACTOR=75);
CLUSTER asset USING asset_pkey;

-- Signifies that the stated amount of particular goods or services
-- has recently changed hands.  If the stated amount is positive, the
-- record signifies that the recipient have recently delivered the
-- stated amount of goods or services to the issuer, with the intent
-- to store them or to resell them to other traders.  A negative
-- amount indicates that the recipient have withdrawn goods from
-- his/her account at the issuer.  The "reason" field contains an
-- explanatory text about the transaction, supplied by the issuer.
CREATE TABLE recent_transaction (
  issuer_id int NOT NULL,
  handoff_id seqnum NOT NULL,
  recipient_id int NOT NULL REFERENCES profile,
  promise_id int NOT NULL,
  amount float NOT NULL,
  reason text NOT NULL,
  ts timestamp with time zone NOT NULL,
  is_a_payment boolean NOT NULL DEFAULT FALSE,
  payment_payer_name text,  -- contains payer's full name if it is a payment
  payment_reason text,  -- contains the payment reason if it is a payment
  payment_payer_id int,  -- contains payer's trader ID if it is a payment
  payment_order_id int,  -- contains payer's delivery order number if it is a payment
  payment_payee_id int,  -- contains payee's trader ID if it is a payment
  CONSTRAINT rt_must_supply_payment_details CHECK (is_a_payment=FALSE OR (
    payment_payer_name IS NOT NULL AND
    payment_reason IS NOT NULL AND
    payment_payer_id IS NOT NULL AND
    payment_order_id IS NOT NULL AND
    payment_payee_id IS NOT NULL)),
  FOREIGN KEY (issuer_id, promise_id) REFERENCES product ON DELETE CASCADE,
  PRIMARY KEY (issuer_id, handoff_id)
);
CREATE INDEX recent_transaction_ts_idx ON recent_transaction (issuer_id, recipient_id, ts);
CLUSTER recent_transaction USING recent_transaction_ts_idx;

-- Signifies an executed transaction that has not been confirmed by
-- the recipient (see comment for "recent_transaction").
CREATE TABLE unconfirmed_transaction (
  id bigserial PRIMARY KEY CHECK (id > 0),
  issuer_id int NOT NULL,
  handoff_id seqnum NOT NULL,
  recipient_id int NOT NULL REFERENCES profile,
  promise_id int NOT NULL,
  amount float NOT NULL,
  reason text NOT NULL,
  ts timestamp with time zone NOT NULL,
  title text NOT NULL,
  unit text NOT NULL,
  summary text NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),
  is_a_payment boolean NOT NULL DEFAULT FALSE,
  payment_payer_name text,
  payment_reason text,
  payment_payer_id int,
  payment_order_id int,
  payment_payee_id int,
  CONSTRAINT ut_must_supply_payment_details CHECK (is_a_payment=FALSE OR (
    payment_payer_name IS NOT NULL AND
    payment_reason IS NOT NULL AND
    payment_payer_id IS NOT NULL AND
    payment_order_id IS NOT NULL AND
    payment_payee_id IS NOT NULL)),
  FOREIGN KEY (recipient_id, issuer_id, promise_id) REFERENCES bid ON DELETE CASCADE
);
CREATE INDEX unconfirmed_transaction_recipient_idx ON unconfirmed_transaction (recipient_id, ts);
CLUSTER unconfirmed_transaction USING unconfirmed_transaction_recipient_idx;

-- Signifies that a issuer have been obligated with a certain amount
-- of goods to a recipient as a result of a given trading turn.  A
-- negative "amount" indicates instead, that the recipient have sold
-- back his/her previously obtained amounts.  
CREATE TABLE recent_deal (
  turn_id int NOT NULL REFERENCES turn,
  recipient_id int NOT NULL REFERENCES profile,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  amount float NOT NULL,
  price value NOT NULL,  -- the price at which the deal has been committed
  ts timestamp with time zone NOT NULL,
  FOREIGN KEY (issuer_id, promise_id) REFERENCES product ON DELETE CASCADE,
  PRIMARY KEY (recipient_id, issuer_id, promise_id, turn_id)
);
CREATE INDEX recent_deal_ts_idx ON recent_deal (issuer_id, ts);
CLUSTER recent_deal USING recent_deal_ts_idx;

-- Signifies an executed deal that has not been confirmed by the
-- recipient (see the comment for "recent_deal").
CREATE TABLE unconfirmed_deal (
  turn_id int NOT NULL REFERENCES turn,
  recipient_id int NOT NULL REFERENCES profile,
  issuer_id int NOT NULL REFERENCES profile,
  promise_id int NOT NULL,
  amount float NOT NULL,
  price value NOT NULL,
  ts timestamp with time zone NOT NULL,
  title text NOT NULL,
  unit text NOT NULL,
  summary text NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),
  PRIMARY KEY (recipient_id, issuer_id, promise_id, turn_id)
);
CREATE INDEX unconfirmed_deal_recipient_idx ON unconfirmed_deal (recipient_id, ts);
CLUSTER unconfirmed_deal USING unconfirmed_deal_recipient_idx;

-- Signifies an executed transaction (see the comment for
-- "recent_transaction") that needs to be confirmed by the issuer.
--
-- Once assigned to a given receipt, the tuple ("issuer_id",
-- "handoff_id") should not be reassigned to a different receipt.
CREATE TABLE unconfirmed_receipt (
  issuer_id int NOT NULL,
  handoff_id seqnum NOT NULL,
  recipient_id int NOT NULL REFERENCES profile,
  promise_id int NOT NULL,
  amount float NOT NULL,
  reason text NOT NULL,
  ts timestamp with time zone NOT NULL,
  FOREIGN KEY (issuer_id, promise_id) REFERENCES product ON DELETE CASCADE,
  PRIMARY KEY (issuer_id, handoff_id)
);
CLUSTER unconfirmed_receipt USING unconfirmed_receipt_pkey;

-- Signifies a delivery order status (see the "delivery_description"
-- table also).
--
-- Once assigned to a delivery order, the pair ("recipient_id",
-- "order_id") should not be reassigned to a different order.
CREATE TABLE delivery_status (
  recipient_id int NOT NULL REFERENCES profile,
  order_id seqnum NOT NULL,
  is_active boolean NOT NULL DEFAULT TRUE,
  last_issuer_review_ts timestamp with time zone,
  issuer_message text,  -- completion message from the trader who should execute the order
  execution_ts timestamp with time zone,  -- NOT NULL indicates a successful completion
  CONSTRAINT must_leave_message CHECK (issuer_message IS NOT NULL OR execution_ts IS NULL),
  PRIMARY KEY (recipient_id, order_id)
)
WITH (FILLFACTOR=66);
CLUSTER delivery_status USING delivery_status_pkey;

-- Signifies a delivery order description.
--
-- Tables "delivery_description" and "delivery_status" constitute one
-- object, but are kept separated for performance reasons.
CREATE TABLE delivery_description (
  recipient_id int NOT NULL,  -- the owner of the goods
  order_id int NOT NULL,
  issuer_id int NOT NULL REFERENCES profile,
  promise_id int NOT NULL,
  amount float NOT NULL CHECK (amount >= 0.0),
  carrier text NOT NULL,  -- the recipient of the goods
  instructions text NOT NULL,  -- the delivery instructions
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title text NOT NULL,
  unit text NOT NULL,
  summary text NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),
  FOREIGN KEY (recipient_id, order_id) REFERENCES delivery_status ON DELETE CASCADE,
  PRIMARY KEY (recipient_id, order_id)
);
CLUSTER delivery_description USING delivery_description_pkey;

-- Signifies that according to a given delivery order ("payer_id",
-- "order_id"), one trader ("payee_id") is authorized to receive some
-- amount of product from another trader ("payer_id"). This kind of
-- automated delivery is called a "payment".
CREATE TABLE delivery_automation (
  payer_id int NOT NULL,
  order_id int NOT NULL,
  payee_id int NOT NULL,
  reason text NOT NULL,  -- payment initiation reason
  p_issuer_id int NOT NULL,
  p_promise_id int NOT NULL,
  p_amount float NOT NULL CHECK (p_amount >= 0.0),
  p_payer_name text,
  FOREIGN KEY (payer_id, order_id) REFERENCES delivery_description ON DELETE CASCADE,
  PRIMARY KEY (payer_id, order_id)
);
CREATE INDEX delivery_automation_amount_idx ON delivery_automation (p_issuer_id, p_promise_id, payee_id, p_amount);
CLUSTER delivery_automation USING delivery_automation_amount_idx;

-- Signifies a generated user authentication key
CREATE TABLE loginkey (
  secret_md5 text PRIMARY KEY, 
  trader_id int NOT NULL REFERENCES trader_status,
  creation_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_recorded_use_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT at_most_one_loginkey_key_per_trader UNIQUE (trader_id)
);

-- Signifies an evidence that a given trader is associated with a
-- given network address.
CREATE TABLE whitelist_entry (
  id bigserial PRIMARY KEY CHECK (id > 0),
  trader_id int NOT NULL REFERENCES trader_status,
  network_address text NOT NULL,
  occurred_more_than_once boolean NOT NULL DEFAULT FALSE,
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX whitelist_entry_trader_idx ON whitelist_entry (trader_id);
CLUSTER whitelist_entry USING whitelist_entry_trader_idx;

----------------------------------------------------------------------
-- Relations in the following section represent temporary information
-- needed during the turn-generation.
----------------------------------------------------------------------

DROP TABLE IF EXISTS commitment CASCADE;
DROP TABLE IF EXISTS matched_commitment CASCADE;

-- Signifies an input egde for the graph.
CREATE TABLE commitment (
  recipient_id int NOT NULL,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  value value NOT NULL,  -- equals (price * amount)
  ordering_number float
);

-- Signifies a successfully matched egde in the graph.
CREATE TABLE matched_commitment (
  recipient_id int NOT NULL,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  value value NOT NULL
);

----------------------------------------------------------------------
-- Relations in the following section represent information related to
-- sending emails to users.
----------------------------------------------------------------------

DROP TABLE IF EXISTS outgoing_email CASCADE;
DROP TABLE IF EXISTS outgoing_customer_broadcast CASCADE;
DROP TABLE IF EXISTS outgoing_notification CASCADE;

-- Signifies an outgoing email message that needs to be sent over the
-- network.
CREATE TABLE outgoing_email (
  id bigserial PRIMARY KEY CHECK (id > 0),
  subject text NOT NULL,
  content text NOT NULL,
  orig_date timestamp with time zone NOT NULL,
  from_mailbox text NOT NULL, 
  from_display_name text NOT NULL,
  to_mailbox text NOT NULL, 
  to_display_name text NOT NULL DEFAULT '',
  reply_to_mailbox text NOT NULL DEFAULT '',
  reply_to_display_name text NOT NULL DEFAULT '',
  sender_mailbox text NOT NULL DEFAULT '',
  sender_display_name text NOT NULL DEFAULT '',
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Signifies an outgoing broadcast message from a trader to his/her
-- partners.
CREATE TABLE outgoing_customer_broadcast (
  id bigserial PRIMARY KEY CHECK (id > 0),
  trader_id int NOT NULL REFERENCES profile,
  from_mailbox text NOT NULL, 
  subject text NOT NULL,
  content text NOT NULL,
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Signifies an outgoing notification message to a given trader,
-- informing him/her of mew deals/transactions.
CREATE TABLE outgoing_notification (
  id bigserial PRIMARY KEY CHECK (id > 0),
  trader_id int NOT NULL REFERENCES profile,
  to_mailbox text NOT NULL, 
  email_cancellation_code text NOT NULL,
  insertion_ts timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

----------------------------------------------------------------------
-- Relations in the following section represent redundant information
-- that we keep for performance reasons.
----------------------------------------------------------------------

DROP TABLE IF EXISTS mv_recent_deal CASCADE;
DROP TABLE IF EXISTS mv_asset CASCADE;

-- This is the same as "recent_deal", only indexed and clustered
-- differently.
CREATE TABLE mv_recent_deal (
  turn_id int NOT NULL,
  recipient_id int NOT NULL,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  amount float NOT NULL,
  price value NOT NULL,
  ts timestamp with time zone NOT NULL,
  title text NOT NULL,
  unit text NOT NULL,
  summary text NOT NULL,
  epsilon float NOT NULL CHECK (epsilon > 0.0),
  FOREIGN KEY (recipient_id, issuer_id, promise_id, turn_id) REFERENCES recent_deal ON DELETE CASCADE,
  PRIMARY KEY (recipient_id, issuer_id, promise_id, turn_id)
);
CREATE INDEX mv_recent_deal_ts_idx ON mv_recent_deal (recipient_id, ts);
CLUSTER mv_recent_deal USING mv_recent_deal_ts_idx;

-- This is the same as "asset", only indexed and clustered
-- differently.
CREATE TABLE mv_asset (
  recipient_id int NOT NULL,
  issuer_id int NOT NULL,
  promise_id int NOT NULL,
  amount float NOT NULL,
  FOREIGN KEY (issuer_id, promise_id, recipient_id) REFERENCES asset ON DELETE CASCADE,
  PRIMARY KEY (recipient_id, issuer_id, promise_id) WITH (FILLFACTOR=75)
)
WITH (FILLFACTOR=75);
CLUSTER mv_asset USING mv_asset_pkey;
