\c postgres;
DROP   DATABASE IF EXISTS memories;
CREATE DATABASE memories;
\c memories;
CREATE EXTENSION "vector";
CREATE EXTENSION "uuid-ossp";
