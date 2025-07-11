# LeanIX and GraphQl Utilities 

A modular Python utility suite for extracting, filtering, and transforming LeanIX data using the GraphQL API. Includes templates, token authentication, Jupyter automation, and ready-to-use scripts for LeanIX FactSheets and log events.

These utilities are created to ease the extraction and management of data from LeanIX using the LeanIX GraphQL API and Python.

## Table of Content
- [Setup](#setup)
    - [Requirements](#requirements)
    - [Configuration](#configuration)
- [Use](#use)
    - [Use Case](#use-case-example-usage)
- [File Structure](#file-structure)
- [License](#license)

## Setup

### Requirements
- python 3.10 or higher
- `pip` (Python package manager)
- (recommended) A virtual enviromnent tool like `venv`or `virtualenv`

Check the required packages in [requirements.txt](requirements.txt)

### Installation
TODO: Add final link to clone the repo!
1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/your-project.git
    cd your-project
    ```
2. Create a Virtual Environment (recommended)
    ```bash
    python -m venv venv
    source venv/bin/activate # On macOs/Linux
    venv\Scripts\activate    # On Windows
    ```

3. Install dependencies:
    Install the required packages in [requirements.txt](requirements.txt):
    ```bash
    pip install -r requirements.txt
    ```
    To install further packages using pip:
    ```bash
    pip3 install <package_name>
    ```

### Configuration
1. **Environment Variables**
    
    API tokens are required to access LeanIX services. These should be placed in the `.env` file in the root directory.

    **NOTE**: It is highly recommended to experiment using the `LEANIX_API_TOKEN_SANDBOX` before applying any changes using `LEANIX_API_TOKEN`.

- `LEANIX_API_TOKEN_SANDBOX`: API Token for Sandbox 
- `LEANIX_API_TOKEN`: API Token

2. **Create a `.env`** by copying the provided template in [`.env_template`](/templates/.env_template).

    Then open the newly created `.env` file and replace the placeholder values: 

    ```
    LEANIX_API_TOKEN=your-production-token-here
    LEANIX_API_TOKEN_SANDBOX=your-sandbox-token-here
    ```
3. **YAML Config Files**

    Inside the `config` folder:
    - `leanix.yml`: Contains endpoints URLs for GraphQL and OAuth2 (Authentication) exchange.
    - `logging.yml`: Defines logging formats, and colors. (`logging_levels.py` defines the logging levels)

    Make sure these files exist and are correctly sturctured. Check the Official [LeanIX documentation: Using GraphQL with Python](https://docs-eam.leanix.net/reference/use-graphql-with-python#:~:text=leanix%2Dgraphql%2Dtutorial-,Step%202%3A%20Create%20and%20Run%20a%20Python%20GraphQL%20Query%20Script,-GraphQL%20queries%20allow).
    
    The code in `leanix_utils.py` will automatically load them via the `_configure()` method.

    Example `leanix.yml`:
    ```
    urls:
        leanixGraphqlUrl: https://{LEANIX_SUBDOMAIN}.leanix.net/services/pathfinder/v1/graphql
        leanixOAuth2Url: https://{LEANIX_SUBDOMAIN}.leanix.net/services/mtm/v1/oauth2/token
    ```

4. **Automatic Imports on Kernel Restart (Works in: VS Code, JupyterLab, classic Jupyter) - Optional**
    
    In general it is highly recommended to experiment and test code in a sandbox environment before applying it to production.
    In this project testing the code and functions in a Jupyter Notebook is a suitable method.

    To ensure necessary packages and modules are automatically imported every time the Jupyter kernel starts - without manually running a cell - you can use IPython's built-in startup system with following steps:
    1. Locate the IPython Startup Folder
       -  Open the terminal and run:
            ```bash
            ipython profile locate
            ```
        - This will output a path like:
            ```bash
            /home/your_username/.ipython/profile_default
            ```
        - Inside the directory, you'll find (or can create) a `startup/` folder:
            ```bash
            ~/.ipython/profile_default/startup/
            ```
        Any `.py` file placed in this folder will be executed automatically on every kernel start.
    2. Create the Startup Script
        - In the `startup/` folder, create a file named `ipynb_startup_imports.py`.
        For a prepared template check: [`ipynb_startup_imports_template.py`](/templates/ipynb_startup_imports_template.py).

        Example content:
        ```py
        """Template to automatically import packages and modules on Kernel Restart"""

        # This runs on every time the .ipynb kernel (re)start

        # general packages and modules
        import numpy as np
        import pandas as pd 
        import json

        # Any project-specific modules
        import graphql_leanix_utils as gqlix

        print("ipynb_startup_imports.py loaded successfully!")
            ```
        this script can include any imports, environment setup, or shared functions you want to be available globally across your notebooks.
    3. Restart the Kernel
        Once this file is in place, restarting the kernel in **any Jupyter notebook** (including those opened in **VS Code**) will automatically run this script. No need to manually run any import cells.



## Use
This section outlines the gernaeral implementation flow for interacting with the LeanIX GraphQL API using custom base queries and filters, resulting in structured data and extraction as Pandas DataFrames.

### General Implementation Concept and Workflow
<br>

![img](/README%20&%20Documenation%20assets/general_implemntation_concept_diagram.png)

<br>

The data retrieval pipeline consists of the following steps: 
1. **Read and Construct Query**:
    Load a base query template and apply dynamic filters via a variables template.
2. **Post GraphQL Query**:
    Submit the constructed query to the LeanIX GraphQL API.
3. **Extract Response**:
    Parse the JSON response to extract the relevant data content.
4. **Create DataFrame**:
    Convert the extracted content into a structured Pandas DataFrame for further analysis.

*You can find the diagram above in [README & Documentation assets](/README%20&%20Documenation%20assets/) folder.*

### Core Components
- **Query Templates**: [`queries_txt`](/queries_txt)
- **Variables Templates**: [`facet_filter_templates.py`](/src/facet_filter_templates.py)
- **GraphQL Logic**: [`graphql_leanix_utils.py`](/src/graphql_leanix_utils.py)


### GraphQL Query Structure:

A query in GraphQL consists of two parts, `query` and `variables`:
- The `query` part contains the information/data in a dictionary with a tree like structure.
- The `variables` part contains the variables such as `filters` and `sortings` that can be applied to the `query`.

***NOTE***: A GraphQL query may have different forms and is not necessarily divided into two parts. The form above is chosen because it suits the use case, so it's just an implementation decision.

### General Idea: 
- Make queries modular by using a **base query** template, which can be extended further depending on the specific use case
- Create a **base query** for the main query types: 
    - `allFactSheets`: Runs a query to get all or a set of fact sheets based on given filters.
    - `allLogEvents`: Runs a query to retrieve all log events.
- Apply filters, primarily `facetFilters`, depending on the use case by adding filters to a custom **variables template**.

<br>

**Base Query and Variables Components/Building Blocks**:

- `base query` templates are maintained in multiple `.txt` files in the folder `queries_txt`, with each FactSheet type having its own **base query** template. For example: `app.txt`, `IT_component.txt`, ...
- `variable templates` are maintained in a separate file `facet_filter_templates.py`
- `query templates` are maintained in a separate file `query_templates.py`

<br>

***NOTE***: In the following example a `allFactSheets` **base query** is used to show the components of the custom **base query**.

- **Base Query Template**: A general base query template for the [main query types](#general-implementation-consept)
    - `#ADDTIONAL_NODE_NODES#`
        
        Placeholder in the **base query** to replace with **on-node-nodes** when needed.

        Example of **on-node-nodes**: `id`, `status`, `category` 
    - `#ADDTIONAL_APPLICATION_NODES#`

        Placeholder in the **base query** to replace with **on-application-nodes** when needed. 
        
        Example of **on-application-nodes**: `id`, `apptype`, `bankId`

<br>

**INFO**: A `allFactSheets` **base query** on applications retrieves by default the `id`, `bankId`, `displayName` (= application name) of the applications.
To see an example check [Use Case](Use_Case.md)

<br>

- **Variables Template**: A general variables template for the [main query types](#general-implementation-consept)
    -  `${facet_filters}`
    
        Placeholder in the **variables template** for the list of filter (`facetFilters`) objects which describes the filtering of one facet and that can be applied to the facet.

<br>

**INFO**: A `allFactSheets` **variables template** has no `facetFilters` applied (=an empty list) and the applications are sorted by `displayName` in ascending order.
To see an example check [Use Case](Use_Case.md)


### Use Case (Example Usage)

To see several examples of how this module/tool is used check [use_cases](./src/use_cases/).

To see an example of retrieving information on applications in LeanIX using a `allFactSheets` **base query** and a **variables template** check [Use Case](Use_Case.md)

## File Structure
```
├───config
│   ├───leanix.yml
│   ├───logging.yml
├───queries_txt
├───data
├───use_cases
│   |   ├───create_factSheets_use_case.ipynb
│   |   ├───use_case_application_factSheet
│   |   ├── ...
├───src
│   ├───__init__.py
│   ├───query_templates.py
│   ├───facet_filter_templates.py
|   ├───leanix_utils.py
│   ├───graphql_leanix_utils.py
│   ├───get_and_set_bankId_for_business_capability.py
│   ├───new_factsheet.py
│   ├───...
├───templates
│   ├───.env_template
│   ├───ipynb_startup_imports_template
└───tests
│   ├───dummy_graphql_responses
│   |   ├───app_ids_dummy.json
│   ├───testing_queries_txt
│   ├───test_graphql_leanix_utils.py
│   └───module_testing.ipynb
├───.env
├───requirements.txt
├───USE_CASE.md
└───README.md
```

### config: 
- `leanix.yml`: Contains endpoints URLs for GraphQL and OAuth2 (Authentication) exchange.
- `logging.yml`: Contains and defines the logging configuration (levels, formatters, handlers, colors, ...) 

### use_cases: 
- Folder containing use cases how this module/tool is used 

### src: 
- `leanix_utils.py`: Contains utilities to obtain a LeanIX Access Token by configuring base URLs for LeanIX Authentication and LeanIX GraphQL API. 
    - Configures the base URLs of LeanIX Authentication Token and LeanIX GraphQL API
    - Loads the `.yml` config files with helper function `load_yaml` identified by `yml_path` to access base URLs stored in `leanix.yml` file
    - Loads environment variables stored in the `.env` file with dotenv function `load_dotenv()`
    - Obtains a LeanIX Access token using the Technical User generated
    API secret
- `graphql_leanix_utils.py`: Contains main logic and utility functions to access, retrieve, modify data from LeanIX using GraphQL API and Python
    - Creates a Logger to track events
    - Obtains leanIX ACCESS_TOKEN
    - Contains variables and helper functions (mostly begin with an underscore `_helperFunctionX`), for example: 
        - Convert factSheets to panda df: `factSheets_to_df(allFactSheets : dict) -> pd.DataFrame`
        - `_get_facet_filter_template(filter:str) -> str`
        - add additional on-factSheet-nodes to query: `_add_on_factSheet_nodes(query: str, nodes: list) -> str`
        - add additional on-node-nodes to query: `_add_on_node_nodes(query: str, nodes: list) -> str`
        - `_clean_query(query: str) -> str`
        - ...

    - Is divided in multiple sections, each section for a specific FactSheet type, for example:
        - Variables
        - Common/Helper Methods
        - GraphQL Queries
        - GraphQL Queries To Pandas DataFrame
        - Application 
        - IT-Components 
        - ...

    - Contains functions to construct, post, modify queries
        - query function, i.e. `query_apps`: Reads query from text file and constructs the query by adding/adjusting filter components.
        - post function i.e. `post_query`: Posts query to LeanIX and returns a parsed response (json), `post_query` is called/used within `query_apps`.
        - ...
    - Contains functions to transform query responses to pandas data frames and evaluate the data
        - transforming function i.e. `factSheets_to_df`: Creates a pandas data frame out of the parsed response.
        - get function, i.e. `get_apps`: Is composed out of two functions: `query_apps` and `factSheets_to_df`. 
        - `get_apps` can be adjusted to suit the use case by passing different arguments to the functions: `query_apps`, `factSheets_to_df`. 
        - ... 
    - Contains functions to save data frame as `.csv` and excel `.xlsx` file
    - Contains function to Read & Post GraphQL Queries from `.txt` file

- `query_templates.py`: Contains GraphQL Query Filter Templates
- `facet_filter_templates.py`: Contains GraphQL facetFilter Templates 
- `new_factsheet.py`: This file contains utility functions to create new FactSheets of type `Application` in LeanIX using LeanIX GraphQL API.
- `get_and_set_bankId_for_business_capability.py`: Script which assigns a `bankId` to each `BusinessCapability` FactSheet
- `requirements.txt`
- `.env`: Contains API TOKEN for LeanIX

### data:
- Folder where DataFrame are saved as `.csv` and excel `.xlsx` files

### tests:
- `dummy_graphql_responses`
├───`app_ids_dummy.json`: Contains a dummy graphql responses as `.json` files

- testing_queries_txt
├───`apps.txt`: GraphQL queries as `.txt` files

- `module_testing.ipynb`: Jupyter Notebook to test new functionalities (In this project testing the code and functions in a Jupyter Notebook is a suitable method)

- `test_graphql_leanix_utils.py`: File to test the main methods in `leanix_utils.py` and `graphql_leanix_utils.py`


## License

This project is licensed under [**no open-source license**](/LICENSE) and is intended for **showcasing purposes only**.  
All rights are reserved by the author.

No part of this project may be used, copied, modified, or distributed without explicit permission.

Unauthorized copying, modification, distribution, or commercial use of this code is strictly prohibited.

