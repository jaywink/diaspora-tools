**PLEASE NOTE that due to an [upstream bug](https://github.com/marekjm/diaspy/issues/21) the contacts migration is currently broken for any pods running 0.5.x or above code.**

## diaspora-tools

Some tools relating to the diaspora* social network
(https://github.com/diaspora/diaspora).

Currently supported features:

* Contact migration from pod to pod

### Contact migration

Since this is the only supported action, it is also the default at the
moment and thus no special command needs to be given.

A "done" user cache file `.diaspora-tools-migrate-user-cache` will be
created in working directory where script is executed. If this
file exists, user guids there will not be added to any aspects.
User cache file can be ignored by passing in `--full` as a parameter.

#### Usage

positional arguments:

* sourcepod &nbsp;&nbsp;&nbsp;username:password@https://sourcepod.tld
* targetpod &nbsp;&nbsp;&nbsp;username:password@https://targetpod.tld

optional arguments:

* -h, --help &nbsp;show this help message and exit
* -n &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Don't do any changes, just print out
* --full &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sync all users in all aspects, ignore user cache file
* --wait &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Wait for webfinger lookups to resolve
  
For example, to migrate contacts from pod A to pod B, waiting for
any triggers that happen to other pods (increases script run time),
the following command would do the trick:

`python diaspora-tools.py --wait jack:password1234@https://pod.example.com jack:password1234@https://pod.foobar.com`

You can specify the `-n` option to just try out the script without actually making any changes.

#### FAQ

##### How are contacts added?

Each aspect is read from the source pod and these contacts will be added
(if they can be found!) to the same aspect on the target pod. If that aspect
is missing, the aspect is created.

##### Are any changes made on the source pod?

No, none at all. Though I take no responsibility for any loss of data :P

##### Will contacts be notified that my sourcepod acccount has added them?

Yes, in the same way as if added via the Diaspora* web interface.

### Requirements

* Python 2.7. Possibly works with Python 3.x but I have not tested it.

Required Python modules:

* `diaspy` ([Marek's fork](https://github.com/marekjm/diaspy))
* `requests`

For Python 2.x SNI SSL support;

* `ndg-httpsclient`
* `pyOpenSSL`
* `pyasn1`

All requirements can be installed using `pip`:

`pip install -r requirements/requirements.txt`

### Installing

Currently only source tarball is available. Download it from the releases
and extract to your location of choice.

Install requirements (see above).

No need to (and no benefit in) install diaspora-tools, just run it from
the folder it is extracted to.

### Credits

Written by Jason Robinson (email: mail@jasonrobinson.me,
[diaspora* profile](https://iliketoast.net/u/jaywink)).

See [other authors](https://github.com/jaywink/diaspora-tools/graphs/contributors) from GitHub.

Thanks [Moritz Kiefer](https://github.com/Javafant) and [Marek Marecki](https://github.com/marekjm) for the awesome `diaspy` module.

### License

Licensed under the MIT license. No responsibility taken by author about
anything this script does or doesn't do :)
