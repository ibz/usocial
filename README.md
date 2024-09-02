# This project has been discontinued

## usocial (2018 - 2022)

Most open source projects are simply forgotten and die a slow and lonely death.

**usocial** was different. Same same, but different.

It started as a personal RSS feed reader, evolved into a Podcasting 2.0 client, got released on Umbrel OS...

You could run usocial on your own Umbrel personal server, follow your favourite blogs, subscribe to your favourite podcasts...

**usocial** would connect to your own Lightning node and, while listening to a podcast episode, you could send sats directly to the podcaster. The payment would even automatically be split, according to the podcaster's desire, and go to different recipients.

It had a terrible UI, but it worked beautifully. It was my way of keeping up to date with podcasts and blogs and tipping creators.

Then, something happened.

**usocial** didn't die, it just evolved into something else: **[Servus](https://github.com/servuscms/servus)** (2022-).

I realized that more important than following blogs and podcasts is publishing your own content. Only *after* there is a solid way for anyone to self-host their web site and **publish** content will there be a need for a self-hosted way to **subscribe** to content.

I used to be a fan of Jekyll, but I realized that it is not for the mere mortals to use. I hated WP, which I had used since 2005 or so. WP was more user-friendly than Jekyll and other SSGes, but it just did not click with me.

I had written a few CMSes before (2008-2012), mostly trying to host my photoblog in a pre-Flickr era and to build a sort-of online travel log. See [nuages](https://github.com/ibz/nuages), [tzadik](https://github.com/ibz/tzadik), [feather](https://github.com/ibz/feather) and [travelist](https://github.com/ibz/travelist).

Then it all clicked. The missing piece was a CMS. I could take a lot of ideas from Jekyll, while trying to keep the usability of WP.

That is how [Servus](https://github.com/servuscms/servus) was born and that was the end of usocial.

It didn't die, it just evolved.

## Setting up the development environment

1. Clone the repo

   `git clone https://github.com/ibz/usocial.git && cd usocial`

1. Set up a venv

   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -e .
   ```

1. Create an "instance" directory which will store your database and config file.

   `mkdir instance`
1. Generate a secret key (this is required by Flask for [CSRF](https://en.wikipedia.org/wiki/Cross-site_request_forgery) protection)

   ```echo "SECRET_KEY = '"`python3 -c 'import os;print(os.urandom(12).hex())'`"'" > instance/config.py```
1. Export the environment variables (`FLASK_APP` is required, `FLASK_ENV` makes Flask automatically restart when you edit a file)

   `export FLASK_APP=usocial.main FLASK_ENV=development`
1. Create the database (this will also create the default user, "me", without a password)

   `flask create-db`

1. Run the app locally

   `flask run`
