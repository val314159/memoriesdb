CREATE TABLE memories (

  id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),

  _type VARCHAR(14) NOT NULL,
  
  _parent UUID NOT NULL REFERENCES memories(id),
  
  _dst UUID REFERENCES memories(id), -- parent and dst could be combined
  _src UUID REFERENCES memories(id), -- could use this as PREV in a linked list

  role UUID REFERENCES memories(id),

--//  role VARCHAR(9), -- if this isn't a history record, could this encode 'point of view'?
--                   -- does this link into entities?
--  context_drift BOOLEAN NOT NULL DEFAULT FALSE, -- is context allowed to drift?

  content TEXT,
  content__drift BOOLEAN NOT NULL DEFAULT FALSE, -- is content allowed to drift?
--  content__embeddings VECTOR(384),
  content__embeddings VECTOR(1024),

  _json JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE embedding_schedule (
   id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
  rec UUID NOT NULL REFERENCES memories(id),
--   created_at TIMESTAMP NOT NULL DEFAULT NOW(),
   started_at TIMESTAMP,
  finished_at TIMESTAMP,
    error_msg TEXT
);
