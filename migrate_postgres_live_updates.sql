-- Add live update columns to PostgreSQL orders table
-- Run this SQL script to add the new live update columns

-- Add the live update columns
ALTER TABLE orders ADD COLUMN IF NOT EXISTS effective_status VARCHAR(50);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS status_updates TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(500);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS last_status_update TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS status_actor VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS live_update_data TEXT;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_orders_effective_status ON orders(effective_status);
CREATE INDEX IF NOT EXISTS ix_orders_last_status_update ON orders(last_status_update);

-- Display the updated schema
\d orders;