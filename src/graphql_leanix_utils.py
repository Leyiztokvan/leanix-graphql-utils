"""
This file contains utility functions to work easily with LeanIX and GraphQL using LeanIX GraphQL API.

**Note**: 
    - API tokens are required to access LeanIX services. These should be placed in the `.env` file in the root directory.
    - **It is recommended to experiment using the `LEANIX_API_TOKEN_SANDBOX` before applying any changes using `LEANIX_API_TOKEN`**.
        In`.env` file:
        - `LEANIX_API_TOKEN_SANDBOX`: API Token for Sandbox 
        - `LEANIX_API_TOKEN`: API Token

**Dependencies**:
    - `leanix_utils.py`
    - `facet_filter_templates.py`
    - `query_templates.py`
"""

import logging
import requests
import json
import pandas as pd
from pandas import json_normalize
import numpy as np
import os
from datetime import datetime, date
import re
from string import Template
from typing import TypedDict
import ast
from functools import reduce

import leanix_utils as lix
import facet_filter_templates as filter_temp
import query_templates as query_temp


########################## Variables / Custom Classes ##########################
# creating a Logger to track events
log = logging.getLogger(__name__)

# NOTE: ACCESS_TOKEN should not be obtained at every time a query is posted 
# but only once at the beginning --> more efficient
ACCESS_TOKEN = lix.obtain_access_token()

# custom references (variables/str) in queries (in .txt files)
ADDTIONAL_NODE_NODES = "#ADDTIONAL_NODE_NODES#"
ADDTIONAL_FACTSHEET_NODES = "#ADDTIONAL_FACTSHEET_NODES#"

class FilterTemplate(TypedDict):
    """Custom typed dictionary created for the graphQL query filters"""
    facet_key: list=None
    keys: list=None
    date_range: list=None

user_group_hierarchy_levels = ["__missing__", "1", "2", "3", "4"]
provider_hierarchy_levels = ["__missing__", "1", "2", "3", "4"]
########################## Variables / Custom Classes ##########################



########################## Common/Helper Methods ##########################

def print_query(query: str, variables: str):
    print(":::::: query ::::::\n", query)
    print(":::::: variables ::::::\n", variables)

def post_query(gql_query: str, gql_variables: str=None) -> dict:
    """Posts a GraphQL query

        Parameters:
            gql_query (str): 
                The query content
            gql_variables(str, optional):
                Additional variables and filters for the query

        Returns:
            parsed_response (dict):
                Content of the query response as python dictionary
    """

    # differentiate between queries with variables and queries without
    if gql_variables:
        data = {"query": gql_query, "variables": gql_variables}
    else:
        data = {"query": gql_query}

    response = requests.post(
        url= lix.URLS.leanix_graphql, # get base URL for LeanIX GrpahQL API
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        data=json.dumps(data)    
    )
    
    log.info(f"graphql query response code: {response.status_code}")
    # Raises HTTPError, if one occurs.
    response.raise_for_status()
    # Fonvert response content (text) to a dict with json.loads()
    parsed_response = json.loads(response.text)
    return parsed_response

# Convert all factSheets to df
def factSheets_to_df(allFactSheets : dict) -> pd.DataFrame:
    """Creates a Pandas DataFrame out of the FactSheet"s attributes

        Parameters:
            allFactSheets (dict):
                The Fact Sheets attributes

        Returns:
            pd.DataFrame:
                A Pandas DataFrame 

        Examples:
            >>> factSheets_to_df(query_apps(facet_filters, on_app_nodes, on_node_nodes)
            Example response: 
            `"data": {"allFactSheets": {"edges": [{"node": 
            {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX", 
            "bankId", "XXXXXXX", 
            "displayName": "XXXXXXX", 
            "type": "Application", 
            "apptype": "web_app", }}`, 
            ...
            
            -> The DataFrame will have the following columns: 
            `[id, displayName, bankId, type, apptype]`
    """

    # get all nodes of the Fact Sheet
    nodes = allFactSheets["data"]["allFactSheets"]["edges"]
    # convert the nodes into a dataframe
    df = json_normalize(nodes)
    #df.info()
    # clean df column names by removing the prefix "node." from the name of the columns, e.g. node.displyName --to--> displayName
    df.columns = [col_name.removeprefix("node.") for col_name in df]
    return df

# Convert all LogEvents of all apps to Pandas DataFrame enteries
def application_logEvents_to_df(logEvents : dict) -> pd.DataFrame :
    """Creates a Pandas DataFrame out of the LogEvents FactSheet"s attributes

        Parameters:
            logEvents (dict):
                The LogEvents attributes

        Returns:
            pd.DataFrame:
                A Pandas DataFrame 

        Examples:
            >>> application_logEvents_to_df(logEvent)
            Example response: 
            `"data": {"allFactSheets": {"edges": [{"node": 
            {"id": "XXXXXXX", 
            "path", "/availabilityDescription", 
            "newValue": "best effort",
            "user": {"displayName": "XXXXXXX"}}}`, 
            ...
            
            -> The DataFrame will have the following columns: 
            `["event_id", "path", "newValue", "user_name", "createdAt"]`
    """

    if len(logEvents) == 0:
        assert "Provided logEvents dict is empty"
    nodes = logEvents["data"]["allLogEvents"]["edges"]
    df = json_normalize(nodes)

    #df.info()
    # remove the node from the name of the columns, e.g. node.displyName --to--> displayName
    df.columns = [col_name.removeprefix("node.") for col_name in df]
    df = df.filter(["id", "path", "newValue", "user.displayName", "createdAt"])
    df.columns = ["event_id", "path", "newValue", "user_name", "createdAt"]
    return df

def _get_gql_query_from_file(file_path : str) -> list:
    """Reads the GraphQL query from `.txt` file

        Parameters:
            file_path (str):
                The path the query `.txt` file

        Returns:
            list:
                List contaning the query and query variables
    """
    query_text = {}
    with open(file_path, "r") as file:
        for i in range(2):
            text = ""
            for line in file:
                if line != "\n":
                    text += line  
                else: # if the line is empty (only whitespace)
                    break
            query_text[i] = text
    return query_text

def query_app_allLogEvents_by_id(id: str) -> dict:
    """Query log events of an application by using the distinct LeanIX ID of that app (factSheetId)

        Parameters:
            id (str):
                ID of factSheet, i.e. ID of application

        Returns:
            parsed_response (dict):
                Content of the query response as python dictionary
    """

    template = query_temp.app_logEvents_by_id_query.replace("FACT_SHEET_ID", id)
    parsed_response = post_query(template)

    return parsed_response

def _convert_gql_query_from_txt(file_path : str) -> dict:
    """Helper method which reads a GraphQL query from `.txt` file and returns a dictionary `query_data = {"query": ..., "variables": ...}`
        
        Parameters:
            file_path (str):
                Path to the query `.txt` file

        Returns:
            query_data (dict):
                dictionary containing the query and it"s variables
    """

    query_data = {}
    text = _get_gql_query_from_file(file_path)
    query_data["query"] = text[0]
    query_data["variables"] = text[1]
    return query_data

def _apply_date_range_filter(date_range: list=None) -> str:
    """Helper method to apply a date range to a custom GraphQL filter template
    
        Parameters:
            date_range (list):
                _from = date_range[0],
                _to = date_range[1]

        Returns:
            applied_date_range (str): 
                The modified date range filter
    """
    
    filter = Template(str(_get_facet_filter_template("date_range")))
    applied_date_range = filter.safe_substitute(_from = str(date_range[0]), _to=str(date_range[1]))
    applied_date_range = applied_date_range.removeprefix("{")
    
    print("Applied Date Range Filter:", applied_date_range)

    return applied_date_range

def _apply_filters_to_query_variables(facet_filters: FilterTemplate=None) -> str:
    """Helper method which replaces placeholders in the query variables with a list of actual filters
    
        Examples
        --------
            Before: Query variables by default (placeholder: `${facet_filters}`):
                >>> {"filter": {
                "facetFilters":
                [
                ${facet_filters}
                ]}}

            After: Query variables after applying filters (filters: applications with an active lifecycle status):
                >>>  {"filter": {
                "facetFilters":
                [
                {"facetKey": "FactSheetTypes",
                "keys": ["Application"]}, 
                {"facetKey": "lifecycle", "operator": "OR", "keys": ["active"]
                ]}} 
    """
    
    if facet_filters:
        applied_filters = ""
        for filter_label in facet_filters:
            filter_template = _get_facet_filter_template(filter_label)
            _keys: list
            _date_range: list
            _keys = facet_filters[filter_label]["keys"]
            # if the facet_key is given
            if "facet_key" in facet_filters[filter_label]:
                _facet_key = facet_filters[filter_label]["facet_key"]
                applied_filters += apply_filter_to_template(filter_template=filter_template, filter_values=_keys, facet_key= _facet_key) + ", "
            else:
                applied_filters += apply_filter_to_template(filter_template=filter_template, filter_values=_keys) + ", "
            
            # if the date_range is given
            if "date_range" in facet_filters[filter_label]:
                _date_range = facet_filters[filter_label]["date_range"]
                # remove the closing bracket from the facetFilter to be able to add a date_range filter
                applied_filters = applied_filters.removesuffix("}, ")
                applied_filters += "," + _apply_date_range_filter(date_range=_date_range) + ", "
        
        applied_filters = _clean_filter_syntax(applied_filters)

        return applied_filters
    else:
        return ""

def _replace_query_variables(query_variables: dict, applied_filters: str):
    """Helper method which replaces a placeholder in the query variables with a list of filters"""

    all_facet_templates = Template(query_variables)
    query_variables = all_facet_templates.substitute(facet_filters = str(applied_filters))
    return query_variables

def _get_facet_filter_template(filter:str) -> str:
    """Helper getter method which searchs and gets for a given filter in filter template dictionary"""

    if filter in filter_temp.filter_templates:
        return filter_temp.filter_templates[filter]

def _add_on_factSheet_nodes(query: str, nodes: list) -> str:
    """Helper method which adds additional on-factScheet-nodes to query"""

    nodes_list = [f"{node} " for node in nodes]
    nodes_str = "".join(nodes_list)
    modified_query = query.replace(ADDTIONAL_FACTSHEET_NODES, nodes_str)
    print("Added on-factSheet-nodes:", nodes)
    return modified_query

def _add_on_node_nodes(query: str, nodes: list) -> str:
    """Helper method which adds additional on-node-nodes to query"""

    nodes_list = [f"{node} " for node in nodes]
    nodes_str = "".join(nodes_list)
    modified_query = query.replace(ADDTIONAL_NODE_NODES, nodes_str)
    print("Added on-node-nodes:", nodes)
    return modified_query

def _clean_query(query: str) -> str:
    """Helper method which removes all query parts within and including hastags using regex

        Examples
        --------
            Before: Uncleaned query (placeholder:`#ADDTIONAL_FACTSHEET_NODES#`):
                >>> ... on Application {
                id
                displayName
                #ADDTIONAL_FACTSHEET_NODES#
                }}} 

            After: Cleaned query:
            >>>  ... on Application {
                id
                displayName
                }}} 
    """
    clean_query = re.sub(f"#([^#]+)#", "", query)
    return clean_query

def _clean_filter_syntax(filter: str) -> str:
    """Helper method to clean a GraphQL filter syntax"""

    # remove the last comma ", " because otherwise the query filter's syntax is incorrect
    filter = filter.removesuffix(", ")
    # replace all single quotes with double quotes because json keys must be wrappped in double quotes 
    clean_filter = filter.replace("\'", "\"")
    return clean_filter

def apply_filter_to_template(filter_template: FilterTemplate, filter_values: list=None, facet_key: str=None) -> str:
    """Helper method to apply filter parameters `keys` to custom GraphQL filter templates"""

    filter = Template(str(filter_template))
    applied_filter = filter.safe_substitute(keys = str(filter_values))

    if facet_key:
        applied_filter = applied_filter.replace("${facet_key}", str(facet_key))
    
    # Example: replace ["["Application"]"]  by  ["Application"]
    # Query syntax will not be correct otherwise!
    applied_filter = applied_filter.replace("[\'[", "[").replace("]\']", "]")

    print("Applied Filters:", applied_filter)

    return applied_filter

def _compine_in_apps_df(apps_df: pd.DataFrame, df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """Helper method to compine/add df of an application related attribut/data to another df (intened for apps_overview_bool function)"""
    apps_df.set_index(apps_df["id"], inplace= True)
    df.set_index(df["id"], inplace= True)
   
    col_ls = ["missing_bankId", "missing_apptype","quality_seal_broken", "quality_seal_borken_by_Python_Interaction", 
              "no_dsg", "missing_dsg", "missing_reporting_tag", "missing_functional_suitability", 
              "missing_business_criticality"]

    # add column
    apps_df[col_name] = None

    for entry in apps_df.index:
            value = np.nan
            if entry not in df.index:
                value = True
            else:
                value = False

            # the boolean value has to be inverted for the attribut in col_ls
            if (col_name in col_ls):
                value = not value
            
            #print(value)
            apps_df.at[entry, col_name] = value     
    return apps_df

def _count_relations(df: pd.DataFrame, relation: str, count_factSheet_type: str) -> pd.DataFrame:
    """Helper method that counts the count of specific realtion an application has
    For example `Process_count` = count of process an application has
    
    Returns:
        pd.DataFrame:
        DataFrame contains: `[id, displayName, bankId, relation, relation_count]`
        Example: `[id, displayName, bankId, relApplicationToProcess,	Process_count]`
    """

    # new col in df for count
    new_col = f"{count_factSheet_type}_count"
    df[new_col] = 0

    # loop over all applications
    for i in range(len(df.index)):
        items = ""
        count = 0
        # when an application has no or only one 
        edges = f"{relation}.edges"
        if str(df[edges][i]).count("node") == 0:
            continue
        # when an applicaiton has multiple  
        elif str(df[edges][i]).count("node") > 1:
            for j in range(len(df[edges][i])):
                s = str(df[edges][i][j]).replace("\'", "\"")

                if count_factSheet_type == "Process":
                    s = s.replace("\\xa0", " ") # one of the process has a "\xa0" character (NO-BREAK SPACE) and most be replaced --> valid JSON
                
                item = json.loads(s)
                items += item["node"]["factSheet"]["displayName"] + ", "
                count += 1
        else:
            s = str(df[edges][i]).removeprefix("[").removesuffix("]").replace("\'", "\"")
            item = json.loads(s)
            items = item["node"]["factSheet"]["displayName"]
            count += 1
            
        df.at[i, new_col] = count

        df.at[i, edges] = items

    # rename column
    df.rename(columns={edges: relation}, inplace= True)
    df[new_col] = df[new_col].astype(int)

    return df 

def _lifecycles_to_dict(lifecycle : str) -> dict:
    """Helper method to convert lifecycle entries to dictionary"""
    s = str(lifecycle)
    # Convert string to list
    parsed_list = ast.literal_eval(s)
    # Convert to dictionary with date objects
    lifecycle_dict = {key: date.fromisoformat(value).strftime("%Y-%m") for key, value in parsed_list} 
    return lifecycle_dict

def _subscriptions_to_dict(subscription : str) -> dict:
    """Helper method to turn subscription data/information into a dictionary"""
    s = str(subscription)
    # Convert string to list
    parsed_list = ast.literal_eval(s) 
    # Convert to dictionary
    subscriptions_dict = {key: tuple([value1, value2]) for key, value1, value2 in parsed_list}    
    return subscriptions_dict

def _check_condition(df: pd.DataFrame, mask_df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    "Helper method for check_apps_dsg_field_correctness()"
    mask_df.set_index("id", inplace= True)
    for id in mask_df.index:
            df.at[id, col_name] = True
    return df

############ extract and clean data methods for data frames

def _extract_applications(df: pd.DataFrame, factSheet_type: str) -> pd.DataFrame:
    """Helper method to extract the Application used by (has relation to) a FactShee"""
    i = 0
    intial_index = df.index # indices of the df
    col_name = f"rel{factSheet_type}ToApplication.edges"
    app_nb = f"Cardinality {factSheet_type} : apps" # number of apps that use the ITComponent
    df[app_nb] = 0

    for rel in df[col_name]:
        if rel != []:
            #print(rel)
            #print("len:", len(rel))
            for j in range(len(rel)):
                app = ""
                app_id = rel[j]["node"]["factSheet"]["id"]
                app_name = rel[j]["node"]["factSheet"]["displayName"]
                app = (str(app_id))

                if len(rel) > 1 and j > 0:
                        # copy the current row
                        new_row = df.loc[i].copy()
                        # add the new row the original DataFrame
                        df = df._append([new_row], ignore_index=True)
                        # modify the subscription of the newly add row 
                        df.at[df.index[-1], col_name] = app # modify entry in column "subscriptions.edges" at the correct index. 
                else:
                    df.at[intial_index[i], col_name] = app # modify entry in column "subscriptions.edges" at the correct index.
                df.at[intial_index[i], app_nb] =  len(rel) 
        i += 1

    df = df.sort_index().reset_index(drop=True)   
    return df 

def _extract_subscriptions(df: pd.DataFrame) -> pd.DataFrame:
    """Helper method to extract the Subscriptions of a FactSheet 
        
        Example: 
            {email: role} --> {'max.mustermann@bank.com': ('RESPONSIBLE', 'GPV')}
    """

    i = 0
    intial_index = df.index # indices of the df

    for rel in df["subscriptions.edges"]:
        if rel != []:
            #print("len:", len(rel))
            
            for j in range(len(rel)):
                users = []
                user_email = rel[j]["node"]["user"]["email"]
                user_role = rel[j]["node"]["type"]
                role = []
                if rel[j]["node"]["roles"] != []:
                        role = rel[j]["node"]["roles"][0]["name"]
                users = [user_email, user_role, role]

                # Note: the users must be in [[]] list otherwise the _subscriptions_to_dict() function will through a "ValueError: too many values to unpack (expected 3)"
                # check function _subscriptions_to_dict() for more details
                users_dict = _subscriptions_to_dict([users])

                if len(rel) > 1 and j > 0:
                    # copy the current row
                    new_row = df.loc[i].copy()
                    # add the new row the original DataFrame
                    df = df._append([new_row], ignore_index=True)
                    # modify the subscription of the newly add row 
                    df.at[df.index[-1], "subscriptions.edges"] = users_dict # modify entry in column "subscriptions.edges" at the correct index. 
                else:
                    df.at[intial_index[i], "subscriptions.edges"] = users_dict # modify entry in column "subscriptions.edges" at the correct index.
        i += 1

    df = df.sort_index().reset_index(drop=True)

    return df
############ extract and clean data methods for data frames

########################## Save DataFrame to File 
def save_df_as_csv(df : pd.DataFrame, target_file: str, target_dir: str= "data"):
    """Saves Pandas DataFrame as CSV

        The file name is {target_file}_df_dateFormat (%Y%m%d%H%M%S)
        Example: application_df on 2022.01.01 at 19:40:55 -> `applications_df_20220101194055` 
        
        Parameters:
            df (pd.DataFrame):
                The Pandas DataFrame to save
            target_file (str):
                Name of the target file
            target_dir (str, optional):
                Name of the target folder, default: "data"
    """

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y%m%d%H%M%S")
    filename = f"{target_dir}/{target_file}_df_{formatted_datetime}"
    df.to_csv(filename, index= False)

def save_df_as_excel(df : pd.DataFrame, target_file: str, target_dir: str= "data"):
    """Saves Pandas DataFrame as Excel `.xlsx`

        The file name is {target_file}_df_dateFormat (%Y%m%d%H%M%S)
        Example: application_df on 2022.01.01 at 19:40:55 -> `applications_df_20220101194055` 
        
        Parameters:
            df (pd.DataFrame):
                The Pandas DataFrame to save
            target_file (str):
                Name of the target file
            target_dir (str, optional):
                Name of the target folder, default: "data"
    """

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y%m%d%H%M%S")
    filename = f"{target_dir}/{target_file}_df_{formatted_datetime}.xlsx"
    with pd.ExcelWriter(filename, mode='w') as writer:
        df.to_excel(writer, index= False)

########################## Save Data Frame to File 

########################## Read & Post GraphQL Queries From File 
def post_query_from_file(file_name: str) -> dict:
    """Reads GraphQL query from a `.txt` file and post the query

        Parameters:
            file_name (str): 
                The name of the query file
                
        Returns:
            parsed_response (dict):
                Content of the query response as python dictionary

        Note:
        -----
        - The query file must be in directory `queries_txt`
        - The query variables and actual query body must be separated by an empty line
    """

    QUERY_PATH = f"{QUERIES_DIR}/{file_name}.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    parsed_response = post_query(query_data["query"], query_data["variables"])
    return parsed_response
########################## Read & Post GraphQL Queries From File 

########################## Common/Helper Methods ##########################


########################## GraphQL Queries ##########################

# path to "queries_txt" directory, to have access to queries .txt files
SCRIPT_PATH = os.path.dirname( __file__ )
QUERIES_DIR = os.path.join( SCRIPT_PATH, '..', 'queries_txt')

def query_bankId(id: str) -> str:
    """Query text, to get bank ID of an application by referencing it LeanIX ID"""
    template = query_temp.bankID_query.replace("FACT_SHEET_ID", id)
    query = post_query(template)
    return query

def query_apps(facet_filters: dict=None, on_app_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all appications on LeanIX with help of a GQL query stored in `.txt` file
    
        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_app_nodes (list, optional):
                Additional on_app_nodes (properties of an application) to be added to the query, e.g., `id`, `displyName`, `lifecycle`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `[id, displayName, level]` of an application (default = when no additional `on_app_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all application with a broken quality seal in addition to other properties like: `apptype`, `level`, ...

            Example 1: Generically define attributes in advance
            >>> filters = {"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
            >>> app_nodes = ["apptype", "qualitySeal"]
            >>> node_nodes = ["level", "status"]
            >>> query_apps(facet_filters= filters, on_app_nodes= app_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
            >>> query_apps(facet_filters= {"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_app_nodes= ["apptype", "qualitySeal"], on_node_nodes= ["level", "status"])
        
            Example response: 
                    >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                    {"id": "XXXXXXX-74e3-4952-be59-XXXXXXX",
                    "bankId": "XXXXX"
                    "displayName": "XXXXXXX", 
                    "apptype": "web_app",
                    "qualitySeal": "BROKEN",
                    "level": 1,
                    "status": "ACTIVE" }}`, 
                    ...
    """

    QUERY_PATH = f"{QUERIES_DIR}/apps.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # apply facet filters when given
    if facet_filters:
        applied_filters = _apply_filters_to_query_variables(facet_filters)
        query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)
    else:
        query_data["variables"] = _replace_query_variables(query_data["variables"], "")

    # add Application's (FactSheet) nodes to query
    if on_app_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_app_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are given
    query_data["query"] = _clean_query(query_data["query"])

    print("-------------------GET FACTSHEET QUERY------------------------")
    print_query(query_data["query"], query_data["variables"])
    print("-------------------GET FACTSHEET QUERY------------------------\n")

    apps = post_query(query_data["query"], query_data["variables"])

    return apps

def query_providers(facet_filters: dict=None, on_provider_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all providers on LeanIX with help of a GQL query stored in `.txt` file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_provider_nodes (list, optional):
                Additional on_provider_nodes (properties of a provider) to be added to the query, e.g., `id`, `displyName`, `lifecycle`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `[id, displayName, level]` of a provider (default = when no additional `on_provider_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all providers with a broken quality seal in addition to other properties like: `type`, `createdAt`, `status`, ...
            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": "Provider"}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> provider_nodes = ["type", "qualitySeal"]
                >>> node_nodes = ["createdAt", "status"]
                >>> query_providers(facet_filters= filters, on_provider_nodes= provider_nodes, on_node_nodes= node_nodes)
                
            Example 2: Specifing attributes when calling the function
                >>> query_providers(facet_filters= {"fact_sheet_type": {"keys":["Provider"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_provider_nodes= ["type", "qualitySeal"], on_node_nodes= ["createdAt", "status"])

            Example response: 
                >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-74e3-4952-be59-XXXXXXX",
                "displayName": "XXXXXXX", 
                "level": 1,
                "relToParent.edges": [{"node": {"factSheet": {"displayName": ...}]
                "type": "Provider",
                "qualitySeal": "BROKEN",
                "createdAt": "2019-06-21T13:21:19.828Z",
                "status": "ACTIVE" }}`, 
                ...
    
    """

    QUERY_PATH = f"{QUERIES_DIR}/provider.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # apply facet filters when given
    if facet_filters:
        applied_filters = _apply_filters_to_query_variables(facet_filters)
        query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)
    else:
        query_data["variables"] = _replace_query_variables(query_data["variables"], "")

    # add provider nodes to query
    if on_provider_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_provider_nodes)

    # add on_node_nodes to query
    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are given
    query_data["query"] = _clean_query(query_data["query"])

    print_query(query_data["query"], query_data["variables"])

    provider = post_query(query_data["query"], query_data["variables"])

    return provider

def query_interfaces(facet_filters: dict=None, on_interface_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all Interfaces on LeanIX with help of a GraphQL query stored in `.txt` file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_interface_nodes (list, optional):
                Additional on_interface_nodes (properties of an interface) to be added to the query, e.g. `displyName`, `description`, `type`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `id, displayName` of an interface (default = when no additional `on_interface_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all interfaces `id, displayName` in addition to other properties like: `qualiySeal`, `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["Interface"]}}
                >>> interface_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["level", "status"]
                >>> query_interfaces(facet_filters= filters, on_interface_nodes= interface_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
                >>> query_interfaces(facet_filters= {"fact_sheet_type": {"keys":["Interface"]}}, on_interface_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])

            Example response: 
                    >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                    {"id": "XXXXXXX-XXXX-4952-XXXX-XXXXXXX",
                    "displayName": "XXXXXXX", 
                    "description": "xxx xxxx xxxx xxxx xxxx",
                    "qualitySeal": "BROKEN",
                    "status": "ACTIVE",
                    "level": 1 }}`, 
                    ...
    """

    QUERY_PATH = f"{QUERIES_DIR}/interface.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # apply facet filters when given
    if facet_filters:
        applied_filters = _apply_filters_to_query_variables(facet_filters)
        query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)
    else:
        query_data["variables"] = _replace_query_variables(query_data["variables"], "")

    # add on Interface nodes to query
    if on_interface_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_interface_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are given
    query_data["query"] = _clean_query(query_data["query"])

    print_query(query_data["query"], query_data["variables"])

    interfaces = post_query(query_data["query"], query_data["variables"])

    return interfaces

def query_interface_allLogEvents_by_id(id: str):
    """Query Log Events of an interface by using the distinct LeanIX ID of each app (factSheetId)

        Parameters:
            id (str):
                ID of factSheet, i.e. ID of interface

        Returns:
            query (str):
                Query which is used get all Log Events of factSheet (interface)
    """

    template = query_temp.interface_logEvents_by_id_query.replace("FACT_SHEET_ID", id)
    query = post_query(template)

    return query

def query_user_groups(facet_filters: dict=None, on_user_group_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all user groups on LeanIX with help of a GQL query stored in `.txt` file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_user_group_nodes (list, optional):
                Additional on_user_group_nodes (properties of a user group) to be added to the query, e.g., `id`, `displyName`, `lifecycle`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `[id, displayName, level]` of a user group (default = when no additional `on_user_group_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all user groups with a broken quality seal in addition to other properties like: `type`, `createdAt`, `status`, ...
            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": "UserGroup"}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> user_group_nodes = ["type", "qualitySeal"]
                >>> node_nodes = ["createdAt", "status"]
                >>> query_user_groups(facet_filters= filters, on_user_group_nodes= user_group_nodes, on_node_nodes= node_nodes)
                
            Example 2: Specifing attributes when calling the function
                >>> query_user_groups(facet_filters= {"fact_sheet_type": {"keys":["UserGroup"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_user_group_nodes= ["type", "qualitySeal"], on_node_nodes= ["createdAt", "status"])

            Example response: 
                >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX",
                "displayName": "XXXXXXX", 
                "level": 1,
                "relToParent.edges": [{"node": {"factSheet": {"displayName": ...}]
                "type": "UserGroup",
                "qualitySeal": "BROKEN",
                "createdAt": "2019-06-21T13:21:19.828Z",
                "status": "ACTIVE" }}`, 
                ...
    
    """

    QUERY_PATH = f"{QUERIES_DIR}/user_group.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # apply facet filters when given
    if facet_filters:
        applied_filters = _apply_filters_to_query_variables(facet_filters)
        query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)
    else:
        query_data["variables"] = _replace_query_variables(query_data["variables"], "")

    # add user_group nodes to query
    if on_user_group_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_user_group_nodes)

    # add on_node_nodes to query
    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are given
    query_data["query"] = _clean_query(query_data["query"])

    print_query(query_data["query"], query_data["variables"])

    user_group = post_query(query_data["query"], query_data["variables"])

    return user_group

def query_activities(facet_filters: dict=None, on_activity_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all Activities on LeanIX with help of a GQL query stored in .txt file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_activity_nodes (list, optional):
                Additional on_activity_nodes (properties of an activity) to be added to the query, e.g. `displyName`, `description`, `type`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `id, displayName` of an activity (default = when no additional `on_activity_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all activities `id, displayName` in addition to other properties like: `qualiySeal`, `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["Activity"]}}
                >>> activity_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["level", "status"]
                >>> query_business_capabilities(facet_filters= filters, on_activity_nodes= activity_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
                >>> query_activities(facet_filters= {"fact_sheet_type": {"keys":["Activity"]}}, on_activity_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])

            Example response: 
                    >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                    {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX",
                    "displayName": "XXXXXXX", 
                    "description": "xxx xxxx xxxx xxxx xxxx",
                    "qualitySeal": "BROKEN",
                    "status": "ACTIVE",
                    "level": 1 }}`, 
                    ...
    """

    QUERY_PATH = f"{QUERIES_DIR}/activity.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # if no facet_filters are given, a default filter is applied
    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["Activity"]}}

    # apply facet filters when given
    applied_filters = _apply_filters_to_query_variables(facet_filters)
    query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)

    # add on Activity nodes to query
    if on_activity_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_activity_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are given
    query_data["query"] = _clean_query(query_data["query"])

    print_query(query_data["query"], query_data["variables"])

    activities = post_query(query_data["query"], query_data["variables"])

    return activities

def query_business_capabilities(facet_filters: dict=None, on_business_capability_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all Business Capabilities on LeanIX with help of a GQL query stored in .txt file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_business_capability_nodes (list, optional):
                Additional on_business_capability_nodes (properties of a business capability) to be added to the query, e.g. `displyName`, `description`, `bankId`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `id, displayName` of a business_capability (default = when no additional `on_business_capability_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all business capability with a broken quality seal in addition to other properties like: `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["BusinessCapability"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> business_capability_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["level", "status"]
                >>> query_business_capabilities(facet_filters= filters, on_business_capability_nodes= business_capability_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
             >>> query_business_capabilities(facet_filters= {"fact_sheet_type": {"keys":["BusinessCapability"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_business_capability_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])

            Example response: 
                >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX",
                "bankId": "XXXXX"
                "displayName": "XXXXXXX", 
                "description": "xxx xxxx xxxx xxxx xxxx",
                "qualitySeal": "BROKEN",
                "status": "ACTIVE",
                "level": 1 }}`, 
                ...
    """

    QUERY_PATH = f"{QUERIES_DIR}/business_capability.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # if no facet_filters are given, a default filter is applied
    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["BusinessCapability"]}}

    # apply facet filters when given
    applied_filters = _apply_filters_to_query_variables(facet_filters)
    query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)

    # add business capability nodes to query
    if on_business_capability_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_business_capability_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are givens
    query_data["query"] = _clean_query(query_data["query"])

    print_query(query_data["query"], query_data["variables"])

    business_capabilities = post_query(query_data["query"], query_data["variables"])

    return business_capabilities

def query_bankId_business_capability(id: str) -> str:
    """Query the bankId of an application by referencing it LeanIX ID

            Parameters:
                id (str): 
                    ID of factSheet, i.e. ID of business capability
                
            Returns:
                bankId (str):
                    bankId of factSheet, i.e. bankId of business capability

            Examples:
                >>> query_bankId_business_capability(id= "XXXXXXX-XXXX-XXXX-be59-XXXXXXX")
                >>> "BCXX03"
    """

    template = query_temp.bankID_business_capability_query.replace("FACT_SHEET_ID", id)
    bankId = post_query(template)["data"]["factSheet"]["bankId"]
    return bankId

def query_ITComponents(facet_filters: dict=None, on_ITComponent_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all IT Components on LeanIX with help of a GQL query stored in .txt file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_ITComponent_nodes (list, optional):
                Additional on_ITComponent_nodes (properties of a IT component) to be added to the query, e.g. `displyName`, `description`, `bankId`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `id, displayName` of a IT_component (default = when no additional `on_ITComponent_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all IT-Components with a broken quality seal in addition to other properties like: `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["ITComponent"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> ITComponent_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["level", "status"]
                >>> query_ITComponent(facet_filters= filters, on_ITComponent_nodes= ITComponent_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
             >>> query_ITComponents(facet_filters= {"fact_sheet_type": {"keys":["ITComponent"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_ITComponent_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])

            Example response: 
                >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX",
                "displayName": "XXXXXXX", 
                "description": "xxx xxxx xxxx xxxx xxxx",
                "qualitySeal": "BROKEN",
                "status": "ACTIVE",
                "level": 1 }}`, 
                ...
    """

    QUERY_PATH = f"{QUERIES_DIR}/IT_component.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # if no facet_filters are given, a default filter is applied
    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["ITComponent"]}}

    # apply facet filters when given
    applied_filters = _apply_filters_to_query_variables(facet_filters)
    query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)

    # add ITComponent nodes to query
    if on_ITComponent_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_ITComponent_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are givens
    query_data["query"] = _clean_query(query_data["query"])

    print_query(query_data["query"], query_data["variables"])

    ITComponents = post_query(query_data["query"], query_data["variables"])

    return ITComponents

def query_processes(facet_filters: dict=None, on_process_nodes: list=None, on_node_nodes: list=None) -> dict:
    """Query all Processes on LeanIX with help of a GQL query stored in .txt file

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_process_nodes (list, optional):
                Additional on_process_nodes (properties of a process) to be added to the query, e.g. `displyName`, `description`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            parsed_response (dict):
                Content (text) of the query response as python dictionary
                By default the response contains `[id, displayName, adonisVersion, externalId]` of a process (default = when no additional `on_process_nodes` or `on_node_nodes` are added)

        Examples:
            These examples get all processes with a broken quality seal in addition to other properties like: `type`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["Process"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> process_nodes = ["type"]
                >>> node_nodes = ["level", "status"]
                >>> query_processes(facet_filters= filters, on_process_nodes= process_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
             >>> query_processes(facet_filters= {"fact_sheet_type": {"keys":["Process"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_process_nodes= ["type"], on_node_nodes= ["level", "status"])

            Example response: 
                >>>  `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX",
                "displayName": "XXXXXXX", 
                "description": "xxx xxxx xxxx xxxx xxxx",
                "qualitySeal": "BROKEN",
                "status": "ACTIVE",
                "level": 1 }}`, 
                ...
    """

    QUERY_PATH = f"{QUERIES_DIR}/process.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # if no facet_filters are given, a default filter is applied
    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["Process"]}}

    # apply facet filters when given
    applied_filters = _apply_filters_to_query_variables(facet_filters)
    query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)

    # add Application's nodes to query
    if on_process_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_process_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex
    # to ensure query syntax is correct when no facetFilters are givens
    query_data["query"] = _clean_query(query_data["query"])
    print_query(query_data["query"], query_data["variables"])
    
    processes = post_query(query_data["query"], query_data["variables"])
    return processes

########################## GraphQL Queries ##########################


########################## GraphQL Queries To Pandas DataFrame ##########################

####################################### Application

def apps_overview_values(sort_values_by_col: str="displayName"):
    """Returns an Overview (Pflichtfelder) of all the applications on LeanIX (values) in form of a Pandas DataFrame

        Parameters:
            sort_values_by_col (str, optional): 
                sort the df row by this column's values

        Returns:
            pd.DataFrame:
            By default the DataFrame contains: 
                `[id, displayName, bankId, completion.percentage, qualitySeal, lxState,	apptype,
                ApplicationLifecycle.asString, ApplicationLifecycle.phases, app_subscriptions, 
                subscription_count, relApplicationToITComponent, ITComponent_count, 
                relApplicationToProcess, Process_count, relApplicationToUserGroup, UserGroup_count, 
                datamaster, completeClientDatabase, massDataQueries, deletionProcess, holdOffTime
                ,backup, personDataProtectionAgreements, dsg_comment, reporting_tag, description]`
            of an application (default = when no additional `on_app_nodes` or `on_node_nodes` are added in get_apps() method)
    """

    df = get_apps_completion()
    df0 = get_apps(on_app_nodes= ["qualitySeal", "lxState"])
    df1 = get_apps_apptype()
    df2 = get_apps_lifecycles()
    df3 = get_apps_subscriptions()
    df4 = get_apps_IT_components()
    df5 = get_apps_processes()
    df6 = get_apps_user_groups()
    df7 = get_apps_dsg_fields()
    df8 = get_apps_descriptions()


    dfs = [df, df0, df1, df2, df3, df4, df5, df6, df7, df8]
    # outer join all dfs to prserve missing values (for example when "bankId" is missing)
    merged_df = reduce(lambda left, right: pd.merge(left, right, on=["id","bankId", "displayName"], how= "outer"), dfs)
    

    merged_df["bankId"] = merged_df["bankId"].replace("", None)
    # changet column "completion.percentage" and count-columns to type int
    merged_df["completion.percentage"] = merged_df["completion.percentage"].fillna(0).astype("int")
    for col in merged_df.columns:
        if str(col).count("count") >= 1:
            merged_df[col]  = merged_df[col].fillna(0).astype("int")
    
    # get rid of duplications (because of the outer-join duplicates are created with only missing values in multiple columns)
    df_cleaned = merged_df.groupby("id", dropna=False).first().sort_values(by= sort_values_by_col, axis= 0).reset_index()
            
    return df_cleaned
    
def apps_overview_bool(sort_values_by_col: str="displayName"):
    """Returns an Overview (Pflichtfelder) of all the applications on LeanIX (boolean values) in form of a Pandas DataFrame

        Parameters:
            sort_values_by_col (str, optional): 
                sort the df row by this column's values

        Returns:
            pd.DataFrame:
            By default the DataFrame contains: 
            `[id, displayName, bankId, completion.percentage, missing_bankId, missing_apptype, IT-Component, subscription, quality_seal_broken, 
            lifecycle, licence, process, missing_dsg, missing_reporting_tag, missing_functional_suitability, missing_business_criticality]`
            of an application

        Note: 
        ----
            - The function takes 1-2 min longer if get_apps_quality_seal_broken_by_python_interaction() is included
    """

    df = get_apps_completion()
    
    df0 = get_apps_with_missing_bankId()
    df1 = get_apps_with_missing_apptype()
    df2 = get_apps_with_no_IT_component()
    df3 = get_apps_with_no_subscription()
    df4 = get_apps_with_broken_quality_seal()
    #df5 = get_apps_quality_seal_broken_by_python_interaction() # function takes 1-2 min longer if get_apps_quality_seal_broken_by_python_interaction() included
    df6 = get_apps_with_no_lifecycle()
    df7 = get_apps_with_no_licence()
    df8 = get_apps_with_no_process()
    #df9 = 
    df10 = get_apps_with_missing_dsg()
    df11 = get_apps_with_missing_reporting_tag()
    df12 = get_apps_with_missing_functional_suitability()
    df13 = get_apps_with_missing_business_criticality()
    #df14 = #add further functions accordingly 

    df = _compine_in_apps_df(df, df0, "missing_bankId")
    df = _compine_in_apps_df(df, df1, "missing_apptype")
    df = _compine_in_apps_df(df, df2, "IT-Component")
    df = _compine_in_apps_df(df, df3, "subscription")
    df = _compine_in_apps_df(df, df4, "quality_seal_broken") 
    #df = _compine_in_apps_df(df, df5, "quality_seal_borken_by_Python_Interaction")
    df = _compine_in_apps_df(df, df6, "lifecycle")
    df = _compine_in_apps_df(df, df7, "licence")
    df = _compine_in_apps_df(df, df8, "process")
    #df = _compine_in_apps_df(df, df9, "")
    df = _compine_in_apps_df(df, df10, "missing_dsg")
    df = _compine_in_apps_df(df, df11, "missing_reporting_tag")
    df = _compine_in_apps_df(df, df12, "missing_functional_suitability")
    df = _compine_in_apps_df(df, df13, "missing_business_criticality")
    #df = _compine_in_apps_df(df, df14, "") #specify column name accordingly

    apps_overview_df = df
    return apps_overview_df.sort_values(by= sort_values_by_col, axis= 0).reset_index(drop=True)

def get_apps(facet_filters: FilterTemplate=None, on_app_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all applications on LeanIX in form of a Pandas DataFrame

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_app_nodes (list, optional):
                Additional on_app_nodes (properties of an application) to be added to the query, e.g. `displyName`, `apptype`, `bankId`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application (default = when no additional `on_app_nodes` or `on_node_nodes` are added)

        Examples:
            These examples get all application with a broken quality seal in addition to other properties like: `apptype`, `level`, ...

            Example 1: Generically define attributes in advance
            >>> filters = {"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
            >>> app_nodes = ["apptype", "qualitySeal"]
            >>> node_nodes = ["level", "status"]
            >>> get_apps(facet_filters= filters, on_app_nodes= app_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
            >>> get_apps(facet_filters= {"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_app_nodes= ["apptype", "qualitySeal"], on_node_nodes= ["level", "status"])
    """

    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["Application"]}}

    # Applying .dropna(how="all") to df to filter to get remove all rows/entries with only NaN-values
    # this is useful in case the function get_ITComponents is called without arguments
    return factSheets_to_df(query_apps(facet_filters, on_app_nodes, on_node_nodes)).dropna(how= "all")

def get_apps_bankId_for_apps_leanix_ids_list(app_leanix_ids: list) -> pd.DataFrame:
    """Returns a Pandas DataFrame of bankId (BLKV Nummer) of one or a list of applications using the application LeanIX-Id

        Parameters:
            app_leanix_ids (list): 
                List of the Applications LeanIX-IDs
        
        Returns:
            pd.DataFrame: `[id, bankId]`
    """
    # list to store the leanixId of each app and their bank number
    apps_id_and_bankId = [[]]

    for id in app_leanix_ids:
        res = query_bankId(id)
        bank_number = res["data"]["factSheet"]["bankId"]
        #print(bank_number)
        apps_id_and_bankId.append([id, bank_number])
        # turn the list to a df 
        apps_id_and_bankId_df = pd.DataFrame(apps_id_and_bankId, columns=["leanIX_Id", "bankId"])
        apps_id_and_bankId_df.dropna(axis=0, how="all", inplace=True)

    return apps_id_and_bankId_df

def get_app_bankId_by_leanix_id(app_leanix_id: str) -> str:
    """Returns a bankId (BLKV Nummer) of a specific application using the application LeanIX-Id

        Parameters:
            app_leanix_id (str): 
                Applications LeanIX-IDs, e.g. Avaloq LeanIX-Id: "XXXXXXXX-XXXX-XXXX-94cd-XXXXXXXXXXXX"
        
        Returns:
            bankId (str)
    """

    res = query_bankId(app_leanix_id)
    bankId = res["data"]["factSheet"]["bankId"]
        
    return bankId

def get_apps_ids() -> pd.DataFrame:
    """Returns all applications on LeanIX in form of a Pandas  DataFrame 
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps()

def get_app_id_by_name(name: str):
    """Returns the `id` of an application with a certain name

        Parameters:
            name (str): 
                Name of the application
        
        Returns:
            new_app_id (str):
                `id` of the application

                *Note*: Raise an error if name is not found
    """
    # get the id of the newly create app
    leanix_apps = get_apps_ids()
    new_app_id = leanix_apps.loc[leanix_apps["displayName"] == name, "id"]
    # raise an error if name is not found
    new_app_id = new_app_id
    if new_app_id.empty:
        raise ValueError(f"Error: Application with name: {name} not found!")
    return new_app_id.iloc[0]

def get_apps_descriptions() -> pd.DataFrame:
    """Returns all applications on LeanIX in form of a Pandas  DataFrame 
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(on_node_nodes=["description"])

def get_apps_with_missing_bankId():
    """Returns all applications on LeanIX with no bankId 
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName]` of an application
    """
    df = get_apps().replace("", None)
    df = df[df["bankId"].isnull()]
    return df

def get_apps_apptype() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications and their type
        Applicaitons types: `[wep_app, mobile_app, client_app, service, component, datafeed]`

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, type]` of an application
    """
    return get_apps(on_app_nodes=["apptype"])

def get_apps_with_missing_apptype() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications without an apptype 
        Applicaitons types: `[wep_app, mobile_app, client_app, service, component, datafeed]`

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, type]` of an application
    """
    df = get_apps(on_app_nodes=["apptype"])
    df = df[df["apptype"].isnull()]
    return df

def get_apps_completion(sort_values_asc: bool=False) -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications and their completion in percent

        Parameters:
                sort_values_asc(bool): 
                    Sorts the rows of the DataFrame in ascending order by the `completion.percentage` column

        Returns:
            pd.DataFrame: `[id, displayName, bankId, completion.percentage]`
    """
    df = get_apps(on_app_nodes=["completion {percentage}"])
    df["completion.percentage"] = df["completion.percentage"].fillna(0).astype("int")
        
    if sort_values_asc:
        df = get_apps(on_app_nodes=["completion {percentage}"]).sort_values(by= "completion.percentage", axis=0)
    return df

def get_apps_IT_components() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all applications and their IT-Components
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relApplicationToITComponent, ITComponents_count]` of an application
    """

    # on_app_node for applications IT component
    relApplicationToITComponent = "relApplicationToITComponent { edges { node { factSheet { displayName id } } } }"
    df = get_apps(facet_filters= {"fact_sheet_type": {"keys":["Application"]},"IT_component":{"keys":[]}}, on_app_nodes=[relApplicationToITComponent])

    relation = "relApplicationToITComponent"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "ITComponents")

def get_apps_with_no_IT_component() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with no IT-Component

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """

    # on_app_node for applications IT component
    relApplicationToITComponent = "relApplicationToITComponent { edges { node { factSheet { displayName id } } } }"
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"IT_component":{"keys":["__missing__"]}}, on_app_nodes=[relApplicationToITComponent]).filter(["id",  "bankId", "displayName"])

def get_apps_processes() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all applications and their Process
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relApplicationToProcess, processes_count]` of an application
    """
    
    # on_app_node for applications processes
    relApplicationToProcess_query = "relApplicationToProcess { edges { node { factSheet { displayName id } } } }"
    df = get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"relation_application_to_process":{"keys":[]}}, on_app_nodes=[relApplicationToProcess_query])

    relation = "relApplicationToProcess"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "Process")

def get_apps_with_no_process() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications that have no process linked

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """

    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"relation_application_to_process":{"keys":["__missing__"]}})

def get_apps_user_groups() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all applications and their User Groups
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relApplicationToUserGroup, userGroups_count]` of an application
    """
    
    # on_app_node for applications user groups
    relApplicationToUserGroup = "relApplicationToUserGroup { edges { node { factSheet { displayName id } } } }"
    df = get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"relation_application_to_user_group":{"keys":[]}}, on_app_nodes=[relApplicationToUserGroup])

    relation = "relApplicationToUserGroup"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "UserGroup")

def get_apps_interfaces() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all applications and their Interfaces
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relConsumerApplicationToInterface, interfaces_count]` of an application
    """
    
    # on_app_node for applications interfaces
    relConsumerApplicationToInterface = "relConsumerApplicationToInterface { edges { node { factSheet { displayName id } } } }"
    df = get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"relation_application_to_interface":{"keys":[]}}, on_app_nodes=[relConsumerApplicationToInterface])

    relation = "relConsumerApplicationToInterface"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "Interface")

def get_apps_subscriptions() -> pd.DataFrame:
    """Returns a Pandas DataFrame of the subscriptions of each application
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, subscriptions.edges]` of an application
    """
    df = get_apps(on_app_nodes= [query_temp.app_subscriptions_query])

    # add col to count subscriptions
    df["subscription_count"] = 0

    i = 0
    indices = df.index # indices of the df
    for rel in df["subscriptions.edges"]:
        if rel != []:
            #print(rel)
            users = []
            #print("len:", len(rel))
            for j in range(len(rel)):
                user_email = rel[j]["node"]["user"]["email"]
                user_role = rel[j]["node"]["type"]
                role = []
                if rel[j]["node"]["roles"] != []:
                    role = rel[j]["node"]["roles"][0]["name"]
                #print(user_email, user_role, role) 
                users.append([user_email, user_role, role])
            #print("users:", users)
            users_dict = _subscriptions_to_dict(users)
            df.at[indices[i], "subscriptions.edges"] = users_dict # modify entry in column "subscriptions.edges" at the correct index
            df.at[indices[i], "subscription_count"] = len(users_dict)
        i += 1
    df["subscriptions.edges"] = df["subscriptions.edges"].apply(lambda y: None if (type(y) == list and len(y) == 0) else y)

    df = df.sort_index().reset_index(drop=True)
    df["subscription_count"] = df["subscription_count"].fillna(0)
    return df.rename(columns= {"subscriptions.edges": "app_subscriptions"})

def get_apps_with_no_subscription() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with no subscription

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """

    return get_apps(facet_filters={"subscriptions":{"keys":["__missing__"]}})

def get_apps_with_no_licence() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with no licence

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"licence":{"keys":["__missing__"]}})

def get_apps_with_no_subscription_and_licence() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with no subscription and no licence

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    apps_with_no_abo = get_apps_with_no_subscription()
    apps_with_no_licence = get_apps_with_no_licence()
    return apps_with_no_abo.merge(apps_with_no_licence)

def get_apps_lifecycles() -> pd.DataFrame:
    """Returns a Pandas DataFrame of the lifecycles of each applicattion

    Returns:
        pd.DataFrame:
        By default the DataFrame contains `[id, displayName, bankId, ApplicationLifecycle.asString,	ApplicationLifecycle.phase]` of an application
    """
    df = get_apps(on_app_nodes= [query_temp.apps_lifecycle_query])

    i = 0
    indices = df.index # indices of the df
    for relation in df["ApplicationLifecycle.phases"]:
        # check if there is a lifecyle
        if type(relation) is list and relation != []:
            lifecylces = []
            #print(relation)
            #print("len:", len(relation))
            for j in range(len(relation)):
                phase = relation[j]["phase"]
                phase_date = relation[j]["startDate"]
                #print(phase, phase_date)
                lifecylces.append([phase, phase_date])
            #print("lifecycles:", lifecylces)
            lifecylces_dict = _lifecycles_to_dict(lifecylces)
            df.at[indices[i], "ApplicationLifecycle.phases"] = lifecylces_dict # modify entry in column "subscriptions.edges" at the correct index. This is done because when the  
        i += 1
    df = df.drop(columns=["ApplicationLifecycle"])
    df = df.sort_index().reset_index(drop=True)

    return df

def get_apps_with_no_lifecycle() -> pd.DataFrame:
    """Gets all applications which don`t have a lifecycle at the moment, until a specific date, or within a specific time period

        Returns:
        -------
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    start_date = str(date.today())
    end_date = start_date
    print("Dates:", start_date, "-", end_date)

    return get_apps(facet_filters={"fact_sheet_type":{"keys":["Application"]}, "lifecycle":{"keys":["__missing__", "_noLifecycle_"], "date_range":[start_date, end_date]}})

def get_apps_by_lifecycle_type(lifecycle: list) -> pd.DataFrame:
    """Gets all applications by specifing one or multiple lifecycle types

        Parameters:
            lifecycle (list): lifecycle type of the application
            lifecycle types: `["__any__", "active", "endOfLife", "phaseIn", "phaseOut", "plan", "__missing__", "_noLifecycle_"]`

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]`
    """

    start_date = str(date.today())
    end_date = start_date
    print("Dates:", start_date, "-", end_date)

    return get_apps(facet_filters={"fact_sheet_type":{"keys":["Application"]}, "lifecycle":{"keys":lifecycle, "date_range":[start_date, end_date]}})

def get_apps_by_lifecycle_date(start_date: str=None, end_date: str=None) -> pd.DataFrame:
    """Gets all applications which don't have a lifecycle at the moment, until a specific date, or within a specific time period
        Parameters:
            start_date (str, optional): 
                Date format Year-Month-Day, e.g.: 2021-01-01

            end_date (str, optional):
                Date format Year-Month-Day, e.g.: 2022-02-02

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application (default = when no additional `on_app_nodes` or `on_node_nodes` are added)

        Notes
        -----
            Case 1: No `start_date` and `end_date` given --> `start_date`= today and `end_date`= `start_date`+ 3 years
             
            Case 2: No start_date given --> `start_date`= today
            
            Case 3: No `end_date` given --> `end_date`= `start_date`+ 3 years
            
            Case 4: If no start and end are given then by default:
            
                `start_date` = current date (today)
                
                `end_date` = start_date + 3 years
            
            Example: `start_date` = 2000-01-01  --> `end_date` = 2003-01-01
        
        Examples:
            Example 1: Without specifing `start_date` and `end_date`
            >>> get_apps_with_no_lifecycle()

            Example 2: Specifing `start_date`
            >>> get_apps_with_no_lifecycle(start_date= "2021-01-01")

            Example 3: specifing `end_date`
            >>> get_apps_with_no_lifecycle(end_date= "2024-01-01")

            Example 4: specifing `start_date` and `end_date`
            >>> get_apps_with_no_lifecycle(start_date= "2021-01-01", end_date= "2024-01-01")
    """

    if not start_date:
        start_date = str(date.today())
        print("No start_date given!")

    if not end_date:
        end_date = str(date(date.today().year+3, date.today().month, date.today().day))
        print("No end_date given!")

    if not (start_date and end_date):
        # date range between current date and 3 years in the future
        # e.g. start_date = 2000-01-01  --> end_date = 2003-01-01
        start_date = str(date.today())
        end_date = str(date(date.today().year+3, date.today().month, date.today().day))

    # start_date must be smaller than end_date
    date_format = "%Y-%m-%d"
    d1 = datetime.strptime(start_date, date_format)
    d2 = datetime.strptime(end_date, date_format)
    assert(d1 <= d2), "end_date cannot be bigger than start_date"

    print("Dates:", start_date, "-", end_date)

    return get_apps(facet_filters={"fact_sheet_type":{"keys":["Application"]}, "lifecycle":{"keys":["active", "endOfLife", "phaseIn", "phaseOut", "plan"], "date_range":[start_date, end_date]}})

def get_apps_by_lifecycle( lifecycle: list, start_date: str=None, end_date: str=None) -> pd.DataFrame:
    """Gets all applications by specifing one or multiple lifecycle types at the moment until a specific date, or within a specific time period
        Parameters:
            lifecycle (list): lifecycle type of the application
            lifecycle types: `["__any__", "active", "endOfLife", "phaseIn", "phaseOut", "plan", "__missing__", "_noLifecycle_"]`

            start_date (str, optional): 
                Date format Year-Month-Day, e.g.: 2021-01-01

            end_date (str, optional):
                Date format Year-Month-Day, e.g.: 2022-02-02

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application (default = when no additional `on_app_nodes` or `on_node_nodes` are added)

        Note:
        -----
            Date Cases:
            Case 1: No `start_date` and `end_date` given --> `start_date`= today and `end_date`= `start_date`+ 3 years
            
            Case 2: No start_date given --> `start_date`= today
            
            Case 3: No `end_date` given --> `end_date`= `start_date`+ 3 years
            
            Case 4: If no start and end are given then by default:
            
                `start_date` = current date (today)
                
                `end_date` = start_date + 3 years
                
            Example: `start_date` = 2000-01-01  --> `end_date` = 2003-01-01
        
        Examples:
            **Different Lifeycycle Type Cases**:

            Example 1: only one lifecycle type 
            >>> get_apps_with_no_lifecycle(lifecycle= ["active"])

            Example 2: multiple lifecycle types 
            >>> get_apps_with_no_lifecycle(lifecycle= ["active", "endOfLife", "phaseIn", "phaseOut", "plan"])

            **Different Date Cases**:

            Example 1: Active apps without specifing `start_date` and `end_date`
            >>> get_apps_with_no_lifecycle(lifecycle= ["active"])

            Example 2: Active and planned apps, and specifing `start_date`
            >>> get_apps_with_no_lifecycle(lifecycle= ["active", "plan"]) start_date= "2021-01-01")

            Example 3: Active and planned apps, and specifing `end_date`
            >>> get_apps_with_no_lifecycle(lifecycle= ["active", "plan"], end_date= "2024-01-01")

            Example 4: Active and planned apps, and specifing `start_date` and `end_date`
            >>> get_apps_with_no_lifecycle(lifecycle= ["active", "plan"], start_date= "2021-01-01", end_date= "2024-01-01")
    """

    if not start_date:
        start_date = str(date.today())
        print("No start_date given!")

    if not end_date:
        end_date = str(date(date.today().year+3, date.today().month, date.today().day))
        print("No end_date given!")

    if not (start_date and end_date):
        # date range between current date and 3 years in the future
        # e.g. start_date = 2000-01-01  --> end_date = 2003-01-01
        start_date = str(date.today())
        end_date = str(date(date.today().year+3, date.today().month, date.today().day))

    # start_date must be smaller than end_date
    date_format = "%Y-%m-%d"
    d1 = datetime.strptime(start_date, date_format)
    d2 = datetime.strptime(end_date, date_format)
    assert(d1 <= d2), "end_date cannot be bigger than start_date"

    print("Dates:", start_date, "-", end_date)

    return get_apps(facet_filters={"fact_sheet_type":{"keys":["Application"]}, "lifecycle":{"keys":lifecycle, "date_range":[start_date, end_date]}})

def get_apps_with_rejected_quality_seal_status() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with status (broken quality seal = "rejected")
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"keys":["REJECTED"]}}, on_app_nodes=["qualitySeal", "lxState"]).dropna(how= "all")

def get_apps_with_broken_quality_seal() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with a broken quality seal
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_app_nodes=["qualitySeal", "lxState"]).dropna(how= "all")

def _quality_seal_broken_by_PI(logEvent:dict) -> bool:
    """Checks wether the quality seal of an app was broken by the Python Interaction (= the script setting the bankId of Applications) or not
    
        Parameters:
            logEvent (dict): 
                LogEvents of the application
                    
        Returns:
            bool:
    """
    entry = application_logEvents_to_df(logEvent)
    broken_qual_seal_df = entry.loc[entry["newValue"] =="BROKEN"]
    broken_by_python_interaction = broken_qual_seal_df.loc[broken_qual_seal_df["user_name"] == "Python Interaction"]
    if broken_by_python_interaction.size > 0:
        # check if "Python Interaction" was the cause of the last quality seal breakage
        broken_qual_seal_df = broken_qual_seal_df.reset_index() # reset index so that the most recent event is at index 0
        if broken_qual_seal_df.at[0 , "user_name"] == "Python Interaction":
            return True 
    else: 
        return False

def get_apps_quality_seal_broken_by_python_interaction() -> pd.DataFrame:
    """Retruns a DataFrame of all application by which the quality seal was broken by the Python Interaction (= the script setting the bankId of Applications)

        Returns:
        -------
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
        
        Note:
        ------- 
            The function takes about 1-3 minutes to collect and process the data
    """
    
    df = get_apps_with_broken_quality_seal()

    # insert new columns into the  DataFrame 
    df.insert(2, "broken_by_PI", None, True)
    ids = [id for id in df["id"]]
    df.set_index("id", inplace= True)
    
    for id in ids:
        app_log_events = query_app_allLogEvents_by_id(id)
        # add logEvents of each app to the DataFrame (if needed)
        # df.loc[id, "logEvents"] = str(app_log_events)
        if _quality_seal_broken_by_PI(logEvent=app_log_events):
            df.loc[id, "broken_by_PI"] = True

    # df will have only rows with "broken_by_PI" == True 
    df = df[df["broken_by_PI"] == True]
    df = df.reset_index()
    return df

def _quality_seal_broken_by_user_name(logEvent:dict, user_name: str) -> bool:
    """Helper method which checks if the quality seal of an app was broken by a specific user or not

        Parameters:
            logEvent (dict): 
                LogEvents of the application
            
            user_name (str):
                name of the user as specified in LeanIX

        Returns:
            bool:
    """

    entry = application_logEvents_to_df(logEvent)
    broken_qual_seal_df = entry.loc[entry["newValue"] =="BROKEN"]
    broken_by_user = broken_qual_seal_df.loc[broken_qual_seal_df["user_name"] == user_name]
    return True if broken_by_user.size > 0 else False

def get_apps_quality_seal_broken_by_user_name(user_name: str) -> pd.DataFrame:
    """Retruns a DataFrame of all application by which quality seal was broken by a specific user

        Parameters:
            user_name (str):
                name of the user as specified in LeanIX
        
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, user_name, bankId, displayName]` of an application

        Note:
        -----
            The function might take about 1-2 minutes to collect and process the data, because it checkes each logEvent of each application
        """
    
    df = get_apps()

    # insert new columns into the dataframe
    df.insert(2, f"broken_by_{user_name}", None, True)
    ids = [id for id in df["id"]]
    df.set_index("id", inplace=True)
    
    for id in ids:
        app_log_events = query_app_allLogEvents_by_id(id)
        # add logEvents of each app to the dataframe (if needed)
        # df.loc[id, "logEvents"] = str(app_log_events)
        if _quality_seal_broken_by_user_name(logEvent=app_log_events, user_name= user_name):
            df.loc[id, f"broken_by_{user_name}"] = True

    # df will have only rows with "broken_by_{user_name}" == True 
    df = df[df[f"broken_by_{user_name}"] == True]
    return df

def _quality_seal_broken_at_date(logEvent:dict, date: str) -> bool:
    """Helper method which checks if the quality seal of an app was broken at a specific date
    
        Parameters:
                logEvent (dict): 
                    LogEvents of the application

                date (str):
                    Date for which the quality seal should be checked
                    Format: year-month-day e.g., "2021-01-01"
                        
        Returns:
            bool:
    """

    entry = application_logEvents_to_df(logEvent)
    broken_qual_seal_df = entry.loc[entry["newValue"] =="BROKEN"]
    # enries that start with the desired date of the form "yera-month-day" in the date format "year-month-day-hour-..." e.g. "2024-12-05T16:11:47.458471949Z"
    broken_at_date = broken_qual_seal_df.loc[broken_qual_seal_df["createdAt"].str.startswith(date)]
    return True if broken_at_date.size > 0 else False

def get_apps_quality_seal_broken_at_date(date: str) -> pd.DataFrame:
    """Retruns a DataFrame of the applications by which quality seal was broken at a specific date (Format: year-month-day, e.g. 2024-12-05)

        Parameters:
            date (str):
                Date for which the quality seal should be checked
                Format: year-month-day e.g., "2024-12-05"
        
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, date, bankId, displayName]` of an application

        Note:
        -----
            The function might take about 1-2 minutes to collect and process the data, because it checkes each logEvent of each application
    """
    df = get_apps()

    ids = [id for id in df["id"]]
    df.set_index("id", inplace=True)
    
    for id in ids:
        app_log_events = query_app_allLogEvents_by_id(id)
        # add logEvents of each app to the dataframe (if needed)
        # df.loc[id, "logEvents"] = str(app_log_events)
        if _quality_seal_broken_at_date(logEvent=app_log_events, date= date):
            df.loc[id, f"broken_by_{date}"] = True

    # df will have only rows with "broken_by_{date}" == True 
    df = df[df[f"broken_by_{date}"] == True]
    return df

##### dsg (Datenschutz)
def get_apps_dsg_fields() -> pd.DataFrame:
    app_nodes = ["datamaster", "completeClientDatabase", "massDataQueries", "deletionProcess", "holdOffTime", "backup", "personDataProtectionAgreements", "dsg_comment"]
    df =  get_apps(on_app_nodes= app_nodes).fillna(value= np.nan).replace("", np.nan)
    
    # reporting_tag is also an dsg_field but has to be aquired seperately
    apps_reporting_tag_df = get_apps_reporting_tag()
    apps_reporting_tag_df.reset_index(drop= True, inplace= True)
    df = pd.merge(df, apps_reporting_tag_df[["id", "reporting_tag"]], on="id")
    
    return df

def check_apps_dsg_field_correctness():
    """Check the correctness/validity of relevent dsg-fields (Datenschutzfelder)

        checks (in German): 
            - alle Datenschutzfelder sind leer:
            Das ist nicht erwünscht, denn mindestens das Feld "Speicherung DSG relevante Daten" muss ausgefüllt sein. Nämlich "Speicherung DSG relevante Daten" = "False
            - "Speicherung DSG relevante Daten" = "True" aber die andere Felder sind leer (nicht ausgefüllt)
            - "Speicherung DSG relevante Daten" = "False" aber die andere Felder sind angegeben (ausgefüllt)
            - "Speicherung DSG relevante Daten" = "False" aber "Kundendatenumfang" = "ja"

        Returns:
            pd.DataFrame:
            By default the DataFrame contains: 
                `[id, displayName, bankId, Speicherung DSG relevante Daten (DSG), 
                alle Datenschutzfelder leer	DSG=True, andere Felder leer, DSG=False, 
                andree Felder angegeben, DSG=False, Kundendatenumfang=Ja]` 
                of an application (default = when no additional `on_app_nodes` or `on_node_nodes` are added)
    """

    df = get_apps_dsg_fields()
    # create new df
    compare_df = df[["id", "displayName","bankId", "datamaster"]].copy()
    compare_df = compare_df.rename(columns={"datamaster": "Speicherung DSG relevante Daten (DSG)"})
    compare_df[["alle Datenschutzfelder leer", "DSG=True, andere Felder leer", "DSG=False, andree Felder angegeben", "DSG=False, Kundendatenumfang=Ja"]]= False
    compare_df.set_index("id", inplace=True)

    # alle Datenschutzfelder sind leer
    # Das ist nicht erwünscht, denn mindestens das Feld "Speicherung DSG relevante Daten" muss ausgefüllt sein 
    # nähmlich "Speicherung DSG relevante Daten" = "False
    cols = df.columns.difference(["id", "bankId", "displayName"])
    mask = df[cols].isna().all(axis=1)
    mask_df = df[mask]
    compare_df = _check_condition(compare_df, mask_df, "alle Datenschutzfelder leer")

    # "Speicherung DSG relevante Daten" = "True" aber die andere Felder sind leer (nicht ausgefüllt)
    condition_a = (df["datamaster"] == "True")
    cols = df.columns.difference(["id", "bankId", "displayName", "datamaster"])
    mask = df[cols].isna().all(axis=1)
    mask_df = df[condition_a & mask]
    compare_df = _check_condition(compare_df, mask_df, "DSG=True, andere Felder leer")

    # "Speicherung DSG relevante Daten" = "False" aber die andere Felder sind angegeben (ausgefüllt)
    condition_a = (df["datamaster"] == "False")
    cols = df.columns.difference(["id", "bankId", "displayName", "datamaster"])
    mask = df[cols].notna().any(axis=1)
    mask_df = df[condition_a & mask]
    compare_df = _check_condition(compare_df, mask_df, "DSG=False, andree Felder angegeben")


    # "Speicherung DSG relevante Daten" = "False" aber "Kundendatenumfang" = "ja"
    mask_df = df[(df["datamaster"] == "False") & (df["completeClientDatabase"] == "yes")]
    compare_df = _check_condition(compare_df, mask_df, "DSG=False, Kundendatenumfang=Ja")

    return compare_df

def get_apps_dsg_field_datamaster_status() -> pd.DataFrame:
    app_nodes = ["datamaster"]
    return get_apps(on_app_nodes= app_nodes).fillna(value= np.nan).replace("", np.nan)

def get_apps_with_missing_dsg() -> pd.DataFrame:
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}, "dsg_datamaster":{"keys":["__missing__"]}})

def get_apps_no_dsg_but_client_database() -> pd.DataFrame:
    """"Speicherung DSG relevante Daten", "False" in Kombination mit Datenfeld "Kundendatenumfang" mit 'yes'"""
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}, "dsg_datamaster":{"keys":["False"]}, "client_database": {"keys": ["yes"]}})
    
def get_apps_no_dsg_but_data_required() -> pd.DataFrame:
    """"Speicherung DSG relevante Daten" = "False" aber die andere Felder sind angegeben (ausgefüllt)"""
    return get_apps(facet_filters={
        "fact_sheet_type": {"keys":["Application"]}, 
        "dsg_datamaster":{"keys":["False", "__missing__"]}, 
        "client_database": {"keys": ["yes"]},
        "mass_data" : {"keys": ["yes", "export"]},
        "person_data_protection" : {"keys": ["inPlace", "notInPlace", "onParent"]},
        })

def get_apps_dsg_but_no_data_required() -> pd.DataFrame:
    """"Speicherung DSG relevante Daten" = "True" aber die andere Felder sind leer (nicht ausgefüllt)"""
    return get_apps(facet_filters={
        "fact_sheet_type": {"keys":["Application"]}, 
        "dsg_datamaster":{"keys":["True"]}, 
        "client_database": {"keys": ["__missing__"]},
        "mass_data" : {"keys": ["__missing__"]},
        "person_data_protection" : {"keys": ["__missing__"]},
        "data_deletion_process": {"keys": ["__missing__"]},
        "data_holdOffTime" : {"keys": ["__missing__"]}
        })

def get_apps_reporting_tag() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications reporting tag
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, tags, reporting_tag]` of an application
    """
    # reporting_tag can have four different values: ["__missing__", "layer 1". "layer 2", "layer 3"]
    reporting_tag_layers = [
        "__missing__",
        "4dc4be27-47cb-4052-9134-aad672504381", # layer 1
        "658c6a8d-1353-4e28-83f1-872d2e772cb9", # layer 2
        "95642a8c-f2d5-43f5-884f-165b128bce1e", # layer 3
        ]
    tagGroup = query_temp.app_tag_group_query
    df =  get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"reporting_tag":{"keys":reporting_tag_layers}}, on_app_nodes= [tagGroup])
    df["reporting_tag"] = None # add new column
    
    df.set_index(df["id"], inplace= True)

    for entry in df.index:
        # when an applicaiton has multiple
        for i in range(len(df.at[entry,"tags"])):
            if str(df.at[entry,"tags"]).count("Layer") >= 1:
                if str(df.at[entry,"tags"][i]).__contains__("Layer"):
                    s = str(df.at[entry, "tags"][i]).replace("\'", "\"")
                    #print(s)
                    #print(df.at[entry, "tags"][i]["name"])
                    df.at[entry, "reporting_tag"] = df.at[entry, "tags"][i]["name"]
            else: # __missing__ reporting tag
                df.at[entry, "reporting_tag"] = None

    return df
    
def get_apps_with_missing_reporting_tag() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with no/missing reporting tag
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"reporting_tag":{"keys":["__missing__"]}})

def get_apps_business_criticality() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with missing businessCriticality
        businessCriticality can have five different keys: ["__missing__", "administrativeService", "businessCritical", "businessOperational", "missionCritical"]

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, businessCriticality]` of an application
    """
    _keys = ["__missing__", "administrativeService", "businessCritical", "businessOperational", "missionCritical"]
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"business_criticality":{"keys":_keys}}, on_app_nodes= ["businessCriticality"])

def get_apps_with_missing_business_criticality() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with missing businessCriticality
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"business_criticality":{"keys":["__missing__"]}})

def get_apps_functional_suitability() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications and their functionalSuitability (Fachliche Eignung)
        functional_suitability can have five different keys: ["__missing__", "appropriate", "insufficient", "perfect", "unreasonable"]
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    _keys = ["__missing__", "appropriate", "insufficient", "perfect", "unreasonable"]
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"functional_suitability":{"keys":_keys}}, on_app_nodes=["functionalSuitability"])

def get_apps_with_missing_functional_suitability() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all applications with missing functionalSuitability (Fachliche Eignung)
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of an application
    """
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]},"functional_suitability":{"keys":["__missing__"]}})

def get_apps_tag_groups():
    tagGroup = query_temp.app_tag_group_query
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}}, on_app_nodes= [tagGroup])

##### dsg (Datenschutz)

####################################### Application

####################################### User Group

def get_user_groups(facet_filters: FilterTemplate=None, on_user_group_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all user groups on LeanIX in form of a Pandas DataFrame
   
        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_user_group_nodes (list, optional):
                Additional on_user_group_nodes (properties of a user group) to be added to the query, e.g., `id`, `displyName`, `type`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, level]` of a user group (default = when no additional `on_user_group_nodes` or `on_node_nodes` are added)

        Examples:
            These examples get all user groups with a broken quality seal in addition to other properties like: `type`, `createdAt`, `status`, ...
            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": "UserGroup"}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> user_group_nodes = ["type", "qualitySeal"]
                >>> node_nodes = ["createdAt", "status"]
                >>> get_user_groups(facet_filters= filters, on_user_group_nodes= user_group_nodes, on_node_nodes= node_nodes)
                    
            Example 2: Specifing attributes when calling the function
                >>> get_user_groups(facet_filters= {"fact_sheet_type": "UserGroup"}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_user_group_nodes= ["type", "qualitySeal"], on_node_nodes= ["createdAt", "status"])
    
            -> The DataFrame will have columns: 
            `[id, displayName, level, relToParent.edges, qualitySeal, createdAt, status]`
    """

    # if no facet_filters are given, a default filter is applied
    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["UserGroup"]}}

    return user_group_factSheets_to_df(query_user_groups(facet_filters, on_user_group_nodes, on_node_nodes))

def user_group_factSheets_to_df(allFactSheets : dict) -> pd.DataFrame:
    """Creates a Pandas DataFrame out of the Fact Sheet attributes

        Parameters:
            allFactSheets (dict):
                The Fact Sheets attributes

        Returns:
            df (pd.DataFrame):

        Examples:
            Example:
                >>> user_group_factSheets_to_df(query_user_group(facet_filters, on_user_group_nodes, on_node_nodes))
            
            Example response: 
                >>> `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-XXXX-XXXX-be59-XXXXXXX", 
                "displayName": "XXXXXXX", 
                "type": "UserGroup", 
                "level": "2", }}`, 
                ...

            -> The DataFrame will have columns: `[id, displayName, type, level]`
    """
    
    # get all nodes of the Fact Sheet
    user_group_nodes = allFactSheets["data"]["allFactSheets"]["edges"]
    df = json_normalize(user_group_nodes)

    # clean df column names by removing the prefix "node." from the name of the columns, e.g. node.displyName --to--> displayName
    df.columns = [col_name.removeprefix("node.") for col_name in df]

    return df

def get_user_groups_by_hierarchy_level(level: str, relation_to_parent: bool= False, parent_leanix_id: str= "") -> pd.DataFrame:
    """Get all user groups by specifing the hierarchy level"""
    assert str(level) in user_group_hierarchy_levels, "The given UserGroup hierarchy level is invalid!"

    _keys = []
    if relation_to_parent: 
        _keys = [parent_leanix_id]

    return get_user_groups(facet_filters={"fact_sheet_type": {"keys":["UserGroup"]},
                                   "facet_key":{"facet_key": "hierarchyLevel", "keys":[str(level)]}, 
                                   "relation_to_parent": {"keys": _keys}}, 
                                   on_node_nodes=["id", "displayName", "level"]).filter(items=["displayName", "id", "level"]) #filter df to only have columns: ["displayName", "id", "level"]

def get_user_groups_with_parentX(parent_leanix_id: str, level: str = "") -> pd.DataFrame:
    """Get all user groups that a given parent has by specifing the parent_leanix_id"""
    _keys = [parent_leanix_id]
    filters = {"fact_sheet_type": {"keys":["UserGroup"]}, "relation_to_parent": {"keys": _keys}}

    # if a level is given, check if the level is valid and apply the hierarchyLevel facet_filter
    if level != "":
        assert str(level) in user_group_hierarchy_levels, "The given UserGroup hierarchy level is invalid!"
        filters.update({"facet_key":{"facet_key": "hierarchyLevel", "keys":[str(level)]}})
        
    return get_user_groups(facet_filters= filters).filter(items=["displayName", "id", "level"]) #filter df to only have columns: ["displayName", "id", "level"]
                                  
######################################## User Group

######################################## Provider

def get_providers(facet_filters: FilterTemplate=None, on_provider_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all providers on LeanIX in form of a Pandas DataFrame
   
        Parameters:
        -------
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_provider_nodes (list, optional):
                Additional on_provider_nodes (properties of a provider) to be added to the query, e.g., `id`, `displyName`, `type`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
        -------
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, level]` of a provider (default = when no additional `on_provider_nodes` or `on_node_nodes` are added)

        Examples:
        -------
            These examples get all providers with a broken quality seal in addition to other properties like: `type`, `createdAt`, `status`, ...
            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": "Provider"}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> provider_nodes = ["type", "qualitySeal"]
                >>> node_nodes = ["createdAT", "status"]
                >>> get_providers(facet_filters= filters, on_provider_nodes= provider_nodes, on_node_nodes= node_nodes)
                    
            Example 2: Specifing attributes when calling the function
                >>> get_providers(facet_filters= {"fact_sheet_type": "Provider"}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_provider_nodes= ["type", "qualitySeal"], on_node_nodes= ["createdAt", "status"])
    
            -> The DataFrame will have columns: 
            `[id, displayName, level, status]`
    """

    if not facet_filters:
        facet_filters= {"fact_sheet_type": {"keys":["Provider"]}}

    return provider_factSheets_to_df(query_providers(facet_filters, on_provider_nodes, on_node_nodes))

# Convert all factSheets of all apps to df enteries with [app_id, displayName]
def provider_factSheets_to_df(allFactSheets : dict) -> pd.DataFrame:
    """Creates a Pandas DataFrame out of the Fact Sheet attributes

        Parameters:
            allFactSheets (dict):
                The Fact Sheets attributes

        Returns:
            df (pd.DataFrame):

        Examples:
            Example:
                >>> provider_factSheets_to_df(query_provider(facet_filters, on_provider_nodes, on_node_nodes))
            
            Example response: 
                >>> `"data": {"allFactSheets": {"edges": [{"node": 
                {"id": "XXXXXXX-66e3-4572-be59-XXXXXXX", 
                "displayName": "XXXXXXX",
                "level": "2", }}`, 
                ...

            -> The DataFrame will have columns: `[id, displayName, level]`
    """
    
    # get all nodes of the Fact Sheet
    provider_nodes = allFactSheets["data"]["allFactSheets"]["edges"]
    df = json_normalize(provider_nodes)

    # clean df column names by removing the prefix "node." from the name of the columns, e.g. node.displyName --to--> displayName
    df.columns = [col_name.removeprefix("node.") for col_name in df]

    return df

def get_provider_by_hierarchy_level(level: str, relation_to_parent: bool= False, parent_leanix_id: str= "") -> pd.DataFrame:

    assert str(level) in provider_hierarchy_levels, "The given Provider hierarchy level is invalid!"

    _keys = []
    if relation_to_parent: 
        _keys = [parent_leanix_id]

    return get_providers(facet_filters={"fact_sheet_type": {"keys":["Provider"]},
                                   "facet_key":{"facet_key": "hierarchyLevel", "keys":[str(level)]}, 
                                   "relation_to_parent": {"keys": _keys}}, 
                                   on_node_nodes=["id", "displayName", "level"]).filter(items=["displayName", "id", "level"]) #filter df to only have columns: ["displayName", "id", "level"]

def get_providers_with_parentX(parent_leanix_id: str, level: str = "") -> pd.DataFrame:

    _keys = [parent_leanix_id]
    filters = {"fact_sheet_type": {"keys":["Provider"]}, "relation_to_parent": {"keys": _keys}}

    # if a level is given, check if the level is valid and apply the hierarchyLevel facet_filter
    if level != "":
        assert str(level) in provider_hierarchy_levels, "The given Provider hierarchy level is invalid!"
        filters.update({"facet_key":{"facet_key": "hierarchyLevel", "keys":[str(level)]}})
        
    return get_providers(facet_filters= filters)

######################################## Provider

####################################### Interface

def get_interfaces(facet_filters: FilterTemplate=None, on_interface_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all interfaces on LeanIX in form of a Pandas DataFrame
   
        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_interface_nodes (list, optional):
                Additional on_interface_nodes (properties of an interface) to be added to the query, e.g. `displyName`, `description`, `type`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName]` of an interface (default = when no additional `on_interface_nodes` or `on_node_nodes` are added)

        Examples:
            These examples query all interfaces `id, displayName` in addition to other properties like: `qualiySeal`, `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["Interface"]}}
                >>> interface_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["level", "status"]
                >>> get_interfaces(facet_filters= filters, on_interface_nodes= interface_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
                >>> get_interfaces(facet_filters= {"fact_sheet_type": {"keys":["Interface"]}}, on_interface_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])

            -> The DataFrame will have columns: 
            `[id, displayName, type, description, qualitySeal, status, level]`
    """

    if not facet_filters:
        facet_filters = {"fact_sheet_type": {"keys":["Interface"]}}

    return factSheets_to_df(query_interfaces(facet_filters, on_interface_nodes, on_node_nodes))

def get_all_interfaces_logEvents(facet_filters: FilterTemplate=None) -> pd.DataFrame:
    """Gets all Log Events of Interfaces on LeanIX with help of a GraphQL query stored in `.txt` file
        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
        Returns:
            interfaces (pd.DataFrame):
                By default the DataFrame contains `id, displayName`, `logEvents` of an interface (default = when no additional `on_interface_nodes` or `on_node_nodes` are added)
        
        Note:
        -----
        The function might take about 1-2 minutes to collect and process the data, because it checkes each logEvent of each application
        
        Examples:
            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["Interface"]}}
                >>> get_all_interfaces_logEvents(facet_filters= filters)
                
            Example 2: Specifing attributes when calling the function
                >>> get_all_interfaces_logEvents(facet_filters= {"fact_sheet_type": {"keys":["Interface"]}})

            -> The DataFrame will have columns: 
            `[id, displayName, logEvents]`
    """
    
    # if no facet_filters are given, a default filter is applied
    if not facet_filters:
        facet_filters = {"fact_sheet_type": {"keys":["Interface"]}}

    interfaces = get_interfaces()
    ids = interfaces["id"]

    interfaces.set_index("id", inplace=True)

    # add a new column in df for the logEvents
    interfaces["logEvents"] = None

    for id in ids:
        log_event = query_interface_allLogEvents_by_id(id)
        interfaces.at[id, "logEvents"] = log_event
        
    return interfaces

def interface_logEvents_to_df(logEvents : dict):
    """Convert all LogEvents of all apps to Pandas DataFrame enteries"""
    if len(logEvents) == 0:
        assert "Provided logEvents dict is empty"
    nodes = logEvents["data"]["allLogEvents"]["edges"]
    df = json_normalize(nodes)
    #df.info()
    # remove the node from the name of the columns, e.g. node.displyName --to--> displayName
    df.columns = [col_name.removeprefix("node.") for col_name in df]
    #df = df.filter(["id", "path", "newValue", "user.displayName"])
    #df.columns = ["event_id", "path", "newValue", "user_name"]
    return df

def get_interface_with_no_provider() -> pd.DataFrame:
    return get_interfaces(facet_filters={"fact_sheet_type": {"keys":["Interface"]},"relation_interface_to_provider_application":{"keys":["__missing__"]}})

def get_interface_with_no_consumer() -> pd.DataFrame:
    return get_interfaces(facet_filters={"fact_sheet_type": {"keys":["Interface"]},"relation_interface_to_consumer_application":{"keys":["__missing__"]}})

def get_interface_logEvents_by_id(id:str):
    """Gets all Log Events of a specific Interfaces on LeanIX using the Interface LeanIX_ID

            Parameters:
                id (str): 
                    ID of factSheet, i.e. ID of interface
                
            Returns:
                interface_log_events_df (pd.DataFrame):
                    By default the DataFrame contains `id, displayName`, `logEvents` of an interface 

            Note:
            ------
            The function might take about 1-2 minutes to collect and process the data, because it checkes each logEvent of each application
            
            Examples:
                >>> get_interface_logEvents_by_id(id= "XXXXXXX-74e3-4952-be59-XXXXXXX")

                -> The DataFrame will have columns: 
                `[id, displayName, logEvents]`
    """

    query = post_query(query_interface_allLogEvents_by_id(id))
    interface_log_events_df = interface_logEvents_to_df(query)
    return interface_log_events_df

####################################### Interface

####################################### Activity

def get_activities(facet_filters: FilterTemplate=None, on_activity_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all Activities on LeanIX in form of a Pandas DataFrame

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_activity_nodes (list, optional):
                Additional on_activity_nodes (properties of an activity) to be added to the query, e.g. `displyName`, `description`, `type`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName]` of an activity (default = when no additional `on_activity_nodes` or `on_node_nodes` are added)

        Examples:
            These examples get all activities `id, displayName` in addition to other properties like: `qualiySeal`, `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["Activity"]}}
                >>> activity_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["level", "status"]
                >>> get_activities(facet_filters= filters, on_activity_nodes= activity_nodes, on_node_nodes= node_nodes)

                
            Example 2: Specifing attributes when calling the function
                >>> get_activities(facet_filters= {"fact_sheet_type": {"keys":["Activity"]}}, on_activity_nodes= ["description", "qualitySeal"], on_node_nodes= ["level", "status"])

            -> The DataFrame will have columns: 
            `[id, displayName, description, qualitySeal, level, status]`
    """

    # Applying .dropna(how="all") to df to filter to get remove all rows/entries with only NaN-values
    # this is useful in case the function get_ITComponents is called without arguments
    return factSheets_to_df(query_activities(facet_filters, on_activity_nodes, on_node_nodes)).dropna(how= "all")

def get_activity_completion() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all activities and their completion in percent

        Returns:
        -------
            pd.DataFrame: `[id, displayName, completion.percentage]`
    """

    return get_activities(facet_filters={"fact_sheet_type": {"keys":["Activity"]}}, on_activity_nodes=["completion {percentage}"]).sort_values(by= "completion.percentage", axis=0)

def get_activities_with_approved_quality_seal_without_admin_permission() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all activities with an incorrectly approved quality seal (meaning, the quality seal was approved when the activity was registered in LeanIX without an adminstrator permission/control)
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName]` of an application
    """

    activites = get_activities(facet_filters={"fact_sheet_type": {"keys":["Activity"]}, "quality_seal": {"keys":["APPROVED"]}}, on_activity_nodes=["lxState", "completion {percentage}"]).sort_values(by= "completion.percentage", axis=0).dropna()
    incomplete_activites = activites[activites["completion.percentage"] < 100]
    
    return incomplete_activites

####################################### Activity

####################################### Business Capability

def get_business_capabilities(facet_filters: FilterTemplate=None, on_business_capability_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all Process on LeanIX in form of a Pandas DataFrame

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_business_capability_nodes (list, optional):
                Additional on_business_capability_nodes (properties of a business capability) to be added to the query, e.g. `displyName`, `description`, `bankId`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]` of a business capability (default = when no additional `on_business_capability_nodes` or `on_node_nodes` are added)

        Examples:
            These examples get all business_capability with a broken quality seal in addition to other properties like: `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["BusinessCapability"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> business_capability_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["status", "level"]
                >>> get_business_capabilities(facet_filters= filters, on_business_capability_nodes= business_capability_nodes, on_node_nodes= node_nodes)

                    
            Example 2: Specifing attributes when calling the function
                >>> get_business_capabilities(facet_filters= {"fact_sheet_type": {"keys":["BusinessCapability"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_business_capability_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])
        
                -> The DataFrame will have columns: 
                `[id, displayName, bankId, description, qualitySeal, status, level]`
    """

    # Applying .dropna(how="all") to df to filter to get remove all rows/entries with only NaN-values
    # this is useful in case the function get_ITComponents is called without arguments
    return factSheets_to_df(query_business_capabilities(facet_filters, on_business_capability_nodes, on_node_nodes)).dropna(how= "all")

def get_business_capabilities_bankId() -> str:
    """Query bankId of all Process registered in LeanIX
    
            Returns:
            -------
                pd.DataFrame:
                DataFrame containing bankId of each business capability registered in LeanIX
                By default the DataFrame contains `[id, displayName, bankId]` of a business capability 

            Examples:
            -------
                >>> get_business_capabilities_bankId(id= "XXXXXXX-74e3-4952-be59-XXXXXXX")
                >>>         id	                           displayName	                bankId
                >>> XXXXXXX-74e3-XXXX-XXXX-XXXXXXX	    XXXXXXXXXXX / XXXXX /...	      BCXXXX
    """

    graphql_query = query_temp.all_bankID_business_capability_query

    return factSheets_to_df(post_query(graphql_query))

####################################### Business Capability

####################################### IT Component

def ITComponents_overview_values(sort_values_by_col: str="displayName") -> pd.DataFrame:
    """Returns an Overview (Pflichtfelder) of all IT-Components on LeanIX in form of a Pandas DataFrame

        Parameters:
                sort_values_by_col (str, optional): 
                    Sorts the rows of the DataFrame in by the this column.

                    Example: sort_values_by_col: str="completion.percentage"

        Returns:
            pd.DataFrame:
            By default the DataFrame contains: 
                `[id, displayName, completion.percentage, description, qualitySeal, lxState, category, softwareDistribution, status, 	
                ITComponent_applications, ITComponent_subscriptions, relITComponentToProvider.edges,
                relITComponentToInterface.edges, ITComponentLifecycle.asString, ITComponentLifecycle.phases, Cardinality ITComponent : apps]`
            of an ITComponent (default = when no additional `on_ITComponent_nodes` or `on_node_nodes` are added)
    """
    df = _get_ITComponents_info()
    df = _ITComponents_lifecycle(df)
    ITComponent_providers_df = get_ITComponents_providers()
    df = df.merge(ITComponent_providers_df, left_on= ["ITComponent_id", "displayName"], right_on=["id", "displayName"]).reset_index(drop= True)
    ITComponent_interfaces_df = get_IT_components_interfaces()
    df = df.merge(ITComponent_interfaces_df, left_on= ["ITComponent_id", "displayName"], right_on=["id", "displayName"]).reset_index(drop= True)
    df = df.drop(columns=["id_x", "id_y"])
    df = _extract_applications(df, factSheet_type= "ITComponent")
    df = _extract_subscriptions(df).rename(columns= {"subscriptions.edges": "ITComponent_subscription", 
                                                     "relITComponentToProvider.edges": "ITComponent_providers", 
                                                     "relITComponentToInterface.edges": "ITComponent_Interfaces",
                                                     "relITComponentToApplication.edges": "ITComponent_application"})

    return df.sort_values(by= sort_values_by_col, axis= 0).reset_index(drop= True)

def get_ITComponents(facet_filters: FilterTemplate=None, on_ITComponent_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all IT-Components on LeanIX in form of a Pandas DataFrame

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_ITComponent_nodes (list, optional):
                Additional on_ITComponent_nodes (properties of a IT component) to be added to the query, e.g. `displyName`, `description`, `bankId`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName]` of a IT component (default = when no additional `on_ITComponent_nodes` or `on_node_nodes` are added)

        Examples:
            These examples get all IT-Components with a broken quality seal in addition to other properties like: `description`, `level`, ...

            Example 1: Generically define attributes in advance
                >>> filters = {"fact_sheet_type": {"keys":["BusinessCapability"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
                >>> ITComponent_nodes = ["description", "qualitySeal"]
                >>> node_nodes = ["status", "level"]
                >>> get_ITComponents(facet_filters= filters, on_ITComponent_nodes= ITComponent_nodes, on_node_nodes= node_nodes)

                    
            Example 2: Specifing attributes when calling the function
                >>> get_ITComponents(facet_filters= {"fact_sheet_type": {"keys":["BusinessCapability"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_ITComponent_nodes= ["description", "qualitySeal"], on_node_nodes= ["status", "level"])
        
                -> The DataFrame will have columns: 
                `[id, displayName, description, qualitySeal, status, level]`
    """

    return factSheets_to_df(query_ITComponents(facet_filters, on_ITComponent_nodes, on_node_nodes)).dropna(how= "all")

def get_ITComponents_applications() -> pd.DataFrame:
    """Returns a Pandas DataFrame of the applications of each IT-Component

        Returns:
        -------
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, relITComponentToApplication.edges]` of an application
    """

    # on_ITComponent_node
    rel_ITComponent_to_app_query = query_temp.rel_ITComponent_to_app_query
    
    df = get_ITComponents(facet_filters={"fact_sheet_type": {"keys":["ITComponent"]}}, on_ITComponent_nodes=[rel_ITComponent_to_app_query])

    i = 0
    for rel in df["relITComponentToApplication.edges"]:
        if rel != []:
            print(rel)
            apps = []
            #print("len:", len(rel))
            for j in range(len(rel)):
                app_id = rel[j]["node"]["factSheet"]["id"]
                apps.append(str(app_id))
            print("apps:", apps)
            df.at[i, "relITComponentToApplication.edges"] = apps
        i += 1

    return df

def get_ITComponents_with_no_applications() -> pd.DataFrame:
    """Returns a Pandas DataFrame of all IT-Components with no Applications

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName]` of an application
    """

    return get_ITComponents(facet_filters={"fact_sheet_type": {"keys":["ITComponent"]},"relation_ITComponent_to_application":{"keys":["__missing__", "_noLifecycle_"]}}).filter(["id", "displayName"])

def get_ITComponents_lifecycles() -> pd.DataFrame:
    """Returns a Pandas DataFrame of the lifecycles of each IT-Component
  
    Returns:
        pd.DataFrame:
        By default the DataFrame contains `[id, displayName, ITComponentLifecycle.asString,	ITComponentLifecycle.phase]` of an ITComponent
    """
    # IT Components lifecycles
    df = _get_ITComponents_info()

    i = 0
    indices = df.index # indices of the df
    for relation in df["ITComponentLifecycle.phases"]:
        # check if there is a lifecyle
        if type(relation) is list and relation != []:
            lifecylces = []
            #print(relation)
            #print("len:", len(relation))
            for j in range(len(relation)):
                phase = relation[j]["phase"]
                phase_date = relation[j]["startDate"]
                #print(phase, phase_date)
                lifecylces.append([phase, phase_date])
            #print("lifecycles:", lifecylces)
            df.at[indices[i], "ITComponentLifecycle.phases"] = lifecylces # modify entry in column "subscriptions.edges" at the correct index. This is done because when the  
        i += 1

    df = df.sort_index()
    df = df.filter(items=["id", "displayName", "ITComponentLifecycle.asString", "ITComponentLifecycle.phases"])
    df = df.sort_values(by=["displayName"])
    return df

def get_ITComponents_by_lifecycle_type(lifecycle: list) -> pd.DataFrame:
    """Returns a Pandas DataFrame with IT-Components and their lifecycle types by specifing one or multiple lifecycle types
        Parameters:
            - lifecycle (list): lifecycle type of the IT-Component
            - lifecycle types: 
            `["__any__", "active", "endOfLife", "phaseIn", "phaseOut", "plan", "__missing__", "_noLifecycle_"]`

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId]`
    """

    start_date = str(date.today())
    end_date = start_date
    print("Dates:", start_date, "-", end_date)

    # on_ITComponent_nodes
    _lifecycle = "ITComponentLifecycle: lifecycle { asString}"
    return get_ITComponents(facet_filters={"fact_sheet_type":{"keys":["ITComponent"]}, "lifecycle":{"keys":lifecycle, "date_range":[start_date, end_date]}}, on_ITComponent_nodes= [_lifecycle])

def get_ITComponents_with_a_lifecycle() -> pd.DataFrame:
    """Returns a Pandas DataFrame of IT-Components with a lifecycle

        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, ITComponentLifecycle.asString]` of an IT-Component
    """
    return get_ITComponents_by_lifecycle_type(lifecycle= ["active", "endOfLife", "phaseIn", "phaseOut", "plan"])

def _get_ITComponents_info(facet_filters: FilterTemplate=None, on_ITComponent_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Helper method which returns relevent information (Pflichtfelder) of all IT-Components on LeanIX in form of a Pandas DataFrame.

        Parameters:
            facet_filters (FilterTemplate, optional): 
                Additional FacetFilters to be applied to the query variables
            
            on_ITComponent_nodes (list, optional):
                Additional on_ITComponent_nodes (properties of a IT component) to be added to the query, e.g. `displyName`, `description`, `bankId`

            on_node_nodes (list, optional):
                Additional on_node_nodes (properties of a node) to be added to the query, e.g. `fullName`, `level`, `status`
            
        Returns:
            pd.DataFrame:
            By default the DataFrame contains:
              `[id, displayName, description, qualitySeal, lxState, category, softwareDistribution, status, completion.percentage, 	
                relITComponentToApplication.edges, subscriptions.edges, relITComponentToProvider.edges,
                relITComponentToInterface.edges, ITComponentLifecycle.asString, ITComponentLifecycle.phases]` 
            of an IT component (default = when no additional `on_ITComponent_nodes` or `on_node_nodes` are added)
    """

    # on_ITComponent_nodes
    _ITComponent_nodes = [query_temp.completion_query, "description", "qualitySeal", "lxState", "category", "softwareDistribution", "status", query_temp.rel_ITComponent_to_app_query, query_temp.ITComponent_subscriptions_query, 
                           query_temp.ITComponent_lifecycle_query]
    
    # if given add on_ITComponent_nodes
    if on_ITComponent_nodes:
        for node in on_ITComponent_nodes:
            _ITComponent_nodes.append(node)
    
    _facet_filters = {"fact_sheet_type":{"keys":["ITComponent"]}}
    # if given add facet_filters
    if facet_filters:
        for key, value in facet_filters.items():
            print(str(key) + ": " + str(value))
            _facet_filters.update({key : value})

    df = get_ITComponents(facet_filters= _facet_filters, on_ITComponent_nodes= _ITComponent_nodes, on_node_nodes= on_node_nodes).drop(columns=["ITComponentLifecycle"])
    
    return df

def get_ITComponents_completion(sort_values_asc: bool=False) -> pd.DataFrame:
    """Returns a Pandas DataFrame of all ITComponents and their completion in percent
        
        Parameters:
                sort_values_asc(bool, optional): 
                    Sorts the rows of the DataFrame in ascending order by the `completion.percentage` column

        Returns:
            pd.DataFrame: `[id, displayName, bankId, completion.percentage]`
    """
    df = get_ITComponents(on_ITComponent_nodes= [query_temp.completion_query])
    df["completion.percentage"] = df["completion.percentage"].fillna(0).astype("int")
        
    if sort_values_asc:
        df = get_ITComponents(on_ITComponent_nodes=["completion {percentage}"]).sort_values(by= "completion.percentage", axis=0)
    return df

def get_ITComponents_subscriptions() -> pd.DataFrame:
    """Returns a Pandas DataFrame of the subscriptions of each ITComponent
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, subscriptions.edges]` of an ITComponent
    """
    df = get_ITComponents(on_ITComponent_nodes= [query_temp.ITComponent_subscriptions_query])

    # add col to count subscriptions
    df["subscription_count"] = 0

    i = 0
    indices = df.index # indices of the df
    for rel in df["subscriptions.edges"]:
        if rel != []:
            #print(rel)
            users = []
            #print("len:", len(rel))
            for j in range(len(rel)):
                user_email = rel[j]["node"]["user"]["email"]
                user_role = rel[j]["node"]["type"]
                role = []
                if rel[j]["node"]["roles"] != []:
                    role = rel[j]["node"]["roles"][0]["name"]
                #print(user_email, user_role, role) 
                users.append([user_email, user_role, role])
            #print("users:", users)
            users_dict = _subscriptions_to_dict(users)
            df.at[indices[i], "subscriptions.edges"] = users_dict # modify entry in column "subscriptions.edges" at the correct index
            df.at[indices[i], "subscription_count"] = len(users_dict)
        i += 1
    df["subscriptions.edges"] = df["subscriptions.edges"].apply(lambda y: None if (type(y) == list and len(y) == 0) else y)

    df = df.sort_index().reset_index(drop=True)
    df["subscription_count"] = df["subscription_count"].fillna(0)
    return df.rename(columns= {"subscriptions.edges": "ITComponent_subscriptions"})

def get_IT_components_interfaces() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all Components and their interfaces
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relITComponentToInterface, Interface_count]` of an ITComponent
    """

    # on_ITComponent_nodes
    relITComponentToInterface = "relITComponentToInterface { edges { node { factSheet { displayName id } } } }"
    df = get_ITComponents(facet_filters= {"fact_sheet_type": {"keys":["ITComponent"]}, "relation_ITComponent_to_interface": {"keys":[]}}, on_ITComponent_nodes=[relITComponentToInterface])

    relation = "relITComponentToInterface"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "Interface")

def get_ITComponents_parents() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all ITComponents and their Parent factSheet
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relToParent, Parent_count]` of an ITComponent
    """
    
    # on_ITComponent_nodes
    relToParent = "relToParent { edges { node { factSheet { displayName id } } } }"
    df = get_ITComponents(facet_filters={"fact_sheet_type": {"keys":["ITComponent"]}, "relation_to_parent": {"keys":[]}}, on_ITComponent_nodes=[relToParent])

    relation = "relToParent"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "Parent")

def get_ITComponents_user_groups() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all ITComponents and their User Groups
    
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relITComponentToUserGroup, UserGroups_count]` of an ITComponent
    """
    
    # on_ITComponent_nodes
    relITComponentToUserGroup = "relITComponentToUserGroup { edges { node { factSheet { displayName id } } } }"
    df = get_ITComponents(facet_filters={"fact_sheet_type": {"keys":["ITComponent"]},"relation_ITComponent_to_user_group":{"keys":[]}}, on_ITComponent_nodes=[relITComponentToUserGroup])

    relation = "relITComponentToUserGroup"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "UserGroup")

def get_ITComponents_providers() -> pd.DataFrame:
    """Returns a Pandas DataFrame with all ITComponents and their Provider
        Returns:
            pd.DataFrame:
            By default the DataFrame contains `[id, displayName, bankId, relITComponentToProvider, Provider_count]` of an ITComponent
    """
    
    # on_ITComponent_nodes
    relITComponentToProvider = "relITComponentToProvider { edges { node { factSheet { displayName id } } } }"
    df = get_ITComponents(facet_filters={"fact_sheet_type": {"keys":["ITComponent"]},"relation_ITComponent_to_provider":{"keys":[]}}, on_ITComponent_nodes=[relITComponentToProvider])

    relation = "relITComponentToProvider"
    return _count_relations(df= df, relation= relation, count_factSheet_type= "Provider")

####################################### IT Component

####################################### Process

def get_processes(facet_filters: FilterTemplate=None, on_process_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
    """Returns all Process on LeanIX in form of a Pandas DataFrame

    Parameters:
        facet_filters (FilterTemplate, optional): 
            Additional FacetFilters to be applied to the query variables
        
        on_process_nodes (list, optional):
            Additional on_process_nodes (properties of a process) to be added to the query, e.g. `displyName`, `description`, `adonisVersion`

        on_node_nodes (list, optional):
            Additional on_node_nodes (properties of a node) to be added to the query, e.g.  `level`, `status`
        
    Returns:
        pd.DataFrame:
        By default the DataFrame contains `[id, displayName, adonisVersion, externalId.externalId]` of a process (default = when no additional `on_process_nodes` or `on_node_nodes` are added)

    Examples:
        These examples get all processes with a broken quality seal in addition to other properties like: `type`, `level`, ...

        Example 1: Generically define attributes in advance
            >>> filters = {"fact_sheet_type": {"keys":["Process"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}
            >>> process_nodes = ["type"]
            >>> node_nodes = ["level", "status"]
            >>> get_processes(facet_filters= filters, on_process_nodes= process_nodes, on_node_nodes= node_nodes)

                
        Example 2: Specifing attributes when calling the function
            >>> get_processes(facet_filters= {"fact_sheet_type": {"keys":["Process"]}, "quality_seal": {"keys":["BROKEN_QUALITY_SEAL"]}}, on_process_nodes= ["type"], on_node_nodes= ["level", "status"])
    
            -> The DataFrame will have columns: 
            `[id, displayName, adonisVersion, externalId.externalId, type, level, status]`
    """

    # Applying .dropna(how="all") to df to filter to get remove all rows/entries with only NaN-values
    # this is useful in case the function get_ITComponents is called without arguments
    # drop column "externalId" becaues it has only NaN values
    return factSheets_to_df(query_processes(facet_filters, on_process_nodes, on_node_nodes)).dropna(how= "all").drop(columns= ["externalId"], axis= "columns")

def processes_overview_values(sort_values_by_col: str="displayName") -> pd.DataFrame:
    """Returns an Overview (Pflichtfelder) of all Process on LeanIX in form of a Pandas DataFrame

        sort_values_by_col (str, optional): 
                    Sorts the rows of the DataFrame in by the this column.
                    
                    Example: sort_values_by_col: str="completion.percentage"

        Parameters:
            sort_values_asc(bool): 
                Sorts the rows of the DataFrame in ascending order by the `completion.percentage` column

        Returns:
            pd.DataFrame:
            By default the DataFrame contains: 
            `[id, displayName, adonisVersion, externalId.externalId, completion.percentage, alias, description, relToParent.edges,
            relProcessToApplication.edges, subscriptions, qualitySeal, lxStatel, level, status, Cardinality ITComponent : apps]` 
            of a process
    """

    _process_nodes = [query_temp.completion_query, "qualitySeal", "lxState", query_temp.process_rel_to_app_query, query_temp.process_subscriptions_query, "alias", "description"]
    _node_nodes = ["level", "status"]
    df = get_processes(on_process_nodes = _process_nodes, on_node_nodes= _node_nodes).dropna(how= "all")


    df = _extract_applications(df, factSheet_type= "Process")
    df = _extract_subscriptions(df).rename(columns= {"subscriptions.edges": "subscriptions"})
    return df.sort_values(by= sort_values_by_col, axis= 0).reset_index(drop=True)

####################################### Process

####################################### CHECK Data Syncronisation and Correctness between Applications and IT-Components

def check_linked_ITComponent_app_synchronisation_overview_values() -> pd.DataFrame:
    """Compares the relation between linked IT-Compnents and Application are in sync regarding: "
        - lifecycle: IT-Compnents and Application have same lifecylce (same month and year)
        - Cardinality: IT-ComponentX uses ApplicationY <==> ApplicationY uses IT-ComponentX"

        Returns:
            pandas.DataFrame:
                The DataFrame contains: 
                    `[ITComponent_id, ITComponent, app_id, app_name,	
                    Cardinality ITComponent : apps,	Cardinality app : ITComponents,	Cardinalities m:n,
                    Cardinality match, ITComponentLifecycle.phases,	ApplicationLifecycle.phases, 
                    app & ITComponent missing lifecycle, ITComponent missing lifecycle,	app missing lifecycle,	
                    active phase is not sync, endOfLife phase is not sync, app: no active phase value, app: no endOfLife phase value,	
                    phaseIn phase is not sync, plan phase is not sync,	phaseOut phase is not sync,
                    ITComponent_subscriptions, app_id, app_name, app_subscriptions, different_subscription,
                     same_subscription, same_role, same_person_different_role]`
    """

    df = _compine_ITComponents_with_application_subscriptions().filter(items=["ITComponent_id", "ITComponentLifecycle.phases", "ApplicationLifecycle.phases"])
    df1 = _compare_ITComponent_app_cardinality()
    df2 = _compare_lifecycles_bool(df)
    df3 = compare_ITComponents_with_it_application_subscriptions_values()
    
    df = df1.merge(df2, on=["ITComponent_id"])
    df = df.merge(df3, on=["ITComponent_id", "ITComponent", "app_id", "app_name"])

    return df

def check_linked_ITComponent_app_synchronisation_overview_bool() -> pd.DataFrame:
    """Compares the relation between linked IT-Compnents and Application are in sync regarding: "
        - lifecycle: IT-Compnents and Application have same lifecylce (same month and year)
        - Cardinality: IT-ComponentX uses ApplicationY <==> ApplicationY uses IT-ComponentX"

        Returns:
            pandas.DataFrame:
                The DataFrame contains: 
                    `[ITComponent_id, ITComponent, app_id, app_name,	
                    Cardinality ITComponent : apps,	Cardinality app : ITComponents,	Cardinalities m:n,
                    Cardinality match, ITComponentLifecycle.phases,	ApplicationLifecycle.phases, 
                    app & ITComponent missing lifecycle, ITComponent missing lifecycle,	app missing lifecycle,	
                    active phase is not sync, endOfLife phase is not sync, app: no active phase value, app: no endOfLife phase value,	
                    phaseIn phase is not sync, plan phase is not sync, phaseOut phase is not sync,
                    ITComponent_subscriptions, app_id, app_name, app_subscriptions, different_subscription, 
                    same_subscription, same_role, same_person_different_role]`
    """
    df = _compine_ITComponents_with_application_subscriptions().filter(items=["ITComponent_id", "ITComponentLifecycle.phases", "ApplicationLifecycle.phases"])
    df1 = _compare_ITComponent_app_cardinality()
    df2 = _compare_lifecycles_bool(df)
    df3 = compare_ITComponents_with_it_application_subscriptions_bool()
    
    df = df1.merge(df2, on=["ITComponent_id"])
    df = df.merge(df3, on=["ITComponent_id", "ITComponent", "app_id", "app_name"])

    return df

def _compine_ITComponents_with_application_subscriptions() -> pd.DataFrame:
    """Helper method that compines the subscriptions of applications and IT-Components in one df"""
    df = ITComponents_overview_values()
    
    app_subs = get_apps_subscriptions().filter(["id", "displayName", "app_subscriptions"]).rename(columns= {"id": "app_id", "displayName":"app_name"})

    app_lifecycle = get_apps_lifecycles().filter(["id", "displayName", "ApplicationLifecycle.phases"]).rename(columns= {"id": "app_id", "displayName":"app_name"})

    apps_info = app_subs.merge(right= app_lifecycle, on=["app_id", "app_name"]).filter(["app_id", "app_name", "app_subscriptions", "ApplicationLifecycle.phases"])

    # version in which each app is replicated according to how many different subscription it has 
    #app_subs = _apps_subscriptions(app_subs)

    df["ITComponent_applications"] = df["ITComponent_applications"].apply(lambda y: None if (type(y) == list and len(y) == 0) else y)
    df["ITComponent_subscriptions"] = df["ITComponent_subscriptions"].apply(lambda y: None if (type(y) == list and len(y) == 0) else y)

    #df = df.merge(right= app_subs, left_on=["ITComponent_applications"] , right_on= ["app_id"], how="left")
    df = df.merge(right= apps_info, left_on=["ITComponent_applications"] , right_on= ["app_id"], how="left")
    
    
    df = df.sort_values(by=["displayName"])
    return df.rename(columns= {"id": "ITComponent_id", "displayName": "ITComponent"})

# Jede IT-Komponente hat einen Owner und ist in sync mit den Applikationen
def compare_ITComponents_with_it_application_subscriptions_bool() -> pd.DataFrame:
    """Compares the subscription of the application and IT-Component linked with them and returns columns with boolean values
        
        Returns:
            pd.DataFrame:
            By default the DataFrame contains:
            `[ITComponent_id, ITComponent, ITComponent_subscriptions, app_id, app_name, app_subscriptions, different_subscription, same_subscription, same_role, same_person_different_role]`
    """
    df = _compine_ITComponents_with_application_subscriptions()
    _col1 = "ITComponent_subscriptions"
    _col2 = "app_subscriptions"

    # add columns
    df["different_subscription"] = False
    df["same_subscription"] = False
    df["same_subscription_same_role"] = False
    df["same_subscription_different_role"] = False

    for entry in df.index:
        different_subscription = False
        same_role = False
        same_person = False
        same_person_different_role = False
        if not (pd.isna(df.at[entry, _col1]) or pd.isna(df.at[entry, _col2])):
            # get keys of each col for each row (= phase types)
            #print(df.at[entry, _col1])
            _col1_keys = list(df.at[entry, _col1])
            _col2_keys = list(df.at[entry, _col2])
            for key in _col1_keys: # if the phase in _col1 is also in _col2 then compare their values
                x = df.at[entry, _col1][key]
                if _col2_keys.__contains__(key):
                    y = df.at[entry, _col2][key]
                    same_person = True
                    if x == y:
                        same_role = True
                    else:
                        same_person_different_role = True
                else:
                    different_subscription = True
            df.at[entry, "different_subscription"] = different_subscription 
            df.at[entry, "same_subscription"] = same_person
            df.at[entry, "same_subscription_same_role"] = same_role
            df.at[entry, "same_subscription_different_role"] = same_person_different_role
    df = df.filter(items=["ITComponent_id", "ITComponent", "ITComponent_subscriptions", "app_id", "app_name", "app_subscriptions", "different_subscription", "same_subscription", "same_subscription_same_role", "same_subscription_different_role"])
    return df

# Jede IT-Komponente hat einen Owner und ist in sync mit den Applikationen
def compare_ITComponents_with_it_application_subscriptions_values() -> pd.DataFrame:
    """Compares the subscription of the applications and IT-Component linked with them and return a df with the values
    Returns:
            pd.DataFrame:
            By default the DataFrame contains:
            `[ITComponent_id, ITComponent, ITComponent_subscriptions, app_id, app_name, app_subscriptions, different_subscription, same_subscription, same_role, same_person_different_role]`
    """
    df = _compine_ITComponents_with_application_subscriptions()
    _col1 = "ITComponent_subscriptions"
    _col2 = "app_subscriptions"

    # add columns
    df["different_subscription"] = None
    df["same_subscription"] = None
    df["same_subscription_same_role"] = None
    df["same_subscription_different_role"] = None

    for entry in df.index:
        different_subscription = ""
        same_role = ""
        same_person = ""
        same_person_different_role = ""
        if not (pd.isna(df.at[entry, _col1]) or pd.isna(df.at[entry, _col2])):
            # get keys of each col for each row (= phase types)
            #print(df.at[entry, _col1])
            _col1_keys = list(df.at[entry, _col1])
            _col2_keys = list(df.at[entry, _col2])
            for key in _col1_keys: # if the phase in _col1 is also in _col2 then compare their values
                x = df.at[entry, _col1][key]
                if _col2_keys.__contains__(key):
                    y = df.at[entry, _col2][key]
                    same_person += f"{key}"
                    if x == y:
                        same_role += f"{x}"
                    else:
                        same_person_different_role += f"{key}: {x} != {y}"
                else:
                    different_subscription += f"{key}: {x} != {_col2_keys}"
            df.at[entry, "different_subscription"] = different_subscription if different_subscription != ""  else None
            df.at[entry, "same_subscription"] = same_person if same_person != ""  else None
            df.at[entry, "same_subscription_same_role"] = same_role if same_role != ""  else None
            df.at[entry, "same_subscription_different_role"] = same_person_different_role if same_person_different_role != ""  else None
    df = df.filter(items=["ITComponent_id", "ITComponent", "ITComponent_subscriptions", "app_id", "app_name", "app_subscriptions", "different_subscription", "same_subscription", "same_subscription_same_role", "same_subscription_different_role"])
    return df

def _compare_lifecycles_bool(df: pd.DataFrame) -> pd.DataFrame:
    """Helper method that implemnts the logic to compare lifecycles of applications and IT-Components (compares types of inconsistency): 
        
            "app & ITComponent missing lifecycle": bool, 
        "ITComponent missing lifecycle": bool, 
        "app missing lifecycle": bool, 
        "active phase is not sync": bool, 
        "endOfLife phase is not sync": bool,
        "app: no active phase value": bool, 
        "app: no endOfLife phase value": bool,
        ...}
    """

    df.sort_index(inplace=True)
    # replace empty list with None
    for col in df.columns:
            df[col] = df[col].apply(lambda y: None if (type(y) == list and len(y) == 0) else y)

    _col1 = "ITComponentLifecycle.phases"
    _col2 = "ApplicationLifecycle.phases"

    
    comparison_cols = {"app & ITComponent missing lifecycle": False, "ITComponent missing lifecycle": False, "app missing lifecycle": False, 
                       "active phase is not sync":False, "endOfLife phase is not sync":False,
                        "app: no active phase value":False, "app: no endOfLife phase value":False}
    for key in comparison_cols:
            df[key] = None

    for entry in df.index:
        # skip row if one of the entries is = NaN (missing value)
        if (pd.isna(df.at[entry, _col1]) or pd.isna(df.at[entry, _col2])):
            if (pd.isna(df.at[entry, _col1])):
                comparison_cols["ITComponent missing lifecycle"] = True
            
            if(pd.isna(df.at[entry, _col2])):
                comparison_cols["app missing lifecycle"] = True
            
            if (pd.isna(df.at[entry, _col1]) and pd.isna(df.at[entry, _col2])):
                comparison_cols["app & ITComponent missing lifecycle"] = True

        else:
            # get keys of each col for each row (= phase types)
            _col1_keys = list(df.at[entry, _col1])
            _col2_keys = list(df.at[entry, _col2])
            
            # new dict to store the comparsion, format{phaseX: bool, phaseY: bool}
            phases = {"active": False, "endOfLife": False}
            
            for key in _col1_keys: # if the phase in _col1 is also in _col2 then compare their values
                if _col2_keys.__contains__(key):
                        x = df.at[entry, _col1][key]
                        y = df.at[entry, _col2][key]
                        if (x <= y):
                            phases[key] = True
                        else:
                            phases[key] = False
                            comparison_cols[f"{key} phase is not sync"] = True                 
                else:
                    if(key == "active"): 
                        comparison_cols["app: no active phase value"] = True
                    elif(key == "endOfLife"):
                        comparison_cols["app: no endOfLife phase value"] = True

        for key in comparison_cols:
            #print(key)
            if comparison_cols[key] == True:
                df.at[entry, key] = True
            else:
                df.at[entry, key] = False

    for i in range(3, len(df.columns)):
        df[df.columns[i]] = df[df.columns[i]].fillna(value= False)
        

    return df

def _compare_ITComponent_app_cardinality() -> pd.DataFrame:
    """Helper methode to help compare the relation between IT-Compnents and Application are in sync regarding:
        - Cardinality: IT-ComponentX uses ApplicationY <==> ApplicationY uses IT-ComponentX"""
    
    df = _compine_ITComponents_with_application_subscriptions()
    df = df.drop_duplicates(subset=["ITComponent_id"])
    df1 = df.filter(items=["ITComponent_id", "ITComponent", "ITComponent_applications", "app_name", "Cardinality ITComponent : apps"])
    df2 = df.groupby(by=["app_id"], as_index=False).size().rename(columns={"size":"Cardinality app : ITComponents"})
    df = df1.merge(df2, left_on="ITComponent_applications", right_on="app_id", how="left").drop(columns=["app_id"]).rename(columns={"ITComponent_applications":"app_id"})
    
    
    df["Cardinality ITComponent : apps"]= df["Cardinality ITComponent : apps"].fillna(value=0)
    df["Cardinality app : ITComponents"] = df["Cardinality app : ITComponents"].fillna(value=0).astype(int).fillna(value=0)
    df["Cardinalities m:n"] = df["Cardinality ITComponent : apps"].astype(str) + " : " + df["Cardinality app : ITComponents"].astype(str)
    df["Cardinality match"] = df.apply(lambda row: row["Cardinality ITComponent : apps"] == row["Cardinality app : ITComponents"], axis= 1)

    return df

def _ITComponents_lifecycle(df: pd.DataFrame) -> pd.DataFrame:  
    """Helper method for get_ITComponents_overview_values method. It extracts and cleans lifecycle values"""
    i = 0
    indices = df.index # indices of the df
    for relation in df["ITComponentLifecycle.phases"]:
        # check if there is a lifecyle
        if type(relation) is list and relation != []:
            lifecylces = []
            #print(relation)
            #print("len:", len(relation))
            for j in range(len(relation)):
                phase = relation[j]["phase"]
                phase_date = relation[j]["startDate"]
                #print(phase, phase_date)
                lifecylces.append([phase, phase_date])
            #print("lifecycles:", lifecylces)
            lifecylces_dict = _lifecycles_to_dict(lifecylces)
            df.at[indices[i], "ITComponentLifecycle.phases"] = lifecylces_dict   
        i += 1
    df = df.rename(columns= {"id": "ITComponent_id"})
    df = df.sort_index().reset_index(drop=True)
    return df

####################################### CHECK Data Syncronisation and Correctness between Applications and IT-Components

########################## GraphQL Queries To Pandas DataFrame ##########################