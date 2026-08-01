-- Trigram support for typo-tolerant fallback search (see get_products_by_name).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category TEXT NOT NULL CHECK (category IN (
        'outerwear', 'electronics', 'accessories', 'apparel', 'footwear',
        'fitness', 'bags', 'home', 'software'
    )),
    size TEXT,
    stock INT NOT NULL CHECK (stock >= 0),
    -- Full-text search vector: name weighted above category, since customers
    -- search by product name far more often than by category. Generated
    -- column (not trigger-maintained) because to_tsvector('english', text) is
    -- immutable when the config name is a literal, so Postgres can compute
    -- and store it automatically on every insert/update with no app-side or
    -- trigger code to keep in sync.
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(category, '')), 'B')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_products_search_vector ON products USING GIN (search_vector);

-- Trigram index on name for fuzzy/typo-tolerant fallback (see product_service.py).
CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);
