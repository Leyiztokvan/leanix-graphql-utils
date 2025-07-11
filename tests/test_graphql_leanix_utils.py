"""
File to test the main methods in `leanix_utils.py` and `graphql_leanix_utils.py`

Note: To run all the test at once:
    - cd into directory containing this file
    - run test using `pytest` library
    command: $ pytest
    
or modify and run `main()` if needed

Note: run tests ussing the `EANIX_API_TOKEN` and not `LEANIX_API_TOKEN_SANDBOX`
"""

import json
import sys
import os
import pandas as pd
from pandas import json_normalize
import pytest


script_dir = os.path.dirname( __file__ )
sys.path.append(script_dir)

# Add src directory to path, to be able to import the modules from src
src_dir = os.path.join(script_dir, '..', "src")
sys.path.append(src_dir)

print("scrpit_dir", script_dir)
print("src_dir", src_dir)


import graphql_leanix_utils as gqlix
import leanix_utils as lix


class TestGqlLeanixBaseFunctions:

    def test_obtain_access_token(self):
        ACCESS_TOKEN = lix.obtain_access_token()
        assert ACCESS_TOKEN != "", "Access token is empty!"
   
    # test the post_query method by feeding in a dummy_graphql_response 
    # path to the queries .txt files
    QUERIES_DIR = f"{script_dir}/testing_queries_txt"
    #print("QUERIES_DIR:", QUERIES_DIR)


    QUERY_PATH = f"{QUERIES_DIR}/apps.txt"
    query_data = gqlix._convert_gql_query_from_txt(QUERY_PATH)
    global gql_query 
    global gql_variables
    global dummy_response
    global nodes_dummy_response_df
    gql_query = query_data["query"]
    gql_variables = query_data["variables"]


    # Build an absolute path from this notebook's parent directory
    DIR = "dummy_grpahql_responses"
    DIR_path = os.path.abspath(os.path.join('tests', DIR))

    # Add `_path` to sys.path if not already present
    if DIR_path not in sys.path:
        sys.path.append(DIR_path)

    DUMMY_RESPONSE_PATH = f"{DIR_path}/app_ids_dummy.json"

    with open(DUMMY_RESPONSE_PATH, "r") as file:
        dummy_response = json.loads(file.read())
    print (DUMMY_RESPONSE_PATH)


    nodes_dummy_response_df = json_normalize(dummy_response["data"]["allFactSheets"]["edges"])
    nodes_dummy_response_df.columns = [col_name.removeprefix("node.") for col_name in nodes_dummy_response_df]

    
    def test_query_apps(self):
        query_response = gqlix.query_apps()
        assert type(query_response) is dict, f"Query post response should be a dict but it is a {type(query_response)}!"
        assert query_response != "", "Query post response is empty!"

        # post response of the query contains the main columns [id, bankId, displayName] and is not empty (has > 0 rows)
        # checke points above by comparing to a dummy_response
        query_df = json_normalize(query_response["data"]["allFactSheets"]["edges"])
        query_df.columns = [col_name.removeprefix("node.") for col_name in query_df]
        dummy_df = nodes_dummy_response_df

        for node in query_df.columns:
            assert node in dummy_df.columns, "One or multiple of data frame main columns [id, bankId, displayName] is missing!"
        assert query_df.index.size > 0 , "Data Frame is empty (has 0 rows)!"
        

    @pytest.mark.parametrize("gql_query, gql_variables, dummy_response", [(gql_query, gql_variables, dummy_response)])
    def test_post_query(self, gql_query, gql_variables, dummy_response):
        # post response of the query contains the main columns [id, bankId, displayName] and is not empty (has > 0 rows)
        # checke points above by comparing to a dummy_response
        dummy_df = json_normalize(dummy_response["data"]["allFactSheets"]["edges"])
        #print("Dummy_df:", dummy_df)

        # remove ${...}  
        gql_variables = gqlix._replace_query_variables(gql_variables, "")

        nodes_query_response = gqlix.post_query(gql_query, gql_variables)["data"]["allFactSheets"]["edges"]
        query_df = json_normalize(nodes_query_response).dropna(how= "all")
        #print("Query_df:", query_df)
        for node in query_df.columns:
            assert node in dummy_df.columns, "One or multiple of data frame main columns [id, bankId, displayName] is missing!"
        assert query_df.index.size > 0 , "Data Frame is empty (has 0 rows)!"

    def test_fact_sheet_to_df(self):
        query_response = dummy_response
        df = gqlix.factSheets_to_df(allFactSheets=query_response)
        assert type(df) is pd.DataFrame, f"Return type of factSheets_to_df() should be a Pandas DataFrame but it is {type(df)}!"
        assert df.columns.size >= 3
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"

    def test_get_apps(self):
        df = gqlix.get_apps()
        print(df)
        # columns: [id, bankId, displayName]
        assert df.columns.size >= 3
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"



    def test_get_user_groups(self):
        df = gqlix.get_user_groups()
        print(df)
        # columns: [id, displayName, level, relToParent.edges]
        assert df.columns.size >= 3
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"

    def test_get_providers(self):
        df = gqlix.get_providers()
        print(df)
        # columns: [id, displayName]
        assert df.columns.size >= 2
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"

    def test_get_interfaces(self):
        df = gqlix.get_interfaces()
        print(df)
        # columns: [id, displayName]
        assert df.columns.size >= 2
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"
    
    def test_get_activities(self):
        df = gqlix.get_activities()
        print(df)
        # columns: [id, displayName]
        assert df.columns.size >= 2
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"
    

    def test_get_business_capabilities(self):
        df = gqlix.get_business_capabilities()
        print(df)
        # columns: [id, bankId, displayName]
        assert df.columns.size >= 3
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"

    
    def test_get_ITComponents(self):
        df = gqlix.get_ITComponents()
        print(df)
        # columns: [id, displayName]
        assert df.columns.size >= 2
        assert df.index.size > 0 , "Data Frame is empty (has 0 rows)!"
    

def main():
    baseFunctions = TestGqlLeanixBaseFunctions

    # modify and run main() if needed
    """
    baseFunctions.test_obtain_access_token(baseFunctions)
    baseFunctions.test_post_query(baseFunctions, gql_query, gql_variables, dummy_response)
    baseFunctions.test_query_apps(baseFunctions)
    baseFunctions.test_fact_sheet_to_df(baseFunctions)
    baseFunctions.test_get_apps(baseFunctions)
    baseFunctions.test_get_user_groups(baseFunctions)
    baseFunctions.test_get_interfaces(baseFunctions)
    baseFunctions.test_get_providers(baseFunctions)
    baseFunctions.test_get_activities(baseFunctions)
    baseFunctions.test_get_business_capabilities(baseFunctions)
    baseFunctions.test_get_ITComponents(baseFunctions)
    """    


if __name__ == '__main__':
    main()