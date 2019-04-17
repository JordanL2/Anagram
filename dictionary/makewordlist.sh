#!/bin/sh

tr -d '\015' < brit-a-z.txt | grep -E "^[a-z][a-z][a-z]+\s*$" | sed -e "s/\\s+//g" > output.txt
cat shortwords.txt >> output.txt
