Realtime Redis Backup
=====================

`Realtime Redis Backup` (RRB) watch for Redis changes in their keys and save in a storage system.

Currently only S3 compatible storage is supported. If you want to collaborate you're welcome! (please check https://github.com/cr0hn/realtime-redis-backup/blob/master/TODO.rst>`_)

Install
=======

Python Install
--------------

.. code-block:: console

    $ pip install realtime-redis-backup

.. warning::

    Python 3.8 or above is needed!

Docker Install
--------------

This method is recommended:

.. code-block:: console

    $ docker pull cr0hn/realtime-redis-backup

Backup Mode
===========

Quick start
-----------

Python way
++++++++++

.. code-block:: console

    $ export S3_SERVER=http://localhost:9000
    $ export S3_BUCKET="my-backup"
    $ export S3_SECRET_KEY=XXXXXXXX
    $ export S3_ACCESS_KEY=XXXXXXXX
    $ rrb redis://localhost:6379/0
    [*] Connecting to Redis...OK!
    [*] Using Redis pattern: '*'
    [*] Starting workers
        > [Worker-0] starting...OK!
        > [Worker-1] starting...OK!
    [*] Starting Realtime Redis Backup service... OK!


Docker way
++++++++++

.. code-block:: console

    $ docker run --rm -d -e S3_SERVER=http://localhost:9000 -e S3_BUCKET="my-backup" -e S3_SERVER=http://localhost:9000 -e S3_SECRET_KEY=XXXXXXXX -e S3_ACCESS_KEY=XXXXXXXX cr0hn/realtime-redis-backup redis://localhost:6379/0

You also can setup redis server by using environ var:

.. code-block:: console

$ docker run --rm -d -e S3_SERVER=http://localhost:9000 -e S3_BUCKET="my-backup" -e S3_SERVER=http://localhost:9000 -e S3_SECRET_KEY=XXXXXXXX -e S3_ACCESS_KEY=XXXXXXXX -e REDIS_SERVER=redis://localhost:6379/0 cr0hn/realtime-redis-backup

Advanced usage
--------------

Parameters and usage modes explained are valid for both method of running: Python and Docker.

Workers
+++++++

By default `RRD` set up 1 concurrent connections with S3. If you want change this value you can use `--concurrency` field.

.. code-block:: console

    $ rrb -c 5 redis://127.0.0.1:6379/1
    [*] Connecting to Redis...OK!
    [*] Using Redis pattern: '*'
    [*] Starting workers
        > [Worker-0] starting...OK!
        > [Worker-1] starting...OK!
        > [Worker-2] starting...OK!
        > [Worker-3] starting...OK!
        > [Worker-4] starting...OK!
    [*] Starting Realtime Redis Backup service... OK!

Specific Redis keys
+++++++++++++++++++

By default all Redis Keys will be stored as backup in storage system. But if you only want to backup some keys, you can set a `redis pattern`. Only Redis Keys that matches with these rules will be stored.

Example:

.. code-block:: console

    $ rrb -r "users:profile*" redis://127.0.0.1:6379/1
    [*] Connecting to Redis...OK!
    [*] Using Redis pattern: 'users:profile*'
    [*] Starting workers
        > [Worker-0] starting...OK!
        > [Worker-1] starting...OK!
    [*] Starting Realtime Redis Backup service... OK!

Base path
+++++++++

By default `RRB` will store Redis keys in root path. If you want to set a relative path at your storage system you can use `--path` param:

.. code-block:: console

    $ rrb -P /my-keys/
    [*] Connecting to Redis...OK!
    [*] Using Redis pattern: 'users:profile*'
    [*] Using S3 base path: '/my-keys/'
    [*] Starting workers
        > [Worker-0] starting...OK!
        > [Worker-1] starting...OK!
    [*] Starting Realtime Redis Backup service... OK!


Versioning
++++++++++

Default mode
^^^^^^^^^^^^

S3 and compatible systems (like MinIO) support versioning for buckets. This means that you can overwrite a file and S3 will manage the versions of files.

File names are a SHA256 of Redis Key:

.. code-block:: console

    $ ls
    -rwxr-xr-x   8 Dani  staff   123B May  9 18:13 adf07f14525c48d64e1752fcada7c690fbb7166fdc566dc7898a4eb1e1f03332.backup
    -rwxr-xr-x   8 Dani  staff   123B May  9 18:10 2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892.backup

Versioning mode
^^^^^^^^^^^^^^^

If you enable this mode `RRB` will append a timestamp in every file as a version of a file. Each time a Redis key changes the content will be stored in a new file with the timestamp prefix. Format is:

    HASH.TIMESTAMP.backup

Enabling versioning mode is easy:

.. code-block:: console

    $ export S3_SERVER=http://localhost:900
    $ export S3_BUCKET="my-backup"
    $ export S3_SECRET_KEY=XXXXXXXX
    $ export S3_ACCESS_KEY=XXXXXXXX
    $ rrb --versioning redis://
    [*] Connecting to Redis...OK!
    [*] Using Redis pattern: 'users:profile*'
    [*] RDD Versioning enabled
    [*] Starting workers
        > [Worker-0] starting...OK!
        > [Worker-1] starting...OK!
    [*] Starting Realtime Redis Backup service... OK!

.. code-block:: console

    $ ls
    -rwxr-xr-x   8 Dani  staff     8B May  9 18:13 1589371200.adf07f14525c48d64e1752fcada7c690fbb7166fdc566dc7898a4eb1e1f03332.backup
    -rwxr-xr-x   9 Dani  staff     9B Apr 24 18:15 1589372333.adf07f14525c48d64e1752fcada7c690fbb7166fdc566dc7898a4eb1e1f03332.backup

Restore Mode
============

Quickstart
----------

Without Docker
++++++++++++++

When you need to recover data from S3 and load into Redis you must use command `rrb-restore`.

Usage is very similar than `rrb`.

.. code-block:: console

    $ export S3_SERVER=http://localhost:900
    $ export S3_BUCKET="my-backup"
    $ export S3_SECRET_KEY=XXXXXXXX
    $ export S3_ACCESS_KEY=XXXXXXXX
    $ export REDIS_SERVER=redis://localhost:6379/0
    $ rrb-restore

Docker mode
+++++++++++

.. code-block:: console

    $ docker run --rm -d -e S3_SERVER=http://localhost:9000 -e S3_BUCKET="my-backup" -e S3_SERVER=http://localhost:9000 -e S3_SECRET_KEY=XXXXXXXX -e S3_ACCESS_KEY=XXXXXXXX -e REDIS_SERVER=redis://localhost:6379/0 --entrypoint rrb-restore cr0hn/realtime-redis-backup

Advanced usage
--------------

Base path
+++++++++

As in `RRB` you also can set the base path where `RRB Restore` will get S3 data:

.. code-block:: console

    $ export S3_SERVER=http://localhost:900
    $ export S3_BUCKET="my-backup"
    $ export S3_SECRET_KEY=XXXXXXXX
    $ export S3_ACCESS_KEY=XXXXXXXX
    $ export REDIS_SERVER=redis://localhost:6379/0
    $ rrb-restore -P /users/profile2/ redis://127.0.0.1:6500
    [*] Connecting to Redis...OK!
    [*] Using S3 base path: '/users/profile2/'
    [*] Starting Redis writers...
        > [Writer-0] starting...OK!
        > [Writer-1] starting...OK!
    [*] Checking S3 connection...Ok!
    [*] Starting S3 channels
        > [Channel-0] starting...OK!
        > [Channel-1] starting...OK!
    [*] Starting S3 reader...OK!
    [*] Start restoring S3 backup to redis...
    [*] All data loaded. Total time: 19.846128015213013 seconds

Concurrency
+++++++++++

You also can setup the concurrency:

.. code-block:: console

    $ export S3_SERVER=http://localhost:900
    $ export S3_BUCKET="my-backup"
    $ export S3_SECRET_KEY=XXXXXXXX
    $ export S3_ACCESS_KEY=XXXXXXXX
    $ export REDIS_SERVER=redis://localhost:6379/0
    $ rrb-restore -c 10 -P /users/profile2/ redis://127.0.0.1:6500
    [*] Connecting to Redis...OK!
    [*] Using S3 base path: '/users/profile2/'
    [*] Starting Redis writers...
        > [Writer-0] starting...OK!
        > [Writer-1] starting...OK!
        > [Writer-2] starting...OK!
        > [Writer-3] starting...OK!
        > [Writer-4] starting...OK!
        > [Writer-5] starting...OK!
        > [Writer-6] starting...OK!
        > [Writer-7] starting...OK!
        > [Writer-8] starting...OK!
        > [Writer-9] starting...OK!
    [*] Checking S3 connection...Ok!
    [*] Starting S3 channels
        > [Channel-0] starting...OK!
        > [Channel-1] starting...OK!
        > [Channel-2] starting...OK!
        > [Channel-3] starting...OK!
        > [Channel-4] starting...OK!
        > [Channel-5] starting...OK!
        > [Channel-6] starting...OK!
        > [Channel-7] starting...OK!
        > [Channel-8] starting...OK!
        > [Channel-9] starting...OK!
    [*] Starting S3 reader...OK!
    [*] Start restoring S3 backup to redis...
    [*] All data loaded. Total time: 12.947448015213013 seconds

Limitations
===========

- Currently only watch for changes in string keys. This means that only watch for `SET` Redis command.
- You can't mix in the same bucket data with `--versioning` flag and without them. If you mix these types first type read form S3 will be used as fomat.

License
=======

This project is distributed under `BSD license <https://github.com/cr0hn/realtime-redis-backup/blob/master/LICENSE>`_
