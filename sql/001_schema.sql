CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
  _type VARCHAR(14) NOT NULL,
  _parent UUID NOT NULL REFERENCES memories(id),
  _dst UUID REFERENCES memories(id), -- parent and dst could be combined
  _src UUID REFERENCES memories(id), -- could use this as PREV in a linked list
  role UUID REFERENCES memories(id),
--//  role VARCHAR(9), -- if this isn't a history record, could this encode 'point of view'?
--                   -- does this link into entities?
  content TEXT,
  context_drift BOOLEAN NOT NULL DEFAULT FALSE, -- is context allowed to drift?
  embeddings VECTOR(384),
  _json JSONB NOT NULL DEFAULT '{}'
);
