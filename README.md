# MemoriesDB - a Database for Memories

## Access your LLM chat history and forms new memories in the same data store

comine elements (blend,gentle tasteful melange)
  time-series db
  relational db
  object database
  graph database
  vector database
  
out-of-the-box features:
  - geared for storing LLM conversations (sessions)
  - can start chucking random strings/documents into the db
  - embeddings for similarity comparison
  - support for fast time-chains
  - the low-level API is in python on top of postgres
  - the web API is available using REST

### Default Object Schema

  - category

  - roles, a category
  - - assistant role
  - - system role
  - - user role (not to be confused with the "user" entity)
  - - ...other roles...

  - entities, a category
  
  - - user entity (not to be confused with the "user" role)

  - session
  - - _parent: user
  - - _src: previous

  - - the NULL session - _src==id

  - history, individual chat messages
  - - content
  - - role
  - - _role <= synthetic property (name of the role)
  - - (should it be role__name)?

document timechain
- locality - deal with data where it is
- use a stored procedure?
- filtering, dynmaically
- when we get to start of prev partial session, jump to next
- moves backwards, seems like a natural way for memories to work

where is the most effiecient point?
  - intermediary
    - right at the point of copying
  - actually one better
    - pre-indexed (bucketed)
