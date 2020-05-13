TODO
====

Redis commands
--------------

[ ] Add support for Redis `SETEX` command
[ ] Add support for Redis `SETBIT` command
[ ] Add support for Redis `SETNX` command
[ ] Add support for Redis `SETRANGE` command

Storage
-------

[ ] Add support for local file storage
[ ] Add support for MongoDB storage

Performance
-----------

[ ] Try performance by using `run_in_executor` for workers. Supposition: the Multiprocessing Queue is slow thant Asyncio Queue.

Monitoring
----------

[ ] Add integration with Prometheus
[ ] Add integration with InfluxDB