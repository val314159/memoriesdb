#!/bin/sh
exec ssh -L11434:localhost:11434 $(vastai ssh-url $(vastai show instances -q)) "$@"
