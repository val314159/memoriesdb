#!/bin/sh
P=11434
I=$(vastai show instances -q)
echo $I
S=$(vastai ssh-url $I)
echo $S
ssh -i ~/.ssh/id_vastai $S -L $P:localhost:$P

