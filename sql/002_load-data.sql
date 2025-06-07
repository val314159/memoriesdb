
-- anything with a sublime parent is itself sublime.
-- anything NOT sublime exists WITHIN the universe

--SELECT uuid_generate_v1mc() as root_id \gset
--INSERT INTO memories (_type, _parent, id) VALUES (
--  'sublime', :'root_id', :'root_id'
--) RETURNING id as sublime_id \gset

SELECT uuid_generate_v1mc() as category_id \gset
INSERT INTO memories (_type, _parent, content, id) VALUES (
  'category', :'category_id', 'category', :'category_id'
) RETURNING id as category_id \gset

INSERT INTO memories (_type, _parent, content) VALUES (
  'category', :'category_id', 'falsehoods'
) RETURNING id as falsehoods_cid \gset

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
  'category', :'category_id', 'entity'
) RETURNING id as entity_id \gset

INSERT INTO memories (_type, _parent, content) VALUES (
  'category', :'category_id', 'role'
) RETURNING id as role_id \gset

INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'role_id', 'system'
) RETURNING id as system_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'role_id', 'assistant'
) RETURNING id as assistant_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'role_id', 'user'
) RETURNING id as user_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'role_id', 'tool'
) RETURNING id as tool_role_id \gset
INSERT INTO memories (_type, _parent, content) VALUES (
  'role', :'role_id', 'toolcall'
) RETURNING id as toolcall_role_id \gset

INSERT INTO memories (_type, _parent) VALUES (
  'user', :'entity_id'
  -- should we add a role here
  -- maybe a "system__role"?
) RETURNING id as user_id \gset

SELECT uuid_generate_v1mc() as session_id \gset
INSERT INTO memories (_type, _parent, _src, id) VALUES (
  'session', :'user_id', :'session_id', :'session_id'
) RETURNING id as session_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'system_role_id',
  'You are a helpful assistant.  You answer questions quickly and tersely.  Your name is Zelda Yvonne.'
   ) RETURNING id as history_id \gset

-- fork off a new session
INSERT INTO memories (_type, _parent, _src) VALUES (
  'session', :'user_id', :'session_id'
  ) RETURNING id as session_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'assistant_role_id',
  'Okay.'
  ) RETURNING id as history_id \gset

INSERT INTO memories (_type, _parent, role, content) VALUES (
  'history', :'session_id', :'user_role_id',
  'what is 2+2?  also, my car is a red dodge charger.'
  ) RETURNING id as history_id \gset

INSERT INTO memories (_type, _parent, role, _json, content) VALUES (
  'history', :'session_id', :'assistant_role_id', '{"A":"B"}',
  '4.'
  ) RETURNING id as history_id \gset
