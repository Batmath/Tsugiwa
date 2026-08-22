#!/bin/sh
chown -R userapp:userapp /app/data /app/log
exec gosu userapp "$@"