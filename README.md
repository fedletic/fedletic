# Fedletic

Social activity tracker with ActivityPub!

As of March 10th, this project is still a proof-of-concept and highly unstable. Functionality, schemas, and everything
else is subject to change.

## How to Install

### From Source

* `git clone git@github.com:fedletic/fedletic.git `
* `cd` into the new `fedletic` directory
* `python3 -m venv .venv`
* `source .venv/bin/activate`
* `pip install -r requirements.txt`
* `cp .sample.env .env` and adjust to your environment.
* `./manage.py migrate` to setup up your database.

You can now use the built-in development server to run `./manage.py runserver`

### Running Fedletic

#### In Development

* You can use the built-in development server that Django provides by running `./manage.py runserver`
* ActivityPub messages and workouts are being handled asynchronously with celery. Start it with
  `celery -A fedletic worker -l DEBUG`

#### In Production

* Don't.

### Docker

*Coming soon*

## Contributing

* Before working on something, make sure it's raised as an issue and approved by a maintainer.
* Write tests. Coverage should never go down, only up.
