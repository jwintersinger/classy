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

    cp config.py.example config.py
    # Now edit config.py as you please.
    ./classy.py

If you find Classy useful, you will likely love [DNDN][dndn]. DNDN greatly
improved my life over three years of scheduling courses.

[blog post]: http://jeff.wintersinger.org/posts/2014/06/classy-helping-you-register-for-full-courses-at-the-university-of-calgary/
[dndn]: http://dndn.ethv.net/
