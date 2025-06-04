--\c postgres;
--DROP   DATABASE IF EXISTS memories;
--CREATE DATABASE memories;
--\c memories;
CREATE EXTENSION "vector";
CREATE EXTENSION "uuid-ossp";

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

-- anything with a sublime parent is itself sublime.
-- anything NOT sublime exists WITHIN the universe

SELECT uuid_generate_v1mc() as root_id \gset
INSERT INTO memories (_type, _parent, id) VALUES (
  'sublime', :'root_id', :'root_id'
) RETURNING id as sublime_id \gset

INSERT INTO memories (_type, _parent, content) VALUES (
  'category', :'sublime_id', 'false'
) RETURNING id as false_cid \gset

--INSERT INTO memories (_type, _parent) VALUES (
--  'false', :'sublime_id'
--) RETURNING id as false_id \gset

-- do we even NEED a universe?
-- like, the fact we exist and don't
-- point to sublime means we're a part of the universe?
--INSERT INTO memories (_type, _parent) VALUES (
--  'universe', :'sublime_id'
--) RETURNING id as universe_id \gset

-- ok if entities pointed to sublime,
-- this would imply that all entities exist outside the universe?
-- well, they are ghosts in the machine
-- we don't really understand them so they might as well
-- be "souls".
INSERT INTO memories (_type, _parent, content) VALUES (
  'category', :'sublime_id', 'entities'
) RETURNING id as entities_id \gset

--INSERT INTO memories (_type, _parent) VALUES (
--  'entities', :'sublime_id'
--) RETURNING id as entities_id \gset

INSERT INTO memories (_type, _parent, content) VALUES (
  'category', :'sublime_id', 'roles'
) RETURNING id as roles_id \gset

--INSERT INTO memories (_type, _parent) VALUES (
--  'roles', :'sublime_id'
--) RETURNING id as roles_id \gset

-- everything before this is a singleton
-- everything after is not.

-- does this mean anything?
-- are concepts singletons?

INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'roles_id', 'system'
) RETURNING id as system_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'roles_id', 'assistant'
) RETURNING id as assistant_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'roles_id', 'user'
) RETURNING id as user_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'roles_id', 'tool'
) RETURNING id as tool_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'roles_id', 'toolcall'
) RETURNING id as toolcall_role_id \gset

INSERT INTO memories (_type, _parent) VALUES (
  'user', :'entities_id'
) RETURNING id as user_id \gset

SELECT uuid_generate_v1mc() as session_id \gset
INSERT INTO memories (_type, _parent, _src, id) VALUES (
  'session', :'user_id', :'session_id', :'session_id'
) RETURNING id as session_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'system_role_id',
  'You are a helpful assistant.'
  ) RETURNING id as history_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'assistant_role_id',
  'Okay.'
  ) RETURNING id as history_id \gset

-- fork off a new session
INSERT INTO memories (_type, _parent, _src) VALUES (
  'session', :'user_id', :'session_id'
) RETURNING id as session_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'user_role_id',
  'what is 2+2?'
  ) RETURNING id as history_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'assistant_role_id',
  '4.'
  ) RETURNING id as history_id \gset
