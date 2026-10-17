CREATE TABLE IF NOT EXISTS enterprise_inquiries (
  id uuid PRIMARY KEY,
  request_hash text NOT NULL,
  name varchar(120) NOT NULL,
  email varchar(254) NOT NULL,
  company varchar(160) NOT NULL,
  service varchar(80) NOT NULL,
  message varchar(5000) NOT NULL,
  consent boolean NOT NULL CHECK (consent),
  notice_version text NOT NULL,
  status text NOT NULL DEFAULT 'new' CHECK (status IN ('new','in_review','closed','hold')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS enterprise_inquiries_newest ON enterprise_inquiries (created_at DESC);
