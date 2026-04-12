-- ============================================================
-- PRINTING SHOP MANAGEMENT SYSTEM - Supabase / PostgreSQL
-- ✅ FRESH SCHEMA v2 — Drop old tables first, then run this
-- Run this full file in Supabase SQL Editor
-- ============================================================

-- ⚠️  DROP OLD TABLES (clears all data — run only if starting fresh)
DROP TABLE IF EXISTS job_details CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP FUNCTION IF EXISTS update_updated_at CASCADE;
DROP FUNCTION IF EXISTS calc_total_cost CASCADE;

-- ============================================================
--  CUSTOMERS
-- ============================================================
CREATE TABLE customers (
    id         BIGSERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    mobile     VARCHAR(20)  NOT NULL,
    address    TEXT         DEFAULT '',
    created_at TIMESTAMPTZ  DEFAULT NOW(),
    updated_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_customers_name_lower ON customers (LOWER(name));

-- ============================================================
--  JOBS
--  total_cost = regular column, updated by trigger
-- ============================================================
CREATE TABLE jobs (
    id               BIGSERIAL PRIMARY KEY,
    job_id           VARCHAR(20)    UNIQUE NOT NULL,
    customer_id      BIGINT         REFERENCES customers(id) ON DELETE SET NULL,
    job_name         VARCHAR(255)   DEFAULT '',
    copies           INTEGER        DEFAULT 1,
    invoice_number   VARCHAR(100)   DEFAULT '',
    made_by          VARCHAR(100)   DEFAULT '',
    job_information  TEXT           DEFAULT '',
    status           VARCHAR(50)    DEFAULT 'Pending'
                         CHECK (status IN ('Pending','In Progress','Completed','Delivered')),
    receiving_date   DATE           DEFAULT CURRENT_DATE,
    delivery_date    DATE,
    paper_cost       NUMERIC(10,2)  DEFAULT 0,
    printing_cost    NUMERIC(10,2)  DEFAULT 0,
    design_cost      NUMERIC(10,2)  DEFAULT 0,
    binding_cost     NUMERIC(10,2)  DEFAULT 0,
    other_charges    NUMERIC(10,2)  DEFAULT 0,
    total_cost       NUMERIC(10,2)  DEFAULT 0,   -- ✅ regular column, not generated
    job_image        VARCHAR(500)   DEFAULT '',
    created_at       TIMESTAMPTZ    DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX idx_jobs_customer_id    ON jobs(customer_id);
CREATE INDEX idx_jobs_status         ON jobs(status);
CREATE INDEX idx_jobs_receiving_date ON jobs(receiving_date);

-- ============================================================
--  JOB DETAILS
-- ============================================================
CREATE TABLE job_details (
    id                  BIGSERIAL PRIMARY KEY,
    job_id              BIGINT UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    -- Printing
    machine             VARCHAR(100) DEFAULT '',
    size_printing       VARCHAR(100) DEFAULT '',
    color               VARCHAR(50)  DEFAULT '',
    color_details       VARCHAR(100) DEFAULT '',
    backside_printing   BOOLEAN      DEFAULT FALSE,
    back_color          VARCHAR(100) DEFAULT '',
    total_printing      VARCHAR(100) DEFAULT '',
    total_sets          VARCHAR(100) DEFAULT '',
    -- Plate
    plate_provider      VARCHAR(100) DEFAULT '',
    plate_type          VARCHAR(100) DEFAULT '',
    plate_size          VARCHAR(100) DEFAULT '',
    -- Design
    design_size         VARCHAR(100) DEFAULT '',
    design_pages        VARCHAR(100) DEFAULT '',
    design_details      TEXT         DEFAULT '',
    -- Lamination
    lam_provider        VARCHAR(100) DEFAULT '',
    lam_type            VARCHAR(100) DEFAULT '',
    lam_size            VARCHAR(100) DEFAULT '',
    lam_quantity        VARCHAR(100) DEFAULT '',
    lam_spot_quantity   VARCHAR(100) DEFAULT '',
    -- Punching
    punch_provider      VARCHAR(100) DEFAULT '',
    punch_size          VARCHAR(100) DEFAULT '',
    punch_quantity      VARCHAR(100) DEFAULT '',
    -- Creasing
    crease_provider     VARCHAR(100) DEFAULT '',
    crease_type         VARCHAR(100) DEFAULT '',
    crease_size         VARCHAR(100) DEFAULT '',
    crease_quantity     VARCHAR(100) DEFAULT '',
    -- Folding
    fold_provider       VARCHAR(100) DEFAULT '',
    fold_size           VARCHAR(100) DEFAULT '',
    fold_quantity       VARCHAR(100) DEFAULT '',
    -- Paper
    paper_provider      VARCHAR(100) DEFAULT '',
    paper_size          VARCHAR(100) DEFAULT '',
    paper_sheets        VARCHAR(100) DEFAULT '',
    paper_type          VARCHAR(100) DEFAULT '',
    paper_gsm           VARCHAR(100) DEFAULT '',
    -- Binding
    bind_provider       VARCHAR(100) DEFAULT '',
    bind_type           VARCHAR(100) DEFAULT '',
    bind_size           VARCHAR(100) DEFAULT '',
    bind_pages          VARCHAR(100) DEFAULT '',
    bind_quantity       VARCHAR(100) DEFAULT '',
    -- Envelope
    env_provider        VARCHAR(100) DEFAULT '',
    env_type            VARCHAR(100) DEFAULT '',
    env_size            VARCHAR(100) DEFAULT '',
    env_quantity        VARCHAR(100) DEFAULT '',
    -- Cutting / Other
    cutting_instructions TEXT        DEFAULT '',
    other_instructions   TEXT        DEFAULT '',
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
--  TRIGGERS
-- ============================================================

-- updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ✅ Auto-calculate total_cost on INSERT or UPDATE of cost columns
CREATE OR REPLACE FUNCTION calc_total_cost()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_cost = COALESCE(NEW.paper_cost, 0)
                   + COALESCE(NEW.printing_cost, 0)
                   + COALESCE(NEW.design_cost, 0)
                   + COALESCE(NEW.binding_cost, 0)
                   + COALESCE(NEW.other_charges, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_jobs_calc_total
BEFORE INSERT OR UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION calc_total_cost();

CREATE TRIGGER trg_job_details_updated_at
BEFORE UPDATE ON job_details
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
--  SUPABASE STORAGE — run separately if bucket doesn't exist
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('job-images', 'job-images', true)
-- ON CONFLICT DO NOTHING;