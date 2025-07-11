"""
Utilities to obtain a LeanIX Access Token by configuring base URLs for LeanIX Authentication and LeanIX GraphQL API.

**Note**: 
    - API tokens are required to access LeanIX services. These should be placed in the `.env` file in the root directory.
    - **It is recommended to experiment using the `LEANIX_API_TOKEN_SANDBOX` before applying any changes using `LEANIX_API_TOKEN`**.
        In`.env` file:
        - `LEANIX_API_TOKEN_SANDBOX`: API Token for Sandbox 
        - `LEANIX_API_TOKEN`: API Token

**Dependencies**:
    - `logging_levels.py` 
"""

import os
import yaml
import requests
from dotmap import DotMap
from dotenv import load_dotenv

from logging_levels import *

#from src.logging_levels import *


# variable to store the base URLs needed for 
# LeanIX Authentication Token and LeanIX GraphQL API
URLS: DotMap

def _configure(yml_path):
    """Configures the base URLs of LeanIX Authentication Token and LeanIX GraphQL API

        | Loads the `.yml` config files with helper function `load_yaml` identified by `yml_path` to access base URLs stored in `leanix.yml` file
        | Loads environment variables stored in the `.env` file with dotenv function `load_dotenv()`

        Parameters:
            yml_path (str):
                Path to `.yml` config files

        Returns:
            None:
    """

    # load config file "leanix.yml" to obtain the base URL of 
    # LeanIX GraphQL API and base URL of LeanIX Authentication Token
    config = load_yaml(yml_path)

    # load credentials from .env file
    # credentials can be overwritten by enviroment variables
    load_dotenv()

    # use environment variables for the LEANIX_API_TOKEN and LEANIX_SUBDOMAIN
    # parameters instead of embedding them directly within the script
    # to minimize unintentionally exposing sensitive data and isolate
    # sensitive information and safeguard it from unauthorized access.
    global LEANIX_API_TOKEN
    global LEANIX_SUBDOMAIN
    
    # TODO: Change to main API_TOKEN when not testing
    #LEANIX_API_TOKEN = os.environ['LEANIX_API_TOKEN']

    # LEANIX SANDBOX for testing 
    LEANIX_API_TOKEN = os.environ['LEANIX_API_TOKEN_SANDBOX']

    LEANIX_SUBDOMAIN = os.environ['LEANIX_SUBDOMAIN']

    # load URLS from "leanix.yml" and replace {LEANIX_SUBDOMAIN} in each
    # url with the actual LEANIX_SUBDOMAIN defined in .env file
    urls = config['urls']
    global URLS
    URLS = DotMap({
        'leanix_graphql': urls['leanixGraphqlUrl'].replace("{LEANIX_SUBDOMAIN}", LEANIX_SUBDOMAIN),
        'leanix_oauth2': urls['leanixOAuth2Url'].replace("{LEANIX_SUBDOMAIN}", LEANIX_SUBDOMAIN),
    })

    
def load_yaml(file_path):
    """Loads the yaml file identified by file_path.
    """
    with open(file_path, 'rt') as file:
        return yaml.safe_load(file.read())


def obtain_access_token() -> str:
    """Obtains a LeanIX Access token using the Technical User generated
    API secret.

    Returns:
        _ACCESS_TOKEN (str):
            The LeanIX Access Token
    """

    # path to "config" folder, to have access to variables in ".yml" config files inside the folder
    SCRIPT_PATH = os.path.dirname(__file__)
    CONFIG_PATH = os.path.join(SCRIPT_PATH, '..', 'config')

    _configure(f"{CONFIG_PATH}/leanix.yml")

    _ACCESS_TOKEN = None
    if _ACCESS_TOKEN:
        return _ACCESS_TOKEN

    # no access token yet, fetch a new one
    if not LEANIX_API_TOKEN:
        raise Exception('A valid token is required')

    response = requests.post(
        url = URLS.leanix_oauth2,
        auth=("apitoken", LEANIX_API_TOKEN),
        data={"grant_type": "client_credentials"}
    )
    log.info(f"Access_token response code: {response.status_code}")
    response.raise_for_status()
    _ACCESS_TOKEN = response.json().get('access_token')
    return _ACCESS_TOKEN


"""
def main():
    obtain_access_token()

if __name__ == '__main__':
    main()
"""