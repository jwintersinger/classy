Classy
======

Classy will query the University of Calgary's PeopleSoft installation to
determine if spots are available in class sections of interest, then e-mail you
as soon as one opens. For more details, please see [my blog post introducing
Classy][blog post].

To use, do the following:

    # Install Beautiful Soup dependency.
      # If on Debian/Ubuntu:  apt-get install beautifulsoup4
      # If on another distro: pip3 install beautifulsoup4
        # Note you can instead run "pip3 install --user beautifulsoup4" if you
        # don't want to install system-wide.

    $ cp config.py.example config.py
    $ # Now edit config.py as you please.
    $ ./classy.py
    [2014-07-01 01:38:03.931248] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 01:42:06.686731] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 01:46:09.432416] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 01:50:12.352554] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 01:54:15.214403] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 01:58:18.362796] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 02:02:21.555650] Queried DRAM 571 for user1@example.org. 0/1 section(s) are open [2 total].
    [2014-07-01 02:06:24.620162] Queried DRAM 571 for user1@example.org. 1/1 section(s) are open [2 total].
    [2014-07-01 02:06:26.440111] Sent "Open course notification: DRAM 571" to user1@example.org.
    [2014-07-01 02:06:26.441488] Removing DRAM 571 from user1@example.org's queries.

If you find Classy useful, you will likely love [DNDN][dndn]. DNDN greatly
improved my life over three years of scheduling courses.

[blog post]: http://jeff.wintersinger.org/posts/2014/06/classy-helping-you-register-for-full-courses-at-the-university-of-calgary/
[dndn]: http://dndn.ethv.net/
