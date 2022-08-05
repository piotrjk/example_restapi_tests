# Example REST API app test suite

This repository contains an example of a basic functional and performance test suites for an REST API application.

The app is made using [FastAPI](https://fastapi.tiangolo.com/) and served using gunicorn with uvicorn workers.

Tests are implemented in [pytest](https://docs.pytest.org), with [Rich](https://github.com/Textualize/rich) used to 
provide some fancy console logging.

## Usage

Tested on Python 3.10 / Linux, but 3.8 should be enough and OS won't matter.  
All commands to be executed from the repo root directory.

First, create a fresh venv for this project:  
`python3 -m venv venv`

Next, activate it:  
`source venv/bin/activate`

Install the requirements:  
`pip install -r requirements.txt`

Run it:  
`pytest -qq -s`

Reporting can be adjusted using pytest commandline arguments. 

## Output
Tests will log out all information on the console, using `rich` library, 
so it will be colorful and may contain some unicode / emoji characters.

I included [example html file with the output](output.html) as it was shown on my tablet pc,
it has a meager i3-10100Y with 5W TDP, so don't be surprised by the benchmark results :) 